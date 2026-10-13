"""Picture of two windings on one sheet (2026-10-13, check of geometry_coverage.py by eye). A CT slice (level 0) around a
mesh node of winding <w> that geometry_coverage.py counts as shared, with the intersections of the neighbouring
windings' meshes with that slice drawn in colour: if the fit put two windings on the same sheet, their dots overlap on
one bright band, and a sheet with no dots next to them was never fitted.
Usage: coverage_view.py <scroll dir> <fit> <volume.zarr> <winding> <out.jpg> [--half 300] [--around 4]"""
import argparse, os
import cv2, numpy as np, tifffile, zarr
from scipy.spatial import cKDTree

ap = argparse.ArgumentParser()
for k in ('sdir', 'fit', 'vol', 'w', 'out'):
    ap.add_argument(k)
ap.add_argument('--half', type=int, default=300); ap.add_argument('--around', type=int, default=4)
a = ap.parse_args()
base = f'{a.sdir}/geometry/{a.fit}/flattened'
ws = sorted(w for w in os.listdir(base) if os.path.isdir(f'{base}/{w}/tifxyz/flatten.tifxyz'))
i0 = ws.index(a.w); near = ws[max(0, i0 - a.around):i0 + a.around + 1]
mesh = {}
for w in near:
    X, Y, Z = (tifffile.imread(f'{base}/{w}/tifxyz/flatten.tifxyz/{k}.tif').astype(np.float64) for k in 'xyz')
    ok = (X > 0) & (Y > 0) & (Z > 0); mesh[w] = np.stack([X[ok], Y[ok], Z[ok]], 1)
# a node of <w> that lies within 1 voxel of another winding's node cloud (a shared spot)
others = np.concatenate([mesh[w] for w in near if w != a.w]); t = cKDTree(others)
d, _ = t.query(mesh[a.w], distance_upper_bound=12)
cand = np.flatnonzero(d < 6)
if not len(cand):
    raise SystemExit(f'{a.w}: no shared node found')
p = mesh[a.w][cand[len(cand) // 2]]; x0, y0, z = int(p[0]), int(p[1]), int(round(p[2]))
V = zarr.open(a.vol, mode='r')['0']; h = a.half
ct = np.asarray(V[z, max(0, y0 - h):y0 + h, max(0, x0 - h):x0 + h]).astype(np.float32)
lo, hi = np.percentile(ct[ct > 0], [1, 99.5]) if (ct > 0).any() else (0, 255)
g = cv2.cvtColor((np.clip((ct - lo) / (hi - lo + 1e-6), 0, 1) * 255).astype(np.uint8), cv2.COLOR_GRAY2BGR)
g = cv2.resize(g, (g.shape[1] * 2, g.shape[0] * 2), interpolation=cv2.INTER_NEAREST)
cols = [(255, 80, 80), (80, 200, 255), (80, 255, 120), (255, 200, 60), (220, 90, 255), (60, 140, 255), (255, 255, 255),
        (160, 255, 255), (255, 140, 200)]
leg = []
for k, w in enumerate(near):
    m = mesh[w]; s = m[np.abs(m[:, 2] - z) < 10]
    s = s[(np.abs(s[:, 0] - x0) < h) & (np.abs(s[:, 1] - y0) < h)]
    c = cols[k % len(cols)]
    for q in s:
        cv2.circle(g, (int((q[0] - (x0 - h)) * 2), int((q[1] - (y0 - h)) * 2)), 3 if w != a.w else 4, c, -1 if w != a.w else 1)
    leg.append((w, c, len(s)))
g = cv2.copyMakeBorder(g, 28 + 18 * len(leg), 0, 0, 0, cv2.BORDER_CONSTANT, value=(22, 22, 22))
cv2.putText(g, f'{a.fit} z {z}: CT slice {2 * h} x {2 * h} voxels around a shared node of {a.w}; dots = mesh nodes within 10 slices',
            (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
for k, (w, c, n) in enumerate(leg):
    cv2.putText(g, f'{w} ({n} nodes)' + (' <- this winding (open circles)' if w == a.w else ''), (8, 40 + 18 * k),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, c, 1, cv2.LINE_AA)
cv2.imwrite(a.out, g, [cv2.IMWRITE_JPEG_QUALITY, 90]); print('written', a.out, 'z', z, 'x', x0, 'y', y0)
