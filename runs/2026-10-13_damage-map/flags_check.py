"""Do the flagged false alarms sit on damage? (2026-10-13) For the eight null winding-depths the 0.2 rule flags with Reader v2
+ d9v4C (report_ct2.txt), take the five strongest 4 mm reading-side tiles that stroke-score's post pass found (post JSONs of
runs/2026-10-11_tier23-newmodels) and look up the damage map's 1.5 mm tiles inside them: where do they rank among all of
that winding's tiles, per damage measure (percentile; 50 = like the rest of the winding, high = more damaged)?
Usage: flags_check.py [tiles dir, default tiles]   (prints a table; writes flags_check<suffix>.tsv)"""
import json, os, sys
import numpy as np

R = os.path.expanduser('~/scroll-prizes/runs/2026-10-13_damage-map'); POST = os.path.expanduser('~/scroll-prizes/runs/2026-10-11_tier23-newmodels/post')
FLAGS = [('0813', 'w062', 0), ('0813', 'w062', 1), ('0813', 'w063', 1), ('0813', 'w079', 0), ('0813', 'w110', 0),
         ('0191', 'w061', 0), ('0191', 'w087', 0), ('0191', 'w087', 1)]
MEAS = {'void': lambda Z: Z['void'], 'dark': lambda Z: Z['dark'], 'crack': lambda Z: Z['crack'], 'near edge': lambda Z: -Z['edge_mm'],
        'wander': lambda Z: Z['wander'], '|offset|': lambda Z: np.abs(Z['offset']), 'bright': lambda Z: Z['bright']}
TD = sys.argv[1] if len(sys.argv) > 1 else 'tiles'; SUF = TD[len('tiles'):]
rows = []
for sc, w, d in FLAGS:
    Z = np.load(f'{R}/{TD}/n_{sc}_{w}.npz'); t = json.loads(str(Z['meta']))['tile_px']
    post = json.load(open(f'{POST}/PHerc{sc}/{w}/{w}__post.json'))['depths'][str(d)]
    cy, cx = Z['y'] + t / 2, Z['x'] + t / 2; inside = np.zeros(len(cy), bool)
    for q in post['top_tiles']:
        inside |= (cy >= q['raw_y']) & (cy < q['raw_y'] + q['size_px']) & (cx >= q['raw_x']) & (cx < q['raw_x'] + q['size_px'])
    r = dict(flag=f'PHerc{sc} {w} d+{d}', tiles=int(inside.sum()), of=len(cy))
    for k, f in MEAS.items():
        v = f(Z); r[k] = float(np.mean([(v < x).mean() + 0.5 * (v == x).mean() for x in v[inside]]) * 100) if inside.any() else float('nan')
    rows.append(r)
keys = list(rows[0])
with open(f'{R}/flags_check{SUF}.tsv', 'w') as fo:
    fo.write('\t'.join(keys) + '\n')
    for r in rows:
        fo.write('\t'.join(f'{r[k]:.0f}' if isinstance(r[k], float) else str(r[k]) for k in keys) + '\n')
print('mean percentile of the flag tiles within their winding (50 = like the rest; higher = more damaged)')
print(f'{"flag":<20} {"tiles":>9} ' + ' '.join(f'{k:>9}' for k in MEAS))
for r in rows:
    print(f'{r["flag"]:<20} {r["tiles"]:>4} /{r["of"]:>4} ' + ' '.join(f'{r[k]:9.0f}' for k in MEAS))
print(f'{"mean":<20} {"":>9} ' + ' '.join(f'{np.nanmean([r[k] for r in rows]):9.0f}' for k in MEAS))
