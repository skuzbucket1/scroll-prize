"""Ink first, geometry second (prototype): cut 66-layer patches along the local sheet normal at points sampled on a surface
prediction, with no mesh, and tile them into one mosaic "render" that run_ink.sh can ink unchanged.
- surface points: voxels of the prediction >= --thr, one per --stride^3 cell (the point nearest the cell's mean)
- normal: smallest-variance direction of the prediction's voxels within --radius; signed to point out of the papyrus
  (the CT is brighter 3 voxels behind the point than 3 voxels in front)
- patch: --size x --size pixels in the tangent plane, 66 layers at (k - 32.5) voxels along the normal (as render66.sh)
Writes <out>/mosaic.zarr (66, H, W) uint8 and <out>/patches.npz (centre, normal, u, v, mosaic row/col of every patch).
Usage: inkfirst_patches.py <ct.zarr> <pred.zarr> <z0 z1 y0 y1 x0 x1> <out dir> [--thr 128] [--stride 96] [--size 256] [--radius 10]"""
import argparse, os, time
import numpy as np, zarr
from scipy.ndimage import map_coordinates

ap = argparse.ArgumentParser()
ap.add_argument('ct'); ap.add_argument('pred'); ap.add_argument('box', nargs=6, type=int); ap.add_argument('out')
ap.add_argument('--thr', type=int, default=128); ap.add_argument('--stride', type=int, default=96)
ap.add_argument('--size', type=int, default=256); ap.add_argument('--radius', type=int, default=10)
ap.add_argument('--margin', type=int, default=48, help='keep points this far inside the block')
a = ap.parse_args()
z0, z1, y0, y1, x0, x1 = a.box; os.makedirs(a.out, exist_ok=True); t0 = time.time()
ct = np.asarray(zarr.open(a.ct, mode='r')['0'][z0:z1, y0:y1, x0:x1])
pr = np.asarray(zarr.open(a.pred, mode='r')['0'][z0:z1, y0:y1, x0:x1])
print(f'block {ct.shape}, CT nonzero {np.mean(ct > 0):.2f}, prediction >= {a.thr}: {np.mean(pr >= a.thr):.4f} ({time.time() - t0:.0f}s)', flush=True)

# 1. one surface point per stride^3 cell
pts = np.argwhere(pr >= a.thr)
m = a.margin
pts = pts[np.all((pts >= m) & (pts < np.array(pr.shape) - m), axis=1)]
cell = pts // a.stride
key = np.ravel_multi_index(cell.T, tuple(np.array(pr.shape) // a.stride + 1))
order = np.argsort(key); key, pts = key[order], pts[order]
starts = np.r_[0, np.nonzero(np.diff(key))[0] + 1]; ends = np.r_[starts[1:], len(key)]
centres = []
for s_, e_ in zip(starts, ends):
    if e_ - s_ < 20:
        continue
    grp = pts[s_:e_]; mu = grp.mean(0)
    centres.append(grp[np.argmin(((grp - mu) ** 2).sum(1))])
centres = np.array(centres)
print(f'{len(centres)} surface points', flush=True)

# 2. normals from the local spread of the prediction, signed out of the papyrus
r = a.radius; normals, keep = [], []
for i, c in enumerate(centres):
    sl = tuple(slice(max(0, q - r), q + r + 1) for q in c)
    loc = np.argwhere(pr[sl] >= a.thr)
    if len(loc) < 30:
        continue
    w, v = np.linalg.eigh(np.cov((loc - loc.mean(0)).T))
    n = v[:, 0]
    if w[0] > 0.25 * w[1]:                    # not sheet-like here (junction, noise)
        continue
    behind = map_coordinates(ct, (c - 3 * n)[:, None], order=1)[0]; front = map_coordinates(ct, (c + 3 * n)[:, None], order=1)[0]
    normals.append(n if behind >= front else -n); keep.append(i)
centres = centres[keep]; N = np.array(normals)
print(f'{len(centres)} points with a sheet-like neighbourhood ({time.time() - t0:.0f}s)', flush=True)

# 3. tangent bases (u along the scroll axis z where possible, so text rows lie along v) and patches
ez = np.array([1.0, 0, 0])
U = ez - (N @ ez)[:, None] * N
bad = np.linalg.norm(U, axis=1) < 0.3
U[bad] = np.cross(N[bad], [0, 1.0, 0])
U /= np.linalg.norm(U, axis=1, keepdims=True); V = np.cross(N, U)
S = a.size; g = int(np.ceil(np.sqrt(len(centres)))); H = W = g * S
mz = zarr.open_group(os.path.join(a.out, 'mosaic.zarr'), mode='w', zarr_format=2)
arr = mz.create_array('0', shape=(66, H, W), chunks=(66, 256, 256), dtype='u1', fill_value=0)
ii, jj = np.mgrid[0:S, 0:S].astype(np.float32) - (S - 1) / 2
rowcol = []
for p, (c, n, u, v) in enumerate(zip(centres, N, U, V)):
    R_, C_ = divmod(p, g); rowcol.append((R_, C_))
    plane = c[:, None, None] + u[:, None, None] * ii + v[:, None, None] * jj          # (3, S, S)
    stack = np.empty((66, S, S), np.uint8)
    for k in range(66):
        q = plane + n[:, None, None] * (k - 32.5)
        stack[k] = np.clip(map_coordinates(ct, q.reshape(3, -1), order=1, mode='constant', cval=0), 0, 255).reshape(S, S)
    arr[:, R_ * S:(R_ + 1) * S, C_ * S:(C_ + 1) * S] = stack
    if p % 200 == 0:
        print(f'  patch {p}/{len(centres)} ({time.time() - t0:.0f}s)', flush=True)
np.savez_compressed(os.path.join(a.out, 'patches.npz'), centre=centres + np.array([z0, y0, x0]), normal=N, u=U, v=V,
                    rowcol=np.array(rowcol), size=S, box=np.array(a.box))
print(f'mosaic {H} x {W} ({g} x {g} patches of {S}) -> {a.out} in {time.time() - t0:.0f}s')
