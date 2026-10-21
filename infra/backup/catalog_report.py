#!/usr/bin/env python3
"""Write docs/DATA_CATALOG.md from data/catalog/{catalog,results}.sqlite (generated; do not edit by hand).
Usage: catalog_report.py [catalog.sqlite] [results.sqlite] [out.md] [--all]   (--all = every scroll; refused for the public docs/)"""
import sqlite3, sys, time
ALL = '--all' in sys.argv; sys.argv = [a for a in sys.argv if a != '--all']   # --all: every scroll, for a PRIVATE copy only
cat = sys.argv[1] if len(sys.argv) > 1 else 'data/catalog/catalog.sqlite'
res = sys.argv[2] if len(sys.argv) > 2 else 'data/catalog/results.sqlite'
out = sys.argv[3] if len(sys.argv) > 3 else 'docs/DATA_CATALOG.md'
# Privacy (2026-10-15): scrolls we don't publish yet are listed in pipeline/common/scrolls_private.json (not in git). Their
# rows never reach the report; without that list the report refuses to run, so a fresh checkout cannot leak them.
import json, os
_pv = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'pipeline', 'common', 'scrolls_private.json')
if not os.path.exists(_pv):
    sys.exit(f'refusing: no private scroll list at {_pv}')
PRIVATE = set(json.load(open(_pv)))
pub = lambda *vals: not any(p in str(v) for v in vals if v is not None for p in PRIVATE | {p.replace('PHerc', '') for p in PRIVATE})
if ALL:
    if os.path.abspath(out).startswith(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'docs'))):
        sys.exit('refusing: --all lists the private scrolls; write it outside the public docs/ (e.g. the private repo)')
    pub = lambda *vals: True
c, r = sqlite3.connect(cat), sqlite3.connect(res); G = 1073741824.0
L = ['# Data catalog (generated)', '',
     f'Generated {time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())} by `infra/backup/catalog.py` (one scan per host) and `infra/backup/results_db.py`, '
     'merged on the Mac into `data/catalog/catalog.sqlite` and `data/catalog/results.sqlite`. Do not edit by hand: re-run the scans. '
     'Layout and rules: `docs/DATA_LAYOUT.md`. Backup set: `infra/backup/backup_r2.sh` (private object storage).', '',
     '## Artifacts by host and kind', '', '| host | kind | items | GiB | critical items |', '|---|---|---:|---:|---:|']
for h, k, n, s, cr in c.execute('select host, kind, count(*), sum(coalesce(size,0)), sum(critical) from artifacts group by 1,2 order by 1, 4 desc'):
    L.append(f'| {h} | {k} | {n} | {s / G:.2f} | {cr} |')
L += ['', 'Public inputs (scan volumes, Lasagna, tracks, surface predictions, normal grids) are listed per store without sizes; they are re-downloadable.', '',
      '## Geometry and ink by scroll and fit', '', '| scroll | fit | meshes (snapped / flattened) | renders | ink maps | ensemble images |', '|---|---|---:|---:|---:|---:|']
q = '''select scroll, fit,
  count(distinct case when kind='mesh-snapped' then winding end), count(distinct case when kind='mesh-flattened' then winding end),
  sum(kind='render'), sum(kind='ink-map'), sum(kind='ensemble-image')
  from artifacts where scroll is not null and fit is not null group by 1,2 having sum(kind in ('mesh-snapped','mesh-flattened','render','ink-map','ensemble-image')) > 0 order by 1,2'''
for sc, fit, ms, mf, rn, im, ei in c.execute(q):
    if pub(sc, fit): L.append(f'| {sc} | {fit} | {ms} / {mf} | {rn} | {im} | {ei} |')
L += ['', '## Scores (results table)', '', '| scroll | fit | source | models | rows | v0.1 LOOK | max row_R |', '|---|---|---|---|---:|---:|---:|']
for row in r.execute('select scroll, fit, source, models, count(*), sum(flag_v01), max(row_R) from scores group by 1,2,3,4 order by 1,2,3,4'):
    sc, fit, src, ms, n, fl, mr = row
    if not pub(sc, fit, src): continue
    L.append(f'| {sc or ""} | {fit or ""} | {src} | {ms} | {n} | {"" if fl is None else fl} | {"" if mr is None else f"{mr:.2f}"} |')
L += ['', '## Known-text control AUCs (best depth per model, reading side)', '', '| control | model | best depth | AUC | r |', '|---|---|---:|---:|---:|']
for ctl, m, d, a, rr in r.execute('''select control, model, depth, auc, r from control_auc a where side='reading' and auc = (select max(auc) from control_auc b
                                     where b.control=a.control and b.model=a.model and b.side='reading') order by control, auc desc'''):
    if pub(ctl): L.append(f'| {ctl} | {m} | {d:+d} | {a:.3f} | {rr:.3f} |')
open(out, 'w').write('\n'.join(L) + '\n'); print(out, len(L), 'lines')
