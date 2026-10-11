"""Full-resolution look at one row window, in reading orientation (rotated 180 degrees from the render): the reading-side
ensemble, the blind side with the same stretch, and the CT layer 33+d, stacked, for judging letters by eye. The same code
on a known-text control gives the reference at the same scale.
Usage: candidate_view.py <maps dir> <name> <models,> <depth> <y0> <x0> <out.jpg> [render.zarr] [--h-mm 12] [--w-mm 20]"""
import argparse, os, sys
import cv2, numpy as np, tifffile
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, 'stroke-score-src'))
from stroke_score.core import ensemble

ap = argparse.ArgumentParser()
for k in ('maps', 'name', 'models'):
    ap.add_argument(k)
ap.add_argument('depth', type=int); ap.add_argument('y0', type=int); ap.add_argument('x0', type=int); ap.add_argument('out')
ap.add_argument('render', nargs='?'); ap.add_argument('--h-mm', type=float, default=12.0); ap.add_argument('--w-mm', type=float, default=20.0)
ap.add_argument('--um', type=float, default=9.362); ap.add_argument('--label', default='')
a = ap.parse_args()
s = 25 + a.depth
paths = {m: (f'{a.maps}/{a.name}__{m}__L66s{s}_reverse.tif', f'{a.maps}/{a.name}__{m}__L66s{s}.tif') for m in a.models.split(',')}
valid = None
for p, q in paths.values():
    v = (tifffile.imread(p) > 0) | (tifffile.imread(q) > 0); valid = v if valid is None else valid & v
E, _ = ensemble(paths, valid)
h, w = int(a.h_mm * 1000 / a.um), int(a.w_mm * 1000 / a.um)
H, W = valid.shape
x0 = max(0, min(a.x0, W - w))
if a.y0 < 0:                                  # centre the crop on the band in this x range
    ys = np.nonzero(valid[:, x0:x0 + w].mean(1) > 0.3)[0]
    a.y0 = int((ys.min() + ys.max()) / 2 - h / 2) if ys.size else 0
y0 = max(0, min(a.y0, H - h))
lo, hi = np.percentile(E['reading'][valid], [1, 99.7])
panels = []
for side in ('reading', 'blind'):
    c = cv2.GaussianBlur(E[side], (0, 0), 1.5)[y0:y0 + h, x0:x0 + w]
    im = np.clip((c - lo) / (hi - lo) * 255, 0, 255).astype(np.uint8); im[~valid[y0:y0 + h, x0:x0 + w]] = 0
    panels.append((im[::-1, ::-1], f'{a.label} {side.upper()} (reading orientation)'))
if a.render:
    import zarr
    ct = np.asarray(zarr.open(a.render, mode='r')['0'][33 + a.depth, y0:y0 + h, x0:x0 + w]).astype(np.float32)
    vv = ct[ct > 0]; clo, chi = np.percentile(vv, [1, 99.5]) if vv.size else (0, 255)
    panels.append((np.clip((ct - clo) / max(chi - clo, 1) * 255, 0, 255).astype(np.uint8)[::-1, ::-1], f'{a.label} CT layer {33 + a.depth}'))
WD = 1600; rows = []
for im, t in panels:
    im = cv2.resize(im, (WD, int(im.shape[0] * WD / im.shape[1])), interpolation=cv2.INTER_AREA)
    c = np.zeros((im.shape[0] + 26, WD), np.uint8); c[26:] = im
    cv2.putText(c, t, (6, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.6, 255, 1, cv2.LINE_AA)
    cv2.line(c, (WD - 6 - int(5000 / a.um * WD / w), 20), (WD - 6, 20), 255, 2)   # 5 mm scale bar
    rows.append(c)
cv2.imwrite(a.out, np.concatenate(rows, 0), [cv2.IMWRITE_JPEG_QUALITY, 90])
print(a.out, f'crop y {y0}:{y0 + h} x {x0}:{x0 + w} (render px)')
