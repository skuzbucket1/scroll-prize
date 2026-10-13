"""Synthetic tests of the geometry and bookkeeping (sampling a tilted sheet, mosaic split/stitch, back-projection, the
shifted-reference null). Whether ink first finds text is tested on known-text segments; see the README."""
import os

import numpy as np
import pytest

zarr = pytest.importorskip('zarr')


def _write(path, arr):
    g = zarr.open_group(path, mode='w', zarr_format=2)
    a = g.create_array('0', shape=arr.shape, chunks=(32, 32, 32), dtype='u1', fill_value=0); a[:] = arr


def _tilted_sheet(n=160):
    nrm = np.array([1.0, 0.25, 0.15]); nrm /= np.linalg.norm(nrm)                 # zyx, mostly along z
    zz, yy, xx = np.mgrid[0:n, 0:n, 0:n].astype(np.float32)
    s = (np.stack([zz, yy, xx], -1) - n / 2) @ nrm                                # signed distance to the mid plane
    ct = np.where((s > -4) & (s < 4), 150, 30).astype(np.uint8)                   # an 8-voxel papyrus slab
    pred = np.where((s > 2.5) & (s < 4.5), 255, 0).astype(np.uint8)               # the +n face
    return ct, pred, nrm


def test_sample_tilted_sheet(tmp_path):
    from ink_first.sample import sample_block
    ct, pred, nrm = _tilted_sheet()
    _write(str(tmp_path / 'ct.zarr'), ct); _write(str(tmp_path / 'pred.zarr'), pred)
    info = sample_block(str(tmp_path / 'ct.zarr'), str(tmp_path / 'pred.zarr'), (0, 160, 0, 160, 0, 160), str(tmp_path / 'out'),
                        stride=48, size=32, margin=24, log=lambda *_: None)
    P = np.load(tmp_path / 'out' / 'patches.npz')
    assert info['patches'] >= 4
    assert np.all(np.abs(P['normal'] @ nrm) > 0.95)                              # normals follow the sheet
    assert np.all(P['normal'] @ nrm > 0)                                          # and point out of the papyrus
    m = np.asarray(zarr.open(str(tmp_path / 'out' / 'mosaic.zarr'), mode='r')['0'])
    S = int(P['size']); tiles = [m[:, r * S:(r + 1) * S, c * S:(c + 1) * S] for r, c in P['rowcol']]
    behind = np.mean([t[27:32].mean() for t in tiles]); front = np.mean([t[37:46].mean() for t in tiles])
    assert behind > front + 50                                                    # papyrus behind the surface (layer 33), air in front


def test_per_sheet_sampling_finds_every_sheet():
    from ink_first.sample import surface_points
    pr = np.zeros((96, 96, 96), np.uint8)
    for z in (30, 50, 70):                                                        # three flat sheets 20 voxels apart
        pr[z:z + 2] = 255
    plain = surface_points(pr, 128, 96, 0)
    per = surface_points(pr, 128, 96, 0, per_sheet=True)
    assert len(plain) == 1                                                        # one point for the whole cell
    assert np.allclose(sorted(p[0] for p in per), [30.5, 50.5, 70.5], atol=0.6)   # one on each sheet


def test_split_stitch_roundtrip(tmp_path):
    import tifffile
    from ink_first.mosaic import split, stitch
    S, n = 32, 10; g = int(np.ceil(np.sqrt(n))); d = tmp_path / 'm'
    rng = np.random.default_rng(0); mos = rng.integers(0, 255, (66, g * S, g * S), dtype=np.uint8)
    _write(str(d / 'mosaic.zarr'), mos)
    np.savez(d / 'patches.npz', rowcol=np.array([divmod(i, g) for i in range(n)]), size=S)
    split(str(d), log=lambda *_: None)
    for q in range(4):                                                            # stand-in for inference: a per-pixel function
        qm = np.asarray(zarr.open(str(d / f'q{q}' / 'mosaic.zarr'), mode='r')['0'])
        os.makedirs(d / f'q{q}' / 'maps', exist_ok=True)
        for suf in ('', '_reverse'):
            tifffile.imwrite(d / f'q{q}' / 'maps' / f'mosaic__m__L66s25{suf}.tif', qm[33])
    stitch(str(d), 'm', log=lambda *_: None)
    assert np.array_equal(tifffile.imread(d / 'maps' / 'mosaic__m__L66s25.tif'), mos[33])


def test_back_projection_recovers_a_field():
    from scipy.spatial import cKDTree
    from ink_first.back import accumulate
    S, C, n = 32, 16, 9; g = 3
    cen = np.array([[50.0, 40 + 12 * (i % 3), 40 + 12 * (i // 3)] for i in range(n)])
    N = np.tile([1.0, 0, 0], (n, 1)); U = np.tile([0, 1.0, 0], (n, 1)); V = np.tile([0, 0, 1.0], (n, 1))
    P = dict(centre=cen, normal=N, u=U, v=V, rowcol=np.array([divmod(i, g) for i in range(n)]), size=S)
    M = np.zeros((g * S, g * S), np.float32)                                      # "ink" = y coordinate / 100 at every pixel
    ii, jj = np.mgrid[0:S, 0:S] - (S - 1) / 2
    for k, (r, c) in enumerate(P['rowcol']):
        M[r * S:(r + 1) * S, c * S:(c + 1) * S] = (cen[k, 1] + ii) / 100.0
    yy, xx = np.mgrid[35:75, 35:75]
    mesh = np.stack([np.full(yy.size, 50.0), yy.ravel(), xx.ravel()], 1)
    img, cnt = accumulate(P, M, cKDTree(mesh), len(mesh), C, 1.0, False)
    ok = np.isfinite(img)
    assert ok.mean() > 0.5 and np.allclose(img[ok], mesh[ok, 1] / 100.0, atol=0.01)


def test_shift_null_separates_signal_from_noise():
    from ink_first.evaluate import auc, shift_null
    rng = np.random.default_rng(1)
    import cv2
    ref = (cv2.GaussianBlur(rng.normal(0, 1, (1280, 1280)).astype(np.float32), (0, 0), 6) > 0.05).astype(np.float32)   # blobs, not periodic
    mask = np.ones_like(ref, bool)
    good = shift_null(ref + rng.normal(0, 0.5, ref.shape), ref, mask); bad = shift_null(rng.normal(0, 1, ref.shape), ref, mask)
    assert good['z'] > 4 and abs(bad['z']) < 3
    assert auc(ref.ravel() + 0.1, ref.ravel() > 0.5) > 0.99
