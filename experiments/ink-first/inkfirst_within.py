"""Ink first, within-scroll test: map an ink-first block onto every rendered winding that crosses it, and compare with the
mesh pipeline's map of that winding at the same pixels. The winding meshes are the flattened tifxyz that were rendered; every
render pixel (at 1/--ds resolution) has a 3D position, and each ink-first patch pixel goes to the nearest render pixel within
--radius voxels. Per winding: coverage, correlation ink first vs mesh based (both layer orders), and the hottest ink-first
2 mm tiles with the mesh-based value there. Also writes side-by-side crops for the best-covered windings.
Usage: inkfirst_within.py <patches.npz> <ink map dir> <model> <flattened dir> <mesh maps dir> <depth s> <out dir> [--ds 2] [--radius 8]"""
import argparse, glob, json, os
import cv2, numpy as np, tifffile
from scipy.spatial import cKDTree

ap = argparse.ArgumentParser()
for k in ('patches', 'inkmaps', 'model', 'flat', 'meshmaps'):
    ap.add_argument(k)
ap.add_argument('s', type=int); ap.add_argument('out')
ap.add_argument('--ds', type=int, default=2); ap.add_argument('--radius', type=float, default=8.0); ap.add_argument('--centre', type=int, default=128)
a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
P = np.load(a.patches); S = int(P['size']); C = a.centre; o = (S - C) // 2
box = P['box']; lo = np.array([box[0], box[2], box[4]]); hi = np.array([box[1], box[3], box[5]])

# 1. render pixels (1/ds) of every winding whose mesh enters the block
pts, owner, pix, wins = [], [], [], []
for d in sorted(glob.glob(os.path.join(a.flat, 'w*', 'tifxyz', 'flatten.tifxyz'))):
    w = d.split(os.sep)[-3]
    mp = os.path.join(a.meshmaps, f'{w}__{a.model}__L66s{a.s}_reverse.tif')
    if not os.path.exists(mp):
        continue
    X, Y, Z = [tifffile.imread(os.path.join(d, f'{k}.tif')).astype(np.float32) for k in 'xyz']
    v = X > 0
    if not v.any():
        continue
    inb = v & (Z >= lo[0]) & (Z < hi[0]) & (Y >= lo[1]) & (Y < hi[1]) & (X >= lo[2]) & (X < hi[2])
    if inb.sum() < 50:
        continue
    H, W = tifffile.TiffFile(mp).pages[0].shape
    f = H / X.shape[0]; h, wd = H // a.ds, W // a.ds
    up = lambda g: cv2.resize(g, (wd, h), interpolation=cv2.INTER_LINEAR)
    vv = cv2.resize(inb.astype(np.uint8), (wd, h), interpolation=cv2.INTER_NEAREST) > 0
    zz, yy, xx = up(Z), up(Y), up(X)
    rr, cc = np.nonzero(vv)
    pts.append(np.stack([zz[rr, cc], yy[rr, cc], xx[rr, cc]], 1)); owner.append(np.full(len(rr), len(wins))); pix.append(np.stack([rr, cc], 1))
    wins.append(dict(w=w, shape=(h, wd), map=mp, f=f))
    print(f'{w}: {len(rr)} render pixels in the block', flush=True)
pts = np.concatenate(pts); owner = np.concatenate(owner); pix = np.concatenate(pix)
tree = cKDTree(pts)
print(f'{len(wins)} windings, {len(pts)} render pixels in the block', flush=True)

# 2. ink-first values onto them
ii, jj = np.mgrid[o:o + C, o:o + C].astype(np.float32) - (S - 1) / 2
res = {}
for order, suf in (('forward', ''), ('reverse', '_reverse')):
    M = tifffile.imread(os.path.join(a.inkmaps, f'mosaic__{a.model}__L66s25{suf}.tif')).astype(np.float32) / 255.
    acc = np.zeros(len(pts)); cnt = np.zeros(len(pts))
    for (R_, C_), c, u, v in zip(P['rowcol'], P['centre'], P['u'], P['v']):
        val = M[R_ * S + o:R_ * S + o + C, C_ * S + o:C_ * S + o + C].ravel()
        q = c[None, :] + u[None, :] * ii.ravel()[:, None] + v[None, :] * jj.ravel()[:, None]
        dd, k = tree.query(q, distance_upper_bound=a.radius); ok = np.isfinite(dd)
        np.add.at(acc, k[ok], val[ok]); np.add.at(cnt, k[ok], 1)
    res[order] = np.where(cnt > 0, acc / np.maximum(cnt, 1), np.nan)

# 3. per winding: compare with the mesh-based map at the same pixels; hottest ink-first tiles
tile = max(4, int(round(2000 / 9.362 / a.ds)))                                  # 2 mm tiles
summary, hot = [], []
for k, W_ in enumerate(wins):
    m = owner == k; rc = pix[m]
    mesh = tifffile.imread(W_['map']).astype(np.float32) / 255.
    mesh = cv2.resize(mesh, (W_['shape'][1], W_['shape'][0]), interpolation=cv2.INTER_AREA)[rc[:, 0], rc[:, 1]]
    row = dict(w=W_['w'], pixels=int(m.sum()))
    for order in ('forward', 'reverse'):
        val = res[order][m]; ok = np.isfinite(val)
        row[f'cov_{order}'] = round(float(ok.mean()), 3)
        row[f'r_{order}'] = round(float(np.corrcoef(val[ok], mesh[ok])[0, 1]), 3) if ok.sum() > 500 else None
    summary.append(row)
    # tiles (forward order): mean ink-first and mesh-based value per 2 mm tile with >= 50 % coverage
    val = res['forward'][m]; ok = np.isfinite(val)
    key = (rc[:, 0] // tile) * 100000 + rc[:, 1] // tile
    for t in np.unique(key[ok]):
        sel = key == t
        if ok[sel].mean() < 0.5 or sel.sum() < 0.25 * tile * tile:
            continue
        hot.append(dict(w=W_['w'], tile_row=int(t // 100000), tile_col=int(t % 100000), inkfirst=float(np.nanmean(val[sel])),
                        inkfirst_sd=float(np.nanstd(val[sel])), mesh=float(mesh[sel].mean()), mesh_sd=float(mesh[sel].std()), n=int(sel.sum())))
hot.sort(key=lambda x: -x['inkfirst_sd'])
json.dump(dict(windings=summary, hottest=hot[:40], tile_px=tile * a.ds), open(os.path.join(a.out, 'within.json'), 'w'), indent=1)
for row in summary:
    print(row)
if hot:
    sd_i = np.array([h_['inkfirst_sd'] for h_ in hot]); sd_m = np.array([h_['mesh_sd'] for h_ in hot])
    print(f'{len(hot)} tiles; tile-level correlation of contrast ink first vs mesh based: {np.corrcoef(sd_i, sd_m)[0, 1]:+.3f}')
    print('hottest ink-first tiles (w, row, col, ink-first sd, mesh sd):')
    for h_ in hot[:12]:
        print(f"  {h_['w']} {h_['tile_row']:3d} {h_['tile_col']:3d}  {h_['inkfirst_sd']:.3f}  {h_['mesh_sd']:.3f}")
np.savez_compressed(os.path.join(a.out, 'within.npz'), pts=pts.astype(np.float32), owner=owner, pix=pix, forward=res['forward'].astype(np.float32),
                    reverse=res['reverse'].astype(np.float32), wins=np.array([w_['w'] for w_ in wins]))
print('->', a.out)
