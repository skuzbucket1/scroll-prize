"""Keep the small part of one ink-first block: per-patch geometry and ink statistics, a compact 64 x 64 thumbnail of each
patch (CT surface layer and ink, both layer orders), the hottest patches at full resolution, and a gallery image of them.
The big inputs (CT and prediction blocks, the 66-layer mosaic, full ink maps) can be deleted afterwards.
Stats per patch, on its central `centre` x `centre` pixels, ink probability p = map / 255: mean, sd, frac50 (share >= 0.5).
Plausibility per patch, from the CT: `air` = share of the centre darker than half the block's median papyrus intensity
(gaps, cracks); `layer_corr` = correlation of CT layers 31 and 35 over the centre, recorded but not used: at 9 um the
texture decorrelates within 4 voxels even for patches lying in their sheet (median 0.07 on PHerc0175A). Galleries: the
hottest patches by frac50, and the hottest among plausible ones (air <= 0.3).
Usage: inkfirst_block_summary.py <block dir with patches.npz, mosaic.zarr, maps/> <out dir> <id> <model,...> [--top 24] [--centre 128]"""
import argparse, os
import cv2, numpy as np, tifffile, zarr

ap = argparse.ArgumentParser()
ap.add_argument('blk'); ap.add_argument('out'); ap.add_argument('id'); ap.add_argument('models')
ap.add_argument('--top', type=int, default=24); ap.add_argument('--centre', type=int, default=128)
a = ap.parse_args()
os.makedirs(a.out, exist_ok=True)
P = np.load(os.path.join(a.blk, 'patches.npz')); S, C = int(P['size']), a.centre; o = (S - C) // 2; n = len(P['rowcol'])
mos = zarr.open(os.path.join(a.blk, 'mosaic.zarr'), mode='r')['0']
cut = lambda M, r, c: M[r * S + o:r * S + o + C, c * S + o:c * S + o + C]
full = lambda M, r, c: M[r * S:(r + 1) * S, c * S:(c + 1) * S]
ct33 = np.asarray(mos[33])                                                # the surface layer of every patch
ct31, ct35 = np.asarray(mos[31]).astype(np.float32), np.asarray(mos[35]).astype(np.float32)
out = dict(centre=P['centre'], normal=P['normal'], u=P['u'], v=P['v'], box=P['box'], size=S, centre_px=C, models=np.array(a.models.split(',')))
out['ct64'] = np.stack([cv2.resize(cut(ct33, r, c), (64, 64), interpolation=cv2.INTER_AREA) for r, c in P['rowcol']]).astype(np.uint8)
nz = ct33[ct33 > 0]; dark = 0.5 * float(np.median(nz)) if nz.size else 0.0
air, lcorr = [], []
for r, c in P['rowcol']:
    x = cut(ct33, r, c).astype(np.float32); air.append(float((x < dark).mean()))
    a1, a2 = cut(ct31, r, c).ravel(), cut(ct35, r, c).ravel()
    lcorr.append(float(np.corrcoef(a1, a2)[0, 1]) if a1.std() > 0 and a2.std() > 0 else 0.0)
out['air'] = np.array(air, np.float32); out['layer_corr'] = np.array(lcorr, np.float32)
plausible = out['air'] <= 0.3
gal = []
for m in a.models.split(','):
    for order, suf in (('fwd', ''), ('rev', '_reverse')):
        f = os.path.join(a.blk, 'maps', f'mosaic__{m}__L66s25{suf}.tif')
        if not os.path.exists(f):
            continue
        M = tifffile.imread(f)
        cent = [cut(M, r, c).astype(np.float32) / 255. for r, c in P['rowcol']]
        st = np.array([[x.mean(), x.std(), (x >= 0.5).mean()] for x in cent], np.float32)
        out[f'stats_{m}_{order}'] = st
        out[f'ink64_{m}_{order}'] = np.stack([cv2.resize((x * 255).astype(np.uint8), (64, 64), interpolation=cv2.INTER_AREA) for x in cent])
        top = np.argsort(-st[:, 2])[:a.top]                                # hottest by share of ink >= 0.5
        out[f'top_{m}_{order}'] = top
        out[f'topink_{m}_{order}'] = np.stack([full(M, *P['rowcol'][k]) for k in top]).astype(np.uint8)
        if not gal:
            out['topct'] = np.stack([full(ct33, *P['rowcol'][k]) for k in top]).astype(np.uint8)
            out['topct_order'] = np.array(f'{m}_{order}')
        okk = np.nonzero(plausible)[0]; topp = okk[np.argsort(-st[okk, 2])][:a.top]       # hottest among plausible patches
        out[f'topplaus_{m}_{order}'] = topp
        out[f'topplausink_{m}_{order}'] = np.stack([full(M, *P['rowcol'][k]) for k in topp]).astype(np.uint8) if len(topp) else np.zeros((0, S, S), np.uint8)
        out[f'topplausct_{m}_{order}'] = np.stack([full(ct33, *P['rowcol'][k]) for k in topp]).astype(np.uint8) if len(topp) else np.zeros((0, S, S), np.uint8)
        for tag, sel in (('', top), ('_plausible', topp)):
            rows = []
            for k in sel[:12]:
                ct = full(ct33, *P['rowcol'][k]); ink = full(M, *P['rowcol'][k])
                ctn = cv2.normalize(ct, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
                tile = np.concatenate([cv2.cvtColor(ctn, cv2.COLOR_GRAY2BGR), cv2.applyColorMap(ink, cv2.COLORMAP_INFERNO)], 1)
                cv2.putText(tile, f'{a.id} #{k} {st[k, 2]:.2f} air {air[k]:.2f} lc {lcorr[k]:.2f}', (6, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)
                rows.append(tile)
            if rows:
                while len(rows) % 3:
                    rows.append(np.zeros_like(rows[0]))
                g = np.concatenate([np.concatenate(rows[i:i + 3], 1) for i in range(0, len(rows), 3)], 0)
                cv2.imwrite(os.path.join(a.out, f'gallery_{m}_{order}{tag}.jpg'), g, [cv2.IMWRITE_JPEG_QUALITY, 88]); gal.append(m)
np.savez_compressed(os.path.join(a.out, 'summary.npz'), **out)
print(f'{a.id}: {n} patches ({int(plausible.sum())} plausible), summary {os.path.getsize(os.path.join(a.out, "summary.npz")) / 2 ** 20:.1f} MiB')
