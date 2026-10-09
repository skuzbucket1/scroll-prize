#!/usr/bin/env bash
# Rank every fleet segment by its stroke score (bin/stroke_score.py output fetched from the workers) and flag those that
# deserve eyes / the Hecate pass. Read-only, no AWS calls.   Usage: aws/fleet_rank.sh [results dir]
# Metrics (absolute, not the reading/blind ratio, which blows up when the blind side is quiet): area_R = share of the
# reading side covered by stroke-sized ink; R-B = area_R minus the blind side's; window = best 2 x 2 cm (4 cm2, First
# Letters scale) reading-side stroke share.
# Calibration 2026-10-09 (PHerc. 343 control vs PHerc0191 w068-w074, depths 0/+1):
#   three models: control area_R 0.0354, R-B +0.030, window 0.050;  PHerc0191 area_R <= 0.0064, R-B <= +0.0021, window <= 0.017
#   four models:  control area_R 0.0335, R-B +0.031, window 0.048;  PHerc0191 area_R <= 0.0073, R-B <= +0.0057, window <= 0.023
# LOOK if area_R >= 0.015, or R-B >= 0.010, or window >= 0.030 (three models) / 0.035 (four models).
HERE=$(cd "$(dirname "$0")" && pwd); ROOT=$(cd "$HERE/.." && pwd)
R=${1:-$ROOT/data/aws-results/fleet}
python3 - "$R" <<'PY'
import glob, json, os, sys
rows = []
for f in glob.glob(os.path.join(sys.argv[1], '*', '*', 'strokes', '*__strokes*_d*.json')):
    j = json.load(open(f)); r, b = j['sides']['reading'], j['sides']['blind']
    aR, aB = r['stroke_frac'], b['stroke_frac']
    wR, wB = r.get('window', {}).get('max', 0.0), b.get('window', {}).get('max', 0.0)
    nm = len(j['models'])
    look = aR >= 0.015 or aR - aB >= 0.010 or wR >= (0.035 if nm >= 4 else 0.030)
    top = (j.get('top_reading_tiles') or [{}])[0]
    rows.append((aR, j['name'].replace('exp30k_snapped_', '').replace('_66', ''), j['depth'], nm, aB, wR, wB,
                 top.get('read_y', ''), top.get('read_x', ''), top.get('damage', ''), 'LOOK' if look else '', os.path.dirname(f)))
rows.sort(key=lambda x: -x[0])
print('winding\tdepth\tmodels\tarea_R\tarea_B\tR-B\twindow_R\twindow_B\ttop_read_y\ttop_read_x\ttop_damage\tflag\tcrops')
for aR, n, d, nm, aB, wR, wB, y, x, dmg, flag, path in rows:
    print(f'{n}\t{d:+d}\t{nm}\t{aR:.4f}\t{aB:.4f}\t{aR - aB:+.4f}\t{wR:.4f}\t{wB:.4f}\t{y}\t{x}\t{dmg}\t{flag}\t{path}')
print(f'# {len(rows)} rows, {sum(1 for r in rows if r[10])} flagged LOOK', file=sys.stderr)
PY
