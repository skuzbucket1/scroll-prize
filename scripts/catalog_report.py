#!/usr/bin/env python3
"""Write docs/DATA_CATALOG.md from data/catalog/{catalog,results}.sqlite (generated; do not edit by hand).
Usage: catalog_report.py [catalog.sqlite] [results.sqlite] [out.md]"""
import sqlite3, sys, time
cat = sys.argv[1] if len(sys.argv) > 1 else 'data/catalog/catalog.sqlite'
res = sys.argv[2] if len(sys.argv) > 2 else 'data/catalog/results.sqlite'
out = sys.argv[3] if len(sys.argv) > 3 else 'docs/DATA_CATALOG.md'
c, r = sqlite3.connect(cat), sqlite3.connect(res); G = 1073741824.0
L = ['# Data catalog (generated)', '',
     f'Generated {time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())} by `scripts/catalog.py` (one scan per host) and `scripts/results_db.py`, '
     'merged on the Mac into `data/catalog/catalog.sqlite` and `data/catalog/results.sqlite`. Do not edit by hand: re-run the scans. '
     'Layout and rules: `docs/DATA_LAYOUT.md`. Backup set: `scripts/backup_r2.sh` (Cloudflare R2).', '',
     '## Artifacts by host and kind', '', '| host | kind | items | GiB | critical items |', '|---|---|---:|---:|---:|']
for h, k, n, s, cr in c.execute('select host, kind, count(*), sum(coalesce(size,0)), sum(critical) from artifacts group by 1,2 order by 1, 4 desc'):
    L.append(f'| {h} | {k} | {n} | {s / G:.2f} | {cr} |')
L += ['', 'Public inputs (scan volumes, Lasagna, tracks, surface predictions, normal grids) are listed per store without sizes; they are re-downloadable.', '',
      '## Geometry and ink by scroll and fit', '', '| scroll | fit | meshes (snapped / flattened) | renders | ink maps | ensemble images |', '|---|---|---:|---:|---:|---:|']
q = '''select scroll, fit,
  count(distinct case when kind='mesh-snapped' then winding end), count(distinct case when kind='mesh-flattened' then winding end),
  sum(kind='render'), sum(kind='ink-map'), sum(kind='ensemble-image')
  from artifacts where scroll is not null and fit is not null group by 1,2 having sum(kind in ('mesh-snapped','mesh-flattened','render','ink-map','ensemble-image')) > 0 order by 1,2'''
for sc, fit, ms, mf, rn, im, ei in c.execute(q): L.append(f'| {sc} | {fit} | {ms} / {mf} | {rn} | {im} | {ei} |')
L += ['', '## Scores (results table)', '', '| scroll | fit | source | models | rows | v0.1 LOOK | max row_R |', '|---|---|---|---|---:|---:|---:|']
for row in r.execute('select scroll, fit, source, models, count(*), sum(flag_v01), max(row_R) from scores group by 1,2,3,4 order by 1,2,3,4'):
    sc, fit, src, ms, n, fl, mr = row
    L.append(f'| {sc or ""} | {fit or ""} | {src} | {ms} | {n} | {"" if fl is None else fl} | {"" if mr is None else f"{mr:.2f}"} |')
L += ['', '## Known-text control AUCs (best depth per model, reading side)', '', '| control | model | best depth | AUC | r |', '|---|---|---:|---:|---:|']
for ctl, m, d, a, rr in r.execute('''select control, model, depth, auc, r from control_auc a where side='reading' and auc = (select max(auc) from control_auc b
                                     where b.control=a.control and b.model=a.model and b.side='reading') order by control, auc desc'''):
    L.append(f'| {ctl} | {m} | {d:+d} | {a:.3f} | {rr:.3f} |')
open(out, 'w').write('\n'.join(L) + '\n'); print(out, len(L), 'lines')
