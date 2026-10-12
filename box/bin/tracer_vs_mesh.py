"""How well does a traced surface follow one of our winding meshes? For every valid point of the trace (tifxyz), the distance
to the reference winding and to its neighbouring windings (all upsampled 4x), and which of them is nearest: points that
end up nearer a neighbour have switched sheets.
Usage: tracer_vs_mesh.py <trace tifxyz> <reference winding dir> [<neighbour winding dir> ...]"""
import sys
import cv2, numpy as np, tifffile
from scipy.spatial import cKDTree


def points(d, up=1):
    X, Y, Z = (tifffile.imread(f'{d}/{c}.tif').astype(np.float32) for c in 'xyz')
    ok = (X > 0) & (Y > 0) & (Z > 0)
    if up > 1:
        r = lambda A: cv2.resize(A, (A.shape[1] * up, A.shape[0] * up), interpolation=cv2.INTER_LINEAR)
        ok = cv2.resize(ok.astype(np.uint8), (X.shape[1] * up, X.shape[0] * up), interpolation=cv2.INTER_NEAREST) > 0
        X, Y, Z = r(X), r(Y), r(Z)
    return np.stack([X[ok], Y[ok], Z[ok]], 1), ok


T, okT = points(sys.argv[1]); refs = sys.argv[2:]
D = np.stack([cKDTree(points(d, 4)[0]).query(T)[0] for d in refs], 1)        # distance to each mesh
near = D.argmin(1); d0 = D[:, 0]
print(f'trace: {len(T)} valid points ({okT.mean():.0%} of its grid, {okT.shape[0]} rows)')
for q in (2, 5, 10):
    print(f'  within {q:2d} voxels of {refs[0].rstrip("/").split("/")[-1]}: {np.mean(d0 <= q):.1%}')
print(f'  distance to the reference: median {np.median(d0):.1f}, 90th percentile {np.percentile(d0, 90):.1f} voxels')
for i, d in enumerate(refs[1:], 1):
    print(f'  nearest to neighbour {d.rstrip("/").split("/")[-1]}: {np.mean(near == i):.1%} of points')
rows = np.nonzero(okT)[0]
per_row = [np.median(d0[rows == r]) for r in np.unique(rows)]
print('  median distance per traced row (every 5th):', ' '.join(f'{v:.1f}' for v in per_row[::5]))
