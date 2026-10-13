"""Summary of an older ink-first block (the 2026-10-11 prototype: patches.npz and maps/ kept, CT mosaic deleted) in the
format of inkfirst_block_summary.py, so the scroll map and the cluster view run on known-text and text-free reference
blocks exactly as on a sweep: centre/normal/u/v, ct64 (the surface layer, layer 33, re-cut from the CT at 2 voxel
spacing over the central `centre` pixels), air (share of ct64 darker than half the block's median papyrus intensity),
stats_<m>_<order> (mean, sd, frac50 over the centre) and ink64_<m>_<order>.
Usage: inkfirst_ref_summary.py <block dir with patches.npz and maps/> <CT zarr (level 0 in volume coordinates)> <out dir>
       [--models readerv2] [--centre 128]"""
import argparse, os
import cv2, numpy as np, tifffile, zarr
from scipy.ndimage import map_coordinates

ap = argparse.ArgumentParser()
ap.add_argument('blk'); ap.add_argument('ct'); ap.add_argument('out')
ap.add_argument('--models', default='readerv2'); ap.add_argument('--centre', type=int, default=128)
a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
P = np.load(os.path.join(a.blk, 'patches.npz')); S, C = int(P['size']), a.centre; o = (S - C) // 2
z0, z1, y0, y1, x0, x1 = map(int, P['box']); pad = S
lo = np.array([max(0, z0 - pad), max(0, y0 - pad), max(0, x0 - pad)])
ct = np.asarray(zarr.open(a.ct, mode='r')['0'][lo[0]:z1 + pad, lo[1]:y1 + pad, lo[2]:x1 + pad])
g = np.arange(C // 2, dtype=np.float32) * 2 - (C - 2) / 2                    # 64 samples over the central 128 pixels
ii, jj = np.meshgrid(g, g, indexing='ij')
ct64 = []
for c, n, u, v in zip(P['centre'], P['normal'], P['u'], P['v']):
    q = (c - lo)[:, None, None] + u[:, None, None] * ii + v[:, None, None] * jj + 0.5 * n[:, None, None]
    ct64.append(np.clip(map_coordinates(ct, q.reshape(3, -1), order=1, mode='constant', cval=0), 0, 255).reshape(len(g), len(g)))
ct64 = np.stack(ct64).astype(np.uint8)
nz = ct64[ct64 > 0]; dark = 0.5 * float(np.median(nz)) if nz.size else 0.0
out = dict(centre=P['centre'], normal=P['normal'], u=P['u'], v=P['v'], box=P['box'], size=S, centre_px=C,
           models=np.array(a.models.split(',')), ct64=ct64, air=(ct64 < dark).mean((1, 2)).astype(np.float32))
for m in a.models.split(','):
    for order, suf in (('fwd', ''), ('rev', '_reverse')):
        f = os.path.join(a.blk, 'maps', f'mosaic__{m}__L66s25{suf}.tif')
        if not os.path.exists(f):
            continue
        M = tifffile.imread(f)
        cent = [M[r * S + o:r * S + o + C, c * S + o:c * S + o + C].astype(np.float32) / 255. for r, c in P['rowcol']]
        out[f'stats_{m}_{order}'] = np.array([[x.mean(), x.std(), (x >= 0.5).mean()] for x in cent], np.float32)
        out[f'ink64_{m}_{order}'] = np.stack([cv2.resize((x * 255).astype(np.uint8), (64, 64), interpolation=cv2.INTER_AREA) for x in cent])
np.savez_compressed(os.path.join(a.out, 'summary.npz'), **out)
print(f'{a.blk}: {len(ct64)} patches ({int((out["air"] <= 0.3).sum())} plausible) -> {a.out}/summary.npz')
