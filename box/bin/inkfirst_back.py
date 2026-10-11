"""Ink first, step 2: map the ink-first patch predictions back to 3D and onto a test mesh (where the text is known), for
evaluation. Every pixel in the centre --centre x --centre of a patch sits at centre + (i - c) u + (j - c) v in the volume;
each mesh point (the tifxyz grid upsampled to full resolution over a window) takes the mean ink of the patch pixels within
--radius voxels. Both layer orders are kept: "reverse" (run_ink's reading side) and "forward".
Writes <out>.npz with, per model and order, a mesh-grid ink image (NaN where no patch pixel landed) and the coverage.
Usage: inkfirst_back.py <patches.npz> <maps dir> <mesh.tifxyz> <row0 row1 col0 col1 (tifxyz grid)> <out.npz> [--centre 128] [--radius 3]"""
import argparse, glob, json, os
import cv2, numpy as np, tifffile
from scipy.spatial import cKDTree

ap = argparse.ArgumentParser()
ap.add_argument('patches'); ap.add_argument('maps'); ap.add_argument('mesh'); ap.add_argument('win', nargs=4, type=int); ap.add_argument('out')
ap.add_argument('--centre', type=int, default=128); ap.add_argument('--radius', type=float, default=3.0)
a = ap.parse_args()
P = np.load(a.patches); S = int(P['size']); C = a.centre; o = (S - C) // 2
r0, r1, c0, c1 = a.win
meta = json.load(open(os.path.join(a.mesh, 'meta.json'))); f = int(round(1 / meta['scale'][0]))      # grid step in voxels (20)
X, Y, Z = [tifffile.imread(os.path.join(a.mesh, f'{k}.tif')).astype(np.float32) for k in 'xyz']
H, W = (r1 - r0) * f, (c1 - c0) * f
up = lambda g: cv2.resize(g[r0:r1 + 1, c0:c1 + 1], ((c1 - c0 + 1) * f, (r1 - r0 + 1) * f), interpolation=cv2.INTER_LINEAR)[:H, :W]
mesh = np.stack([up(Z), up(Y), up(X)], -1).reshape(-1, 3)                  # zyx, full resolution over the window
tree = cKDTree(mesh)
ii, jj = np.mgrid[o:o + C, o:o + C].astype(np.float32) - (S - 1) / 2
out = {'shape': np.array([H, W])}
for path in sorted(glob.glob(os.path.join(a.maps, '*.tif'))):
    model = os.path.basename(path).split('__')[1]; order = 'reverse' if path.endswith('_reverse.tif') else 'forward'
    M = tifffile.imread(path).astype(np.float32) / 255.
    acc = np.zeros(len(mesh)); cnt = np.zeros(len(mesh))
    for (R_, C_), c, u, v in zip(P['rowcol'], P['centre'], P['u'], P['v']):
        val = M[R_ * S + o:R_ * S + o + C, C_ * S + o:C_ * S + o + C].reshape(-1)
        pts = (c[None, None, :] + u[None, None, :] * ii[..., None] + v[None, None, :] * jj[..., None]).reshape(-1, 3)
        d, k = tree.query(pts, distance_upper_bound=a.radius)
        ok = np.isfinite(d)
        if ok.any():
            np.add.at(acc, k[ok], val[ok]); np.add.at(cnt, k[ok], 1)
    img = np.where(cnt > 0, acc / np.maximum(cnt, 1), np.nan).reshape(H, W)
    out[f'{model}_{order}'] = img.astype(np.float32)
    print(f'{model} {order}: mesh coverage {np.mean(cnt > 0):.3f}, mean ink where covered {np.nanmean(img):.3f}', flush=True)
np.savez_compressed(a.out, **out)
print('->', a.out)
