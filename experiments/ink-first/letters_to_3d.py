"""Put letter boxes drawn on a tifxyz render back into the scan, and pick the ink-first block that holds the most of them.
Boxes are [x0, y0, x1, y1] in render pixels (x = column, y = row; the render at the mesh's own scale: node = pixel *
scale). Each box is sampled every `step` pixels; a sample counts when the four mesh nodes around it are valid, and its
3D position is the bilinear blend of theirs. The block is the `size`^3 cube (level-0 voxels) holding the most samples.
Writes <out>/blocks.tsv (the one block, in the format of inkfirst_plan.py) and <out>/letters3d.npz (samples: zyx, letter
id, render row/col; and the mesh nodes, for mapping patches back onto the render).
Usage: letters_to_3d.py <mesh.tifxyz> <letter_boxes.json> <out dir> [--size 1280] [--step 20] [--id b343] (all options: --help)
       [--shape Z Y X (volume, to keep the block inside)]"""
import argparse, json, os
import numpy as np, tifffile

ap = argparse.ArgumentParser()
ap.add_argument('mesh'); ap.add_argument('boxes'); ap.add_argument('out')
ap.add_argument('--size', type=int, default=1280); ap.add_argument('--step', type=float, default=20.0); ap.add_argument('--id', default='b343')
ap.add_argument('--shape', type=int, nargs=3)
a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
X, Y, Z = (tifffile.imread(os.path.join(a.mesh, f'{k}.tif')).astype(np.float64) for k in 'xyz')
sc = json.load(open(os.path.join(a.mesh, 'meta.json')))['scale']; sr, sc_ = float(sc[1]), float(sc[0])   # [col, row] scale
valid = (X >= 0) & (Y >= 0) & (Z >= 0)
H, W = X.shape


def at(row_px, col_px):
    """zyx of render pixel (row, col), or None where the mesh has no valid cell."""
    r, c = row_px * sr, col_px * sc_; r0, c0 = int(np.floor(r)), int(np.floor(c))
    if r0 < 0 or c0 < 0 or r0 + 1 >= H or c0 + 1 >= W or not valid[r0:r0 + 2, c0:c0 + 2].all():
        return None
    fr, fc = r - r0, c - c0
    w = np.array([(1 - fr) * (1 - fc), (1 - fr) * fc, fr * (1 - fc), fr * fc])
    pick = lambda G: float(w @ np.array([G[r0, c0], G[r0, c0 + 1], G[r0 + 1, c0], G[r0 + 1, c0 + 1]]))
    return pick(Z), pick(Y), pick(X)


L = json.load(open(a.boxes))['letters']
pts, ids, rc = [], [], []
for l in L:
    x0, y0, x1, y1 = l['box']
    for yy in np.arange(y0, y1 + 1e-6, a.step):
        for xx in np.arange(x0, x1 + 1e-6, a.step):
            p = at(yy, xx)
            if p is not None:
                pts.append(p); ids.append(l['id']); rc.append((yy, xx))
pts, ids, rc = np.array(pts), np.array(ids), np.array(rc)
print(f'{len(L)} letters, {len(pts)} samples on the mesh; letters span z {pts[:, 0].min():.0f}-{pts[:, 0].max():.0f}, '
      f'y {pts[:, 1].min():.0f}-{pts[:, 1].max():.0f}, x {pts[:, 2].min():.0f}-{pts[:, 2].max():.0f}')
h = a.size / 2
inside = lambda c: (np.abs(pts - c) <= h - 48).all(1)                      # 48 = the sampler's margin
best = max(range(len(pts)), key=lambda i: (inside(pts[i]).sum(), len(set(ids[inside(pts[i])]))))
c = pts[best]; c2 = pts[inside(c)].mean(0)
if inside(c2).sum() >= inside(c).sum():
    c = c2
lo = np.round(c - h).astype(int)
if a.shape:
    lo = np.clip(lo, 0, np.array(a.shape) - a.size)
hi = lo + a.size; m = (pts >= lo + 48).all(1) & (pts < hi - 48).all(1)
full = [l['id'] for l in L if (m[ids == l['id']].all() and (ids == l['id']).any())]
part = [l['id'] for l in L if m[ids == l['id']].any() and l['id'] not in full]
print(f'block {a.id}: z {lo[0]}-{hi[0]}, y {lo[1]}-{hi[1]}, x {lo[2]}-{hi[2]}; {m.sum()} of {len(pts)} samples inside; '
      f'letters fully inside {full}, partly {part}')
with open(os.path.join(a.out, 'blocks.tsv'), 'w') as f:
    f.write('id\tz0\tz1\ty0\ty1\tx0\tx1\toccupancy\n')
    f.write(f'{a.id}\t{lo[0]}\t{hi[0]}\t{lo[1]}\t{hi[1]}\t{lo[2]}\t{hi[2]}\tnan\n')
np.savez_compressed(os.path.join(a.out, 'letters3d.npz'), zyx=pts, id=ids, rowcol=rc, inside=m, block=np.concatenate([lo, hi]),
                    mesh_z=Z, mesh_y=Y, mesh_x=X, mesh_valid=valid, scale=np.array([sr, sc_]))
