"""Map ink-first patch predictions back to 3D: every pixel (i, j) of a patch's centre sits at c + (i - m) u + (j - m) v.

  onto_mesh    onto a window of a tifxyz mesh (e.g. a known-text segment, for evaluation): each mesh point (the grid
               upsampled to full resolution) takes the mean of the patch pixels within `radius` voxels
  onto_renders onto every rendered winding (flattened tifxyz + its ink maps) that crosses the block: within-scroll
               comparison with the mesh pipeline at the same pixels

`blend`: per-patch z-score and Hann weights over the centre, which smooths overlaps but removes absolute ink levels (on
PHerc0139 it raised the significance, on PHerc0841 it lowered the correlation; keep both)."""
from __future__ import annotations

import glob
import json
import os

import numpy as np

from .mosaic import centre as patch_centre


def _offsets(S: int, C: int):
    o = (S - C) // 2
    ii, jj = np.mgrid[o:o + C, o:o + C].astype(np.float32) - (S - 1) / 2
    return ii.ravel(), jj.ravel()


def _weights(C: int, blend: bool):
    hw = np.hanning(C + 2)[1:-1]
    return (np.outer(hw, hw) + 0.05).ravel() if blend else np.ones(C * C)


def patch_points(P, k: int, ii, jj) -> np.ndarray:
    c, u, v = P['centre'][k], P['u'][k], P['v'][k]
    return c[None, :] + u[None, :] * ii[:, None] + v[None, :] * jj[:, None]


def accumulate(P, ink_map: np.ndarray, tree, n_targets: int, centre: int, radius: float, blend: bool):
    """Mean (weighted) ink of the patch pixels landing within `radius` of each target point of a cKDTree."""
    S = int(P['size']); ii, jj = _offsets(S, centre); wgt = _weights(centre, blend)
    acc, cnt = np.zeros(n_targets), np.zeros(n_targets)
    for k, rc in enumerate(P['rowcol']):
        val = patch_centre(ink_map, rc, S, centre).ravel().astype(np.float64)
        if blend:
            val = (val - val.mean()) / (val.std() + 1e-3)
        d, idx = tree.query(patch_points(P, k, ii, jj), distance_upper_bound=radius)
        ok = np.isfinite(d)
        if ok.any():
            np.add.at(acc, idx[ok], val[ok] * wgt[ok]); np.add.at(cnt, idx[ok], wgt[ok])
    return np.where(cnt > 0, acc / np.where(cnt > 0, cnt, 1), np.nan), cnt


def read_tifxyz(d: str):
    import tifffile
    X, Y, Z = [tifffile.imread(os.path.join(d, f'{k}.tif')).astype(np.float32) for k in 'xyz']
    meta = json.load(open(os.path.join(d, 'meta.json')))
    return X, Y, Z, int(round(1 / meta['scale'][0]))


def mesh_window_points(mesh: str, window) -> tuple[np.ndarray, tuple]:
    """Full-resolution zyx points of a tifxyz grid window (r0 r1 c0 c1 in grid cells)."""
    import cv2
    X, Y, Z, f = read_tifxyz(mesh); r0, r1, c0, c1 = window
    H, W = (r1 - r0) * f, (c1 - c0) * f
    up = lambda g: cv2.resize(g[r0:r1 + 1, c0:c1 + 1], ((c1 - c0 + 1) * f, (r1 - r0 + 1) * f), interpolation=cv2.INTER_LINEAR)[:H, :W]
    return np.stack([up(Z), up(Y), up(X)], -1).reshape(-1, 3), (H, W)


def onto_mesh(patches: str, maps: str, mesh: str, window, centre: int = 128, radius: float = 8.0, blend: bool = False, log=print) -> dict:
    """{'<model>_<order>': image on the mesh window (NaN where no patch pixel landed), 'shape': (H, W)}."""
    import tifffile
    from scipy.spatial import cKDTree
    P = np.load(patches); pts, shape = mesh_window_points(mesh, window); tree = cKDTree(pts)
    out = {'shape': np.array(shape)}
    for path in sorted(glob.glob(os.path.join(maps, '*.tif'))):
        model = os.path.basename(path).split('__')[1]; order = 'reverse' if path.endswith('_reverse.tif') else 'forward'
        img, cnt = accumulate(P, tifffile.imread(path).astype(np.float32) / 255., tree, len(pts), centre, radius, blend)
        out[f'{model}_{order}'] = img.reshape(shape).astype(np.float32)
        log(f'{model} {order}: mesh coverage {np.mean(cnt > 0):.3f}')
    return out


def onto_renders(patches: str, inkmaps: str, model: str, flat_dir: str, meshmaps: str, s: int = 25, ds: int = 2,
                 radius: float = 8.0, centre: int = 128, log=print) -> dict:
    """Every rendered winding (flat_dir/wNNN/tifxyz/flatten.tifxyz with meshmaps/wNNN__<model>__L66s<s>_reverse.tif) that
    enters the block: ink-first values on its render pixels (1/ds) and the mesh-based map there. Returns per-winding rows."""
    import cv2, tifffile
    from scipy.spatial import cKDTree
    P = np.load(patches); box = P['box']; lo = box[[0, 2, 4]]; hi = box[[1, 3, 5]]
    pts, owner, pix, wins = [], [], [], []
    for d in sorted(glob.glob(os.path.join(flat_dir, 'w*', 'tifxyz', 'flatten.tifxyz'))):
        w = d.split(os.sep)[-3]; mp = os.path.join(meshmaps, f'{w}__{model}__L66s{s}_reverse.tif')
        if not os.path.exists(mp):
            continue
        X, Y, Z, _ = read_tifxyz(d); v = X > 0
        inb = v & (Z >= lo[0]) & (Z < hi[0]) & (Y >= lo[1]) & (Y < hi[1]) & (X >= lo[2]) & (X < hi[2])
        if inb.sum() < 50:
            continue
        H, W = tifffile.TiffFile(mp).pages[0].shape; h, wd = H // ds, W // ds
        up = lambda g: cv2.resize(g, (wd, h), interpolation=cv2.INTER_LINEAR)
        vv = cv2.resize(inb.astype(np.uint8), (wd, h), interpolation=cv2.INTER_NEAREST) > 0
        zz, yy, xx = up(Z), up(Y), up(X); rr, cc = np.nonzero(vv)
        pts.append(np.stack([zz[rr, cc], yy[rr, cc], xx[rr, cc]], 1)); owner.append(np.full(len(rr), len(wins)))
        pix.append(np.stack([rr, cc], 1)); wins.append(dict(w=w, shape=(h, wd), map=mp))
    if not wins:
        raise SystemExit('no rendered winding enters this block')
    pts, owner, pix = np.concatenate(pts), np.concatenate(owner), np.concatenate(pix)
    log(f'{len(wins)} windings, {len(pts)} render pixels in the block')
    tree = cKDTree(pts); res = {}
    for order, suf in (('forward', ''), ('reverse', '_reverse')):
        M = tifffile.imread(os.path.join(inkmaps, f'mosaic__{model}__L66s25{suf}.tif')).astype(np.float32) / 255.
        res[order], _ = accumulate(P, M, tree, len(pts), centre, radius, False)
    rows = []
    for k, W_ in enumerate(wins):
        m = owner == k; rc = pix[m]
        mesh = cv2.resize(tifffile.imread(W_['map']).astype(np.float32) / 255., (W_['shape'][1], W_['shape'][0]), interpolation=cv2.INTER_AREA)
        mv = mesh[rc[:, 0], rc[:, 1]]; row = dict(w=W_['w'], pixels=int(m.sum()))
        for order in ('forward', 'reverse'):
            val = res[order][m]; ok = np.isfinite(val)
            row[f'cov_{order}'] = round(float(ok.mean()), 3)
            row[f'r_{order}'] = round(float(np.corrcoef(val[ok], mv[ok])[0, 1]), 3) if ok.sum() > 500 else None
        rows.append(row); log(str(row))
    return dict(windings=rows)
