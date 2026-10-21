"""Ink first, step 3: mesh-free sheet views. The recto-surface prediction of the block is split into connected sheets (at
1/--ds resolution, 26-connected); each large sheet is flattened onto its best-fit plane (PCA; the axis closest to the scroll
axis z is drawn vertically, so lines of text come out horizontal), and the ink-first patch predictions (per-patch z-score,
Hann-weighted centre) are painted onto it: every patch pixel goes to the nearest sheet within 2 coarse voxels.
Writes <out>/sheet_NN.png (ink, uncovered dark blue), <out>/sheets.json (size, planarity, coverage, w047 share) and
<out>/montage.jpg. A block of ~1.3 cm holds gently curved sheets, so the plane is a fair flattening; folded or fused sheets
show up as low planarity.
Usage: inkfirst_sheets.py <pred.zarr> <z0 z1 y0 y1 x0 x1> <patches.npz> <map.tif> <out dir> [--ds 4] [--px 2] [--top 16] (all options: --help)
       [--centre 192] [--mesh <tifxyz> <r0 r1 c0 c1>]"""
import argparse, json, os
import cv2, numpy as np, tifffile, zarr
from scipy import ndimage

ap = argparse.ArgumentParser()
ap.add_argument('pred'); ap.add_argument('box', nargs=6, type=int); ap.add_argument('patches'); ap.add_argument('map'); ap.add_argument('out')
ap.add_argument('--ds', type=int, default=4); ap.add_argument('--px', type=float, default=2.0); ap.add_argument('--top', type=int, default=16)
ap.add_argument('--centre', type=int, default=192); ap.add_argument('--thr', type=int, default=128)
ap.add_argument('--mesh', nargs=5, help='tifxyz dir + grid window r0 r1 c0 c1: report which sheet holds it')
a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
z0, z1, y0, y1, x0, x1 = a.box; ds = a.ds
pr = np.asarray(zarr.open(a.pred, mode='r')['0'][z0:z1, y0:y1, x0:x1]) >= a.thr
sh = tuple(s // ds * ds for s in pr.shape)
coarse = pr[:sh[0], :sh[1], :sh[2]].reshape(sh[0] // ds, ds, sh[1] // ds, ds, sh[2] // ds, ds).max(axis=(1, 3, 5))
del pr
lab, n = ndimage.label(coarse, structure=np.ones((3, 3, 3)))
size = np.bincount(lab.ravel()); size[0] = 0
order = np.argsort(size)[::-1][:a.top]; order = order[size[order] > 0]
print(f'{n} sheets at 1/{ds}; top {len(order)} sizes {size[order].tolist()}', flush=True)
dist, idx = ndimage.distance_transform_edt(lab == 0, return_indices=True)
near = lab[tuple(idx)]; near[dist > 2] = 0                                    # nearest sheet within 2 coarse voxels
del idx, dist

info = {}
for k in order:
    v = (np.argwhere(lab == k) * ds + ds / 2).astype(np.float64)              # block-local voxel coords (zyx)
    mu = v.mean(0); w, e = np.linalg.eigh(np.cov((v - mu).T))
    e1, e2 = e[:, 2], e[:, 1]                                                  # in-plane axes
    vert, hor = (e1, e2) if abs(e1[0]) >= abs(e2[0]) else (e2, e1)
    vert = vert if vert[0] >= 0 else -vert
    pa, pb = (v - mu) @ hor, (v - mu) @ vert
    info[int(k)] = dict(voxels=int(size[k]), planarity=float(w[0] / w[1]), mu=mu, hor=hor, vert=vert,
                        lo=(pa.min(), pb.min()), shape=(int((pb.max() - pb.min()) / a.px) + 2, int((pa.max() - pa.min()) / a.px) + 2))
acc = {k: np.zeros(info[k]['shape']) for k in info}; cnt = {k: np.zeros(info[k]['shape']) for k in info}

P = np.load(a.patches); S = int(P['size']); C = a.centre; o = (S - C) // 2; box0 = P['box'][[0, 2, 4]]
M = tifffile.imread(a.map).astype(np.float32)
ii, jj = np.mgrid[o:o + C, o:o + C].astype(np.float32) - (S - 1) / 2
hw = np.hanning(C + 2)[1:-1]; WGT = (np.outer(hw, hw) + 0.05).ravel()
cshape = np.array(near.shape)
for (R_, C_), c, u, v in zip(P['rowcol'], P['centre'], P['u'], P['v']):
    val = M[R_ * S + o:R_ * S + o + C, C_ * S + o:C_ * S + o + C].ravel()
    val = (val - val.mean()) / (val.std() + 1e-3)
    pts = (c - box0)[None, :] + (u[None, :] * ii.ravel()[:, None] + v[None, :] * jj.ravel()[:, None])     # block-local zyx
    q = np.clip((pts / ds).astype(int), 0, cshape - 1)
    sheet = near[q[:, 0], q[:, 1], q[:, 2]]
    for k in np.unique(sheet):
        if k == 0 or int(k) not in info:
            continue
        m = sheet == k; I = info[int(k)]; d = pts[m] - I['mu']
        cc = ((d @ I['hor'] - I['lo'][0]) / a.px).astype(int); rr = ((d @ I['vert'] - I['lo'][1]) / a.px).astype(int)
        ok = (rr >= 0) & (rr < I['shape'][0]) & (cc >= 0) & (cc < I['shape'][1])
        np.add.at(acc[int(k)], (rr[ok], cc[ok]), val[m][ok] * WGT[m][ok]); np.add.at(cnt[int(k)], (rr[ok], cc[ok]), WGT[m][ok])

w047 = {}
if a.mesh:
    md = a.mesh[0]; r0, r1, c0, c1 = map(int, a.mesh[1:])
    X, Y, Z = [tifffile.imread(os.path.join(md, f'{t}.tif'))[r0:r1, c0:c1] for t in 'xyz']
    mp = np.stack([Z, Y, X], -1).reshape(-1, 3) - box0
    q = np.clip((mp / ds).astype(int), 0, cshape - 1); s_ = near[q[:, 0], q[:, 1], q[:, 2]]
    w047 = {int(k): float(np.mean(s_ == k)) for k in np.unique(s_) if k}

tiles, out = [], {}
for rank, k in enumerate(info):
    I = info[k]; img = np.where(cnt[k] > 0, acc[k] / np.where(cnt[k] > 0, cnt[k], 1), np.nan)
    cov = float(np.mean(cnt[k] > 0)); share = w047.get(k, 0.0)
    out[k] = dict(rank=rank, voxels=I['voxels'], planarity=round(I['planarity'], 4), size_mm=[round(s * a.px * 9.362e-3, 1) for s in I['shape']],
                  coverage=round(cov, 3), w047_share=round(share, 3))
    lo, hi = (np.nanpercentile(img, [1, 99.5]) if np.isfinite(img).any() else (0, 1))
    g = (np.clip((np.nan_to_num(img, nan=lo) - lo) / max(hi - lo, 1e-6), 0, 1) * 255).astype(np.uint8)
    g = cv2.GaussianBlur(g, (0, 0), 1.0); rgb = cv2.cvtColor(g, cv2.COLOR_GRAY2BGR); rgb[cnt[k] == 0] = (70, 40, 40)
    cv2.imwrite(os.path.join(a.out, f'sheet_{rank:02d}.png'), rgb)
    t = cv2.resize(rgb, (360, int(360 * rgb.shape[0] / rgb.shape[1])) if rgb.shape[1] >= rgb.shape[0] else (int(360 * rgb.shape[1] / rgb.shape[0]), 360))
    tile = np.zeros((384, 360, 3), np.uint8); tile[24:24 + t.shape[0], :t.shape[1]] = t[:360]
    cv2.putText(tile, f'#{rank} cov {cov:.2f} plan {I["planarity"]:.3f}' + (f' w047 {share:.0%}' if share > 0.05 else ''), (4, 16),
                cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1, cv2.LINE_AA)
    tiles.append(tile)
    print(f'sheet #{rank}: {I["voxels"]} coarse voxels, planarity {I["planarity"]:.3f}, {out[k]["size_mm"]} mm, coverage {cov:.2f}, w047 share {share:.2f}', flush=True)
while len(tiles) % 4:
    tiles.append(np.zeros_like(tiles[0]))
cv2.imwrite(os.path.join(a.out, 'montage.jpg'), np.concatenate([np.concatenate(tiles[i:i + 4], 1) for i in range(0, len(tiles), 4)], 0))
json.dump({str(k): v for k, v in out.items()}, open(os.path.join(a.out, 'sheets.json'), 'w'), indent=1)
print('->', a.out)
