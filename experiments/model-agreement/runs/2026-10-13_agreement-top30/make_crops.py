"""Crops for the agreement filter (2026-10-13, step 2; the six-model agreement rule held on three of four known-text
segments: PHerc. 343 78 %, 0841 w00 78 %, 0139 w047 78 % of letter tiles, against 0-7 % of clean 9.36 µm papyrus).
From each scroll's stroke-score 0.2 post pass (Reader v2 + d9v4C), rank winding-depths by an approximate 0.2 margin
(contrast (area_R - area_B) / 0.025, or rows row_R / 1.5 when row_R >= 1.8 row_B), keep each winding's best depth, take
the top `n` windings per scroll, and cut a 14 x 8 mm window (+256 px margin) centred on that depth's strongest 4 mm
reading-side tile, as the agreement-null crops were cut. Writes <out>/<scroll>_<w>_top.zarr, .window and crops.tsv.
Usage: make_crops.py <out dir> [--n 15]"""
import json, os, sys
import numpy as np, zarr
out = sys.argv[1]; n = int(sys.argv[sys.argv.index('--n') + 1]) if '--n' in sys.argv else 15
os.makedirs(out, exist_ok=True)
POST = os.path.expanduser('~/scroll-prizes/runs/2026-10-11_tier23-newmodels/post')
FITS = {'PHerc0813': 'exp30k-z12000', 'PHerc0191': 'exp30k-z11200'}
h, w_, m = 854, 1495, 256
with open(f'{out}/crops.tsv', 'w') as fo:
    fo.write('name\tscroll\twinding\tdepth\tmargin\tflag\ty0\tx0\n')
    for sc, fit in FITS.items():
        rows = [l.rstrip('\n').split('\t') for l in open(f'{POST}/{sc}/ranking_v02.tsv')]; hd = rows[0]; rows = rows[1:]
        best = {}
        for r in rows:
            d = dict(zip(hd, r)); rR, rB = float(d['row_R'] or 0), float(d['row_B'] or 0)
            mg = max((float(d['area_R']) - float(d['area_B'])) / 0.025, rR / 1.5 if rR >= 1.8 * rB else 0.0)
            if d['name'] not in best or mg > best[d['name']][0]:
                best[d['name']] = (mg, int(d['depth']), d['flag_v02'])
        top = sorted(best.items(), key=lambda t: -t[1][0])[:n]
        for wn, (mg, dep, flag) in top:
            post = json.load(open(f'{POST}/{sc}/{wn}/{wn}__post.json'))['depths'][str(dep)]
            q = post['top_tiles'][0]; cy, cx = q['raw_y'] + q['size_px'] // 2, q['raw_x'] + q['size_px'] // 2
            src = zarr.open(f'/mnt/nvme/scroll-prizes/data/{sc}/renders/{fit}/{wn}.zarr', mode='r')['0']; H, W = src.shape[1:]
            y = int(np.clip(cy - h // 2, 0, max(0, H - h))); x = int(np.clip(cx - w_ // 2, 0, max(0, W - w_)))
            Y0, X0 = max(0, y - m), max(0, x - m)
            a = np.asarray(src[:, Y0:min(H, y + h + m), X0:min(W, x + w_ + m)])
            name = f'{sc}_{wn}_top'
            g = zarr.open_group(f'{out}/{name}.zarr', mode='w', zarr_format=2)
            g.create_array('0', shape=a.shape, chunks=(66, 256, 256), dtype='u1', fill_value=0)[:] = a
            hh, ww = min(h, a.shape[1] - (y - Y0)), min(w_, a.shape[2] - (x - X0))
            open(f'{out}/{name}.window', 'w').write(f'{y - Y0} {x - X0} {hh} {ww}\n')
            fo.write(f'{name}\t{sc}\t{wn}\t{dep}\t{mg:.2f}\t{flag}\t{y}\t{x}\n'); fo.flush()
            print(name, f'margin {mg:.2f} depth {dep} {flag}', flush=True)
