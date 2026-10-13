"""How much of a band's fitted windings is really new sheet? (2026-10-13; the tall-band review found w082-w084 of PHerc0813
exp30k-z10500 on one sheet, so some of what we "searched" was the same papyrus two or three times, and the sheets in
between were never searched.) For every node of every flattened winding mesh (tifxyz) of a fit, the nearest node of any
OTHER winding of the same fit, and the distance from this node to that winding's surface along its normal: under
`--same-mm` (0.03 mm, about 3 voxels) the two windings sit on the same sheet there. Lateral distance must be under one
node spacing so that a merely nearby sheet does not count.
Per winding: the share of its area that duplicates another winding, and which. Per fit: total area, area on sheets no
earlier winding already covers ("unique"), and the duplicated share. Writes <out>.tsv (per winding) and prints a summary.
Usage: geometry_coverage.py <scroll dir> <fit> <um> <out prefix> [--same-mm 0.03]"""
import argparse, json, os
import numpy as np, tifffile
from scipy.spatial import cKDTree

ap = argparse.ArgumentParser()
ap.add_argument('sdir'); ap.add_argument('fit'); ap.add_argument('um', type=float); ap.add_argument('out')
ap.add_argument('--same-mm', type=float, default=0.03)
a = ap.parse_args()
base = f'{a.sdir}/geometry/{a.fit}/flattened'
ws = sorted(w for w in os.listdir(base) if os.path.isdir(f'{base}/{w}/tifxyz/flatten.tifxyz'))
P, N, Wi, area = [], [], [], {}
for i, w in enumerate(ws):
    d = f'{base}/{w}/tifxyz/flatten.tifxyz'
    X, Y, Z = (tifffile.imread(f'{d}/{k}.tif').astype(np.float64) for k in 'xyz')
    ok = (X > 0) & (Y > 0) & (Z > 0)
    Xi, Xj = np.gradient(X); Yi, Yj = np.gradient(Y); Zi, Zj = np.gradient(Z)
    nx, ny, nz = Yi * Zj - Zi * Yj, Zi * Xj - Xi * Zj, Xi * Yj - Yi * Xj
    nn = np.sqrt(nx ** 2 + ny ** 2 + nz ** 2)
    sp = np.sqrt(Xj ** 2 + Yj ** 2 + Zj ** 2)                               # node spacing along the row, voxels
    good = ok & (nn > 0) & np.isfinite(nn)
    good[1:-1, 1:-1] &= ok[:-2, 1:-1] & ok[2:, 1:-1] & ok[1:-1, :-2] & ok[1:-1, 2:]
    good[[0, -1], :] = False; good[:, [0, -1]] = False
    P.append(np.stack([X[good], Y[good], Z[good]], 1)); N.append(np.stack([nx[good], ny[good], nz[good]], 1) / nn[good][:, None])
    Wi.append(np.full(int(good.sum()), i)); area[w] = float(nn[good].sum()) * (a.um / 1000.) ** 2      # mm2 (|t_i x t_j| per node)
P, N, Wi = np.concatenate(P), np.concatenate(N), np.concatenate(Wi)
spacing = float(np.median(np.linalg.norm(np.diff(P[:2000], axis=0), axis=1)))
tree = cKDTree(P); same_vx = a.same_mm * 1000 / a.um
print(f'{a.fit}: {len(ws)} windings, {len(P)} mesh nodes; same-sheet threshold {same_vx:.1f} voxels', flush=True)
k = 12
dist, idx = tree.query(P, k=k, distance_upper_bound=25.0)
dup_of = np.full(len(P), -1)
for c in range(1, k):
    j = idx[:, c]; have = np.isfinite(dist[:, c]) & (dup_of < 0)
    jj = np.where(have, j, 0); other = have & (Wi[jj] != Wi)
    d = P[jj] - P; perp = np.abs((d * N[jj]).sum(1)); lat = np.sqrt(np.maximum((d * d).sum(1) - perp ** 2, 0))
    hit = other & (perp < same_vx) & (lat < 25.0)
    dup_of[hit] = Wi[jj[hit]]
rows = []; uniq_nodes = 0
for i, w in enumerate(ws):
    m = Wi == i; n = int(m.sum()); dup = dup_of[m] >= 0
    earlier = dup & (dup_of[m] < i)                                         # duplicates of a lower-numbered winding
    uniq_nodes += n - int(earlier.sum())
    partners = {}
    for p in dup_of[m][dup]:
        partners[ws[p]] = partners.get(ws[p], 0) + 1
    top = ', '.join(f'{p} {c / n:.0%}' for p, c in sorted(partners.items(), key=lambda t: -t[1])[:3])
    rows.append((w, n, area[w], float(dup.mean()) if n else 0.0, top))
with open(f'{a.out}.tsv', 'w') as fo:
    fo.write('winding\tnodes\tarea_mm2\tshared_share\tshared_with\n')
    for w, n, ar, s, top in rows:
        fo.write(f'{w}\t{n}\t{ar:.1f}\t{s:.3f}\t{top}\n')
tot = sum(r[2] for r in rows); sh = sum(r[2] * r[3] for r in rows) / max(tot, 1e-9)
print(f'total mesh area {tot / 100:.1f} cm2; {sh:.1%} of it lies on a sheet another winding of the fit also covers; '
      f'unique sheet area about {uniq_nodes / len(P) * tot / 100:.1f} cm2 ({uniq_nodes / len(P):.1%})')
worst = sorted(rows, key=lambda r: -r[3])[:12]
print('most-shared windings: ' + '; '.join(f'{w} {s:.0%} ({top})' for w, n, ar, s, top in worst if s > 0.05))
json.dump(dict(fit=a.fit, windings=len(ws), nodes=int(len(P)), area_cm2=tot / 100, shared_share=sh, unique_share=uniq_nodes / len(P),
               same_mm=a.same_mm), open(f'{a.out}.json', 'w'), indent=1)
