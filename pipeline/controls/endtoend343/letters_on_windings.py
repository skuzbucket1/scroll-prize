"""Which of our windings pass through known letters? (2026-10-13; end-to-end positive control)
Letters: letters3d.npz from experiments/ink-first/letters_to_3d.py (zyx samples every 20 render px inside each letter box of
a published segment, with the letter id). For every flattened winding <root>/<w>/tifxyz/flatten.tifxyz: the nearest mesh
node of every sample, the offset split into the component along the winding's local normal and the in-plane rest. A
sample is ON the winding when |normal offset| <= 4 voxels and in-plane <= 15 voxels (nodes are 20 voxels apart).
Writes a TSV sorted by samples on: winding, samples_on, letters_on (ids with >= 30 % of their samples on), median |normal|.
Usage: letters_on_windings.py <letters3d.npz> <flattened root> <out.tsv>"""
import glob, os, sys
import numpy as np, tifffile
from scipy.spatial import cKDTree

L = np.load(sys.argv[1]); P = L['zyx'].astype(np.float64); ids = L['id']; root, out = sys.argv[2], sys.argv[3]


def mesh(d):
    X, Y, Z = (tifffile.imread(os.path.join(d, f'{c}.tif')).astype(np.float64) for c in 'xyz')
    G = np.stack([Z, Y, X], -1); ok = (X > 0) & (Y > 0) & (Z > 0)
    gy = np.gradient(G, axis=0); gx = np.gradient(G, axis=1); n = np.cross(gx, gy)
    n /= np.linalg.norm(n, axis=-1, keepdims=True) + 1e-9
    ok &= np.isfinite(n).all(-1)
    rc = np.argwhere(ok)
    return G[ok], n[ok], rc


def on(d):
    V, N, rc = mesh(d)
    if len(V) < 10:
        return None
    dist, j = cKDTree(V).query(P, distance_upper_bound=60)
    m = np.isfinite(dist); j = np.where(m, j, 0)
    off = P - V[j]; nn = np.abs((off * N[j]).sum(1)); ip = np.sqrt(np.maximum((off ** 2).sum(1) - nn ** 2, 0))
    hit = m & (nn <= 4) & (ip <= 15)
    return hit, nn, rc[j]


rows = []
for f in sorted(glob.glob(os.path.join(root, '*', 'tifxyz', 'flatten.tifxyz'))):
    w = f.split(os.sep)[-3]; r = on(f)
    if r is None:
        continue
    hit, nn, _ = r
    lets = [int(i) for i in np.unique(ids) if hit[ids == i].mean() >= 0.3]
    rows.append((int(hit.sum()), w, lets, float(np.median(nn[hit])) if hit.any() else float('nan')))
rows.sort(reverse=True)
with open(out, 'w') as fh:
    fh.write('winding\tsamples_on\tletters_on\tmedian_abs_normal_vox\n')
    for n, w, lets, med in rows:
        fh.write(f'{w}\t{n}\t{",".join(map(str, lets))}\t{med:.2f}\n')
print(f'{len(rows)} windings; {len(P)} letter samples of {len(np.unique(ids))} letters; best: ' +
      '; '.join(f'{w} {n} samples, letters {lets}' for n, w, lets, _ in rows[:3]))
