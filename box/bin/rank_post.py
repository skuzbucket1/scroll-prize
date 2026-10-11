"""Rank post_models.py results (__post.json, any model set) with the stroke-score 0.2 columns: row score, the v0.2 row
rule and neighbour recurrence of the along-winding profile (w-2..w+2 of the same series). Sorted by row_R.
Usage: rank_post.py <post dir> [--row-thr 2.0] [--row-ratio 1.8] > ranking_v02.tsv"""
import argparse, glob, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, 'stroke-score-src'))
from stroke_score.cli import flag_v02, recurrence

ap = argparse.ArgumentParser(); ap.add_argument('post'); ap.add_argument('--row-thr', type=float, default=2.0)
ap.add_argument('--row-ratio', type=float, default=1.8); a = ap.parse_args()
rows = []
for f in sorted(glob.glob(os.path.join(a.post, '**', '*__post.json'), recursive=True)):
    j = json.load(open(f))
    for d, r in j['depths'].items():
        rows.append(dict(name=j['name'], depth=int(d), models=len(j['models']), set=','.join(j['models']), tool=j.get('tool', '0.1'),
                         row_R=r['row_R'], row_B=r['row_B'], area_R=r['area_R'], area_B=r['area_B'], window_R=r['window_R'],
                         window_B=r['window_B'], row_at=r.get('row_at'), recur='', _prof=r.get('profile_R')))
recurrence(rows)
for x in rows:
    x['flag_v02'] = 'LOOK' if flag_v02(x['models'], x['row_R'], x['row_B'], a) else ''
rows.sort(key=lambda x: -x['row_R'])
cols = ['name', 'depth', 'set', 'row_R', 'row_B', 'recur', 'flag_v02', 'area_R', 'area_B', 'window_R', 'window_B', 'row_at', 'tool']
print('\t'.join(cols))
for x in rows:
    print('\t'.join(f'{x[c]:.4f}' if isinstance(x[c], float) else str(x[c]) for c in cols))
print(f'# {len(rows)} rows, {sum(1 for x in rows if x["flag_v02"])} LOOK by the v0.2 row rule '
      f'(row_R >= {a.row_thr} and >= {a.row_ratio} x row_B; thresholds provisional)', file=sys.stderr)
