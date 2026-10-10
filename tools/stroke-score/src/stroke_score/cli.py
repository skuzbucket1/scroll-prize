"""Command line: `stroke-score score ...` scores one render at one depth; `stroke-score rank ...` ranks many results.

  stroke-score score --surface <name>.zarr --maps <dir> --um 9.362 --depth 1 --out <dir> [--models ...] [--crops 3]
  stroke-score score --surface <name>.zarr --map-list maps.json --um 8.64 --depth 1 --out <dir>
  stroke-score rank <result dirs or json files...> [--out ranking.tsv]
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
import sys

from .core import Params, run

# Short model names and the file names Erwin Nieuwlaar's run_ink.sh writes for them (66-layer render, depth d):
#   villa models  <name>__<model>__L66s<25+d>[_reverse].tif      Hecate  <name>__hecate__L66zc<32.5+d>[_reverse].png
# `_reverse` is the READING side (the text face), the plain file the BLIND side.
MODELS = {'dnative': 'dnative', 'hecate': 'hecate', 'ink9-42': 'hybrid_3d2d-seed42', 'ink9-43': 'hybrid_3d2d-seed43'}


def nieuwlaar_paths(maps_dir: str, name: str, model: str, d: int) -> tuple[str, str] | None:
    mk = MODELS.get(model, model)
    if mk == 'hecate':
        stem = os.path.join(maps_dir, f'{name}__hecate__L66zc{32.5 + d:.2f}')
        pr, pb = stem + '_reverse.png', stem + '.png'
    else:
        stem = os.path.join(maps_dir, f'{name}__{mk}__L66s{d + 25}')
        pr, pb = stem + '_reverse.tif', stem + '.tif'
    return (pr, pb) if os.path.isfile(pr) and os.path.isfile(pb) else None


def cmd_score(a) -> int:
    name = a.name or os.path.basename(a.surface.rstrip('/'))[:-5]
    want = [m for m in a.models.split(',') if m]
    if a.map_list:
        spec = json.load(open(a.map_list))
        maps = {m: (spec[m]['reading'], spec[m]['blind']) for m in spec if not want or m in want}
    else:
        maps = {}
        for m in want:
            pp = nieuwlaar_paths(a.maps, name, m, a.depth)
            if pp:
                maps[m] = pp
        if len(maps) < len(want):
            print(f'only {sorted(maps)} of {want} have both sides at d{a.depth:+d} in {a.maps}', file=sys.stderr)
            return 2
    p = Params(um=a.um, thr=a.thr, bg_mm=a.bg_mm, amin_mm2=a.amin_mm2, amax_mm2=a.amax_mm2, tile_mm=a.tile_mm,
               step_mm=a.step_mm, window_mm=a.window_mm, window_min_frac=a.window_min_frac, edge_mm=a.edge_mm,
               hole_mm2=a.hole_mm2, void_frac=a.void_frac, top=a.top)
    r = run(a.surface, maps, a.out, name, a.depth, p, mid_layer=a.mid_layer, tag=a.tag, crops=a.crops,
            png=not a.no_png, zrange=tuple(a.zrange))
    s = r['sides']
    print(json.dumps(dict(name=name, depth=a.depth, models=r['models'],
                          area_R=s['reading']['stroke_frac'], area_B=s['blind']['stroke_frac'],
                          window_R=s['reading']['window'].get('max'), window_B=s['blind']['window'].get('max'),
                          seconds=r['seconds'])))
    return 0


def flag(nm: int, aR: float, aB: float, wR: float, wB: float, a) -> bool:
    """LOOK if area_R >= area_thr, or R - B >= diff_thr, or the best window >= window_thr (three models) or
    window_thr4 (four or more) and at least window_ratio times the blind side's best window. Single models never flag."""
    if nm < 3 or any(math.isnan(x) for x in (aR, aB)):
        return False
    wt = a.window_thr4 if nm >= 4 else a.window_thr
    return aR >= a.area_thr or aR - aB >= a.diff_thr or (wR >= wt and wR >= a.window_ratio * wB)


def cmd_rank(a) -> int:
    files = []
    for x in a.inputs:
        files += sorted(glob.glob(os.path.join(x, '**', '*__strokes*_d*.json'), recursive=True)) if os.path.isdir(x) else [x]
    rows = []
    for f in files:
        try:
            j = json.load(open(f))
            r, b = j['sides']['reading'], j['sides']['blind']
        except (KeyError, ValueError):
            continue
        aR, aB = r['stroke_frac'], b['stroke_frac']
        wR, wB = r.get('window', {}).get('max', 0.0), b.get('window', {}).get('max', 0.0)
        nm = len(j['models'])
        top = (j.get('top_reading_tiles') or [{}])[0]
        rows.append(dict(name=j['name'], depth=j['depth'], models=nm, area_R=aR, area_B=aB, diff=aR - aB, window_R=wR,
                         window_B=wB, top_read_y=top.get('read_y', ''), top_read_x=top.get('read_x', ''),
                         top_damage=top.get('damage', ''), flag='LOOK' if flag(nm, aR, aB, wR, wB, a) else '',
                         file=f))
    rows.sort(key=lambda x: -(x['area_R'] if not math.isnan(x['area_R']) else -1))
    cols = ['name', 'depth', 'models', 'area_R', 'area_B', 'diff', 'window_R', 'window_B', 'top_read_y', 'top_read_x',
            'top_damage', 'flag', 'file']
    out = open(a.out, 'w') if a.out else sys.stdout
    print('\t'.join(cols), file=out)
    for x in rows:
        print('\t'.join(f'{x[c]:.4f}' if isinstance(x[c], float) else str(x[c]) for c in cols), file=out)
    print(f'# {len(rows)} rows, {sum(1 for x in rows if x["flag"])} flagged LOOK', file=sys.stderr)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog='stroke-score', description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('score', help='score one render at one depth')
    s.add_argument('--surface', required=True, help='66-layer render: zarr group with array "0" of shape (layers, H, W)')
    g = s.add_mutually_exclusive_group(required=True)
    g.add_argument('--maps', help='folder with run_ink.sh outputs (Nieuwlaar naming)')
    g.add_argument('--map-list', help='JSON {model: {"reading": path, "blind": path}} for any naming')
    s.add_argument('--out', required=True)
    s.add_argument('--name', help='map name prefix (default: render folder name without .zarr)')
    s.add_argument('--um', type=float, required=True, help='render pixel size in micrometres')
    s.add_argument('--depth', type=int, default=1)
    s.add_argument('--mid-layer', type=int, default=33, help='render layer of depth 0 (66-layer renders: 33)')
    s.add_argument('--models', default='dnative,hecate,ink9-42,ink9-43')
    s.add_argument('--tag', default='', help='suffix for the output names')
    s.add_argument('--thr', type=float, default=2.0)
    s.add_argument('--bg-mm', type=float, default=1.5)
    s.add_argument('--amin-mm2', type=float, default=0.02)
    s.add_argument('--amax-mm2', type=float, default=1.5)
    s.add_argument('--tile-mm', type=float, default=4.0)
    s.add_argument('--step-mm', type=float, default=1.0)
    s.add_argument('--window-mm', type=float, default=20.0)
    s.add_argument('--window-min-frac', type=float, default=0.3)
    s.add_argument('--edge-mm', type=float, default=0.5)
    s.add_argument('--hole-mm2', type=float, default=0.5)
    s.add_argument('--void-frac', type=float, default=0.0)
    s.add_argument('--top', type=int, default=10)
    s.add_argument('--crops', type=int, default=0, help='write review crops of the top N tiles')
    s.add_argument('--zrange', type=float, nargs=2, default=(-1.0, 4.0))
    s.add_argument('--no-png', action='store_true')
    s.set_defaults(fn=cmd_score)
    r = sub.add_parser('rank', help='rank score files and flag the ones worth a look')
    r.add_argument('inputs', nargs='+', help='result folders (searched recursively) or json files')
    r.add_argument('--out', help='write the table here instead of stdout')
    r.add_argument('--area-thr', type=float, default=0.015)
    r.add_argument('--diff-thr', type=float, default=0.010)
    r.add_argument('--window-thr', type=float, default=0.030, help='window line for three models')
    r.add_argument('--window-thr4', type=float, default=0.035, help='window line for four or more models')
    r.add_argument('--window-ratio', type=float, default=2.0)
    r.set_defaults(fn=cmd_rank)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == '__main__':
    sys.exit(main())
