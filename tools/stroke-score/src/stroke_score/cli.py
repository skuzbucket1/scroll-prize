"""Command line: `stroke-score score ...` scores one render at one depth; `stroke-score rank ...` ranks many results.

  stroke-score score --surface <name>.zarr --maps <dir> --um 9.362 --depth 1 --out <dir> [--models ...] [--crops 3]
  stroke-score score --surface <name>.zarr --map-list maps.json --um 8.64 --depth 1 --out <dir>
  stroke-score rank <result dirs or json files...> [--out ranking.tsv]
  stroke-score control list | fetch <control> <dir> | eval --control <id> --fetched <dir> --maps <dir> --name <n> --depth d
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
import re
import sys

import numpy as np

from .core import Params, run

# Short model names and the file names Erwin Nieuwlaar's run_ink.sh writes for them (66-layer render, depth d):
#   villa models  <name>__<model>__L66s<25+d>[_reverse].tif      Hecate  <name>__hecate__L66zc<32.5+d>[_reverse].png
# `_reverse` is the READING side (the text face), the plain file the BLIND side.
MODELS = {'dnative': 'dnative', 'hecate': 'hecate', 'ink9-42': 'hybrid_3d2d-seed42', 'ink9-43': 'hybrid_3d2d-seed43',
          'readerv2': 'readerv2', 'd9v4c': 'd9v4c'}


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
    want = [m for m in a.models.split(',') if m and m != 'auto']
    if a.models == 'auto' and not a.map_list:
        want = [m for m in MODELS if nieuwlaar_paths(a.maps, name, m, a.depth)]
        if not want:
            print(f'no maps for {name} at d{a.depth:+d} in {a.maps}', file=sys.stderr)
            return 2
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
                          row_R=s['reading']['row']['score'], row_B=s['blind']['row']['score'], seconds=r['seconds'])))
    return 0


def flag(nm: int, aR: float, aB: float, wR: float, wB: float, a) -> bool:
    """LOOK if area_R >= area_thr, or R - B >= diff_thr, or the best window >= window_thr (three models) or
    window_thr4 (four or more) and at least window_ratio times the blind side's best window. Single models never flag."""
    if nm < 3 or any(math.isnan(x) for x in (aR, aB)):
        return False
    wt = a.window_thr4 if nm >= 4 else a.window_thr
    return aR >= a.area_thr or aR - aB >= a.diff_thr or (wR >= wt and wR >= a.window_ratio * wB)


# v0.2 LOOK thresholds per model set (the row score's scale depends on the models), set from known text cut into strips as
# tall as our ~1 cm search bands and from the null windings; see the README. Other model sets use V02_DEFAULT.
V02_THRESHOLDS = {
    frozenset({'dnative', 'ink9-42', 'ink9-43'}): dict(row=1.2, shape=0.35),   # 0 of 194 PHerc0191 null winding-depths pass
    frozenset({'readerv2', 'd9v4c'}): dict(row=1.5, shape=0.42),               # 1 of 100 PHerc0813 null winding-depths passes
}
V02_DEFAULT = dict(row=1.5, shape=0.42)
_SHORT = {v: k for k, v in MODELS.items()}


def v02_thresholds(models, a=None) -> dict:
    t = dict(V02_THRESHOLDS.get(frozenset(_SHORT.get(m, m) for m in models), V02_DEFAULT))
    if a is not None and getattr(a, 'row_thr', None) is not None:
        t['row'] = a.row_thr
    if a is not None and getattr(a, 'shape_thr', None) is not None:
        t['shape'] = a.shape_thr
    return t


def flag_v02(models, rR, rB, sR, a) -> bool:
    """v0.2 LOOK: the reading side shows rows (row_R at least the model set's row threshold and at least row_ratio x the
    blind side) and those rows are made of strokes (shape_R, the share of mark area in long thin marks, at least the
    shape threshold). Needs two or more models."""
    if len(models) < 2 or rR is None or rB is None or sR is None:
        return False
    t = v02_thresholds(models, a)
    return rR >= t['row'] and rR >= a.row_ratio * rB and sR >= t['shape']


def recurrence(rows: list) -> None:
    """For each row with a profile, the best correlation of its reading-side profile with the same depth and model set on
    neighbouring windings (w-2..w+2 of the same series, shifts of up to 3 bins). High values mean the pattern repeats turn
    after turn: sheet structure, not text."""
    series = {}
    for x in rows:
        m = re.search(r'(?<![A-Za-z0-9])w(\d{3})(?![0-9])', x['name'])
        if not m or not x.get('_prof'):
            continue
        key = (x['name'][:m.start()] + 'w###' + x['name'][m.end():], x['depth'], x['models'])
        series.setdefault(key, {})[int(m.group(1))] = x
    for key, by_w in series.items():
        for w, x in by_w.items():
            p0 = np.array([np.nan if v is None else v for v in x['_prof']], float)
            best = None
            for dw in (-2, -1, 1, 2):
                y = by_w.get(w + dw)
                if not y:
                    continue
                p1 = np.array([np.nan if v is None else v for v in y['_prof']], float)
                for sh in range(-3, 4):
                    a_, b_ = (p0[sh:], p1[:len(p1) - sh]) if sh >= 0 else (p0[:sh], p1[-sh:])
                    ok = np.isfinite(a_) & np.isfinite(b_)
                    if ok.sum() < 20 or np.std(a_[ok]) == 0 or np.std(b_[ok]) == 0:
                        continue
                    r = float(np.corrcoef(a_[ok], b_[ok])[0, 1])
                    best = r if best is None or r > best else best
            x['recur'] = round(best, 3) if best is not None else ''
    for x in rows:
        x.pop('_prof', None)


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
        rR, rB = (r.get('row') or {}).get('score'), (b.get('row') or {}).get('score')
        sR, sB = (r.get('shape') or {}).get('score'), (b.get('shape') or {}).get('score')
        hz = (r.get('shape') or {}).get('horiz')
        rows.append(dict(name=j['name'], depth=j['depth'], models=nm, area_R=aR, area_B=aB, diff=aR - aB, window_R=wR,
                         window_B=wB, top_read_y=top.get('read_y', ''), top_read_x=top.get('read_x', ''),
                         top_damage=top.get('damage', ''), flag='LOOK' if flag(nm, aR, aB, wR, wB, a) else '',
                         file=f, row_R=rR if rR is not None else '', row_B=rB if rB is not None else '',
                         shape_R=sR if sR is not None else '', shape_B=sB if sB is not None else '', streak=hz if hz is not None else '',
                         recur='', flag_v02='LOOK' if flag_v02(j['models'], rR, rB, sR, a) else '', _prof=r.get('profile')))
    recurrence(rows)
    rows.sort(key=lambda x: -(x['area_R'] if not math.isnan(x['area_R']) else -1))
    cols = ['name', 'depth', 'models', 'area_R', 'area_B', 'diff', 'window_R', 'window_B', 'top_read_y', 'top_read_x',
            'top_damage', 'flag', 'file', 'row_R', 'row_B', 'recur', 'flag_v02', 'shape_R', 'shape_B', 'streak']
    out = open(a.out, 'w') if a.out else sys.stdout
    print('\t'.join(cols), file=out)
    for x in rows:
        print('\t'.join(f'{x[c]:.4f}' if isinstance(x[c], float) else str(x[c]) for c in cols), file=out)
    print(f'# {len(rows)} rows, {sum(1 for x in rows if x["flag"])} flagged LOOK (v0.1 rule), '
          f'{sum(1 for x in rows if x["flag_v02"])} LOOK by the v0.2 rule (rows of strokes)', file=sys.stderr)
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
    s.add_argument('--models', default='auto', help='comma list (dnative,hecate,ink9-42,ink9-43,readerv2,d9v4c) or auto = every model found')
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
    r.add_argument('--row-thr', type=float, help='v0.2 rule: reading-side row score at least this (default: per model set)')
    r.add_argument('--row-ratio', type=float, default=1.8, help='v0.2 rule: and at least this times the blind side')
    r.add_argument('--shape-thr', type=float, help='v0.2 rule: shape score at least this (default: per model set)')
    r.set_defaults(fn=cmd_rank)
    from . import control
    control.add_parser(sub)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == '__main__':
    sys.exit(main())
