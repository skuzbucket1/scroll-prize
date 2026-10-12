"""ink-first: look for ink without a mesh. Cut patches along the local sheet normal from a published surface prediction,
ink them with any 66-layer surface-volume ink model, map the predictions back to 3D.

  ink-first fetch  --url <zarr> --out <store> --box z0 z1 y0 y1 x0 x1 [--level 0]
  ink-first sample --ct <zarr> --pred <zarr> --box z0 z1 y0 y1 x0 x1 --out <dir> [--stride 96] [--size 256] [--flat 0.25]
  (ink <dir>/mosaic.zarr with your model; with Nieuwlaar's run_ink.sh: run_ink.sh <dir>/mosaic.zarr readerv2 0 <dir>/maps)
  ink-first split  <dir>                     big mosaics: ink <dir>/q0..q3/mosaic.zarr, then
  ink-first stitch <dir> --model readerv2
  ink-first back   --patches <dir>/patches.npz --maps <dir>/maps --mesh <tifxyz> --window r0 r1 c0 c1 --out <npz> [--blend]
  ink-first within --patches ... --inkmaps <dir>/maps --model readerv2 --flat <flattened dir> --meshmaps <maps dir> --out <json>
  ink-first eval   --back <npz> --reference <image> --window ... [--mask <image>] [--cells-mm 0.5 1]
  ink-first stats  --patches ... --map <tif> [--label NAME]
"""
from __future__ import annotations

import argparse
import json
import sys

import numpy as np


def _fetch(a):
    from .fetch import fetch_block
    fetch_block(a.url, a.out, a.level, a.box, a.threads)


def _sample(a):
    from .sample import sample_block
    sample_block(a.ct, a.pred, a.box, a.out, a.thr, a.stride, a.size, a.radius, a.flat, a.margin)


def _split(a):
    from .mosaic import split
    split(a.dir)


def _stitch(a):
    from .mosaic import stitch
    stitch(a.dir, a.model, a.s)


def _back(a):
    from .back import onto_mesh
    out = onto_mesh(a.patches, a.maps, a.mesh, a.window, a.centre, a.radius, a.blend)
    np.savez_compressed(a.out, **out); print('->', a.out)


def _within(a):
    from .back import onto_renders
    res = onto_renders(a.patches, a.inkmaps, a.model, a.flat, a.meshmaps, a.s, a.ds, a.radius, a.centre)
    json.dump(res, open(a.out, 'w'), indent=1); print('->', a.out)


def _load_image(path: str, shape):
    import cv2, tifffile
    if path.endswith('.zarr') or path.endswith('.zarr/'):
        import zarr
        im = np.asarray(zarr.open(path, mode='r')['0']).astype(np.float32)
    else:
        im = tifffile.imread(path).astype(np.float32) if path.lower().endswith(('.tif', '.tiff')) else cv2.imread(path, 0).astype(np.float32)
    return im


def _eval(a):
    """Crop the reference (and mask) to the mesh window: reference images cover the whole segment on a grid `scale` times
    the tifxyz grid x its cell size (2.4 um references of 9 um meshes: about 3.9)."""
    import cv2
    from .evaluate import auc, best_alignment, density_cells, shift_null
    B = np.load(a.back); H, W = map(int, B['shape']); r0, r1, c0, c1 = a.window; f = a.cell
    ref = _load_image(a.reference, None); s = ref.shape[0] / (a.grid_rows * f)
    crop = lambda im, interp: cv2.resize(im[int(r0 * f * s):int(r1 * f * s), int(c0 * f * s):int(c1 * f * s)], (W, H), interpolation=interp)
    R = crop(ref, cv2.INTER_AREA); R = R / max(R.max(), 1e-6)
    mask = np.ones((H, W), bool) if not a.mask else crop((_load_image(a.mask, None) > 0).astype(np.uint8), cv2.INTER_NEAREST) > 0
    mask[:20] = mask[-20:] = False; mask[:, :20] = mask[:, -20:] = False
    keys = [k for k in B.files if k != 'shape']; cov0 = np.isfinite(B[keys[0]]) & mask
    if a.shift:          # an alignment found independently (e.g. from the mesh-based map): no optimistic bias
        dy, dx = a.shift; how = 'given'
    else:                # searched on the image being scored: slightly optimistic; prefer --shift from an independent map
        dy, dx = best_alignment(B[keys[0]], R, cov0); how = f'searched on {keys[0]} (optimistic; prefer --shift)'
    R = np.roll(np.roll(R, dy, 0), dx, 1); mask = np.roll(np.roll(mask, dy, 0), dx, 1) if a.mask else mask
    print(f'reference shift {dy},{dx} ({how}); covered {cov0.mean():.3f} of the window')
    out = {}
    for k in keys:
        img = B[k]; cov = np.isfinite(img) & mask
        res = shift_null(img, R, cov); res['auc'] = auc(np.nan_to_num(img)[cov], R[cov] >= 0.5)
        res['cells'] = {mm: density_cells(img, R, cov, int(round(mm * 1000 / a.um))) for mm in a.cells_mm}
        out[k] = res
        print(f"{k:22s} AUC {res['auc']:.3f}  r {res['r']:+.3f}  null max {res['null_max']:+.3f}  z {res['z']:+.1f}  " +
              '  '.join(f"cells {mm} mm r {c['r']:+.3f}" for mm, c in res['cells'].items()))
    if a.out:
        json.dump(out, open(a.out, 'w'), indent=1, default=float)


def _stats(a):
    import tifffile
    from .evaluate import STAT_COLS, patch_stats
    P = np.load(a.patches); X = patch_stats(P, tifffile.imread(a.map).astype(np.float32) / 255., a.centre)
    if a.out:
        np.savez_compressed(a.out, stats=X, cols=np.array(STAT_COLS))
    med, p90 = np.median(X, 0), np.percentile(X, 90, 0)
    print(f'{a.label:14s} patches {len(X):5d} | median ' + ' '.join(f'{c} {m:.3f}' for c, m in zip(STAT_COLS, med)) +
          f' | 90th pct sd {p90[1]:.3f} frac50 {p90[3]:.3f}')


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog='ink-first', description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    f = sub.add_parser('fetch', help='download the chunks of a remote zarr level covering a box')
    f.add_argument('--url', required=True); f.add_argument('--out', required=True); f.add_argument('--box', nargs=6, type=int, required=True)
    f.add_argument('--level', default='0'); f.add_argument('--threads', type=int, default=24); f.set_defaults(fn=_fetch)
    s = sub.add_parser('sample', help='cut patches along the sheet normal from a surface prediction into a mosaic')
    s.add_argument('--ct', required=True); s.add_argument('--pred', required=True); s.add_argument('--box', nargs=6, type=int, required=True)
    s.add_argument('--out', required=True); s.add_argument('--thr', type=int, default=128); s.add_argument('--stride', type=int, default=96)
    s.add_argument('--size', type=int, default=256); s.add_argument('--radius', type=int, default=10); s.add_argument('--flat', type=float, default=0.25)
    s.add_argument('--margin', type=int, default=48); s.set_defaults(fn=_sample)
    p = sub.add_parser('split', help='split a big mosaic into quarters for inference'); p.add_argument('dir'); p.set_defaults(fn=_split)
    p = sub.add_parser('stitch', help='stitch the quarters\' ink maps'); p.add_argument('dir'); p.add_argument('--model', required=True)
    p.add_argument('--s', type=int, default=25, help='run_ink.sh layer start (25 = depth 0)'); p.set_defaults(fn=_stitch)
    b = sub.add_parser('back', help='map the ink maps back onto a tifxyz mesh window')
    b.add_argument('--patches', required=True); b.add_argument('--maps', required=True); b.add_argument('--mesh', required=True)
    b.add_argument('--window', nargs=4, type=int, required=True, help='r0 r1 c0 c1 in tifxyz grid cells'); b.add_argument('--out', required=True)
    b.add_argument('--centre', type=int, default=128); b.add_argument('--radius', type=float, default=8.0); b.add_argument('--blend', action='store_true')
    b.set_defaults(fn=_back)
    w = sub.add_parser('within', help='compare with the mesh pipeline on every rendered winding crossing the block')
    for k in ('patches', 'inkmaps', 'model', 'flat', 'meshmaps', 'out'):
        w.add_argument('--' + k, required=True)
    w.add_argument('--s', type=int, default=25); w.add_argument('--ds', type=int, default=2); w.add_argument('--radius', type=float, default=8.0)
    w.add_argument('--centre', type=int, default=128); w.set_defaults(fn=_within)
    e = sub.add_parser('eval', help='evaluate a back-projection against known text')
    e.add_argument('--back', required=True); e.add_argument('--reference', required=True, help='ink reference or labels over the whole segment')
    e.add_argument('--mask', help='supervision mask over the whole segment'); e.add_argument('--window', nargs=4, type=int, required=True)
    e.add_argument('--grid-rows', type=int, required=True, help='rows of the tifxyz grid'); e.add_argument('--cell', type=int, default=20, help='voxels per grid cell')
    e.add_argument('--um', type=float, default=9.362); e.add_argument('--cells-mm', type=float, nargs='*', default=[0.5, 1.0]); e.add_argument('--out')
    e.add_argument('--shift', type=int, nargs=2, metavar=('DY', 'DX'), help='alignment of the reference to the mesh grid, found independently')
    e.set_defaults(fn=_eval)
    t = sub.add_parser('stats', help='per-patch statistics of a raw ink map')
    t.add_argument('--patches', required=True); t.add_argument('--map', required=True); t.add_argument('--centre', type=int, default=192)
    t.add_argument('--label', default=''); t.add_argument('--out'); t.set_defaults(fn=_stats)
    a = ap.parse_args(argv)
    a.fn(a)
    return 0


if __name__ == '__main__':
    sys.exit(main())
