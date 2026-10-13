#!/usr/bin/env python3
"""One results table: collect every score this host holds into SQLite with provenance.
Sources: stroke-score JSONs (*__strokes_d±NN.json, packaged tool and the research script), post_models JSONs (*__post.json:
stroke + row scores for any model set), rowness.txt (row scores of three-model maps), control evaluations (eval*.json: AUC/r).
Scroll, fit and winding come from the segment name or the path. The v0.1 LOOK rule is recomputed for every row.
Usage: results_db.py <host> <root> <out.sqlite>          Merge: results_db.py --merge <out.sqlite> <in1.sqlite> <in2.sqlite> ...
(stdlib only)"""
import glob, json, os, re, sqlite3, sys

SCHEMA = '''create table if not exists scores (host text, path text, source text, scroll text, fit text, winding text, name text,
  run_id text, models text, n_models int, depth int, area_R real, area_B real, window_R real, window_B real, row_R real, row_B real,
  top_damage real, flag_v01 int, primary key (host, path, depth));
create table if not exists control_auc (host text, path text, control text, model text, depth int, side text, auc real, r real,
  primary key (host, path, model, depth, side));'''
NAME_RULES = [(r'^exp30k_snapped_(w\d{3})', 'PHerc0191', 'exp30k-z9000'), (r'^community_snapped_(w\d{3})', 'PHerc0191', 'community-z11600'),
              (r'^p0813_exp30k_(w\d{3})', 'PHerc0813', 'exp30k-z12000'), (r'^c0139_(w047)', 'PHerc0139', 'control-w047'),
              (r'^c0841_(ag2814)', 'PHerc0841', 'control-ag2814'), (r'^control343', 'PHerc0343', 'control')]
MODEL_ALIAS = {'hybrid_3d2d-seed42': 'ink9-42', 'hybrid_3d2d-seed43': 'ink9-43'}

def where(name, rel):
    for pat, sc, fit in NAME_RULES:
        m = re.match(pat, name or '')
        if m: return sc, fit, (m.group(1) if m.groups() else None)
    parts = rel.split('/'); sc = next((x for x in parts if re.fullmatch(r'PHerc[0-9A-Za-z]+', x)), None); fit = None
    if 'scores' in parts: fit = parts[parts.index('scores') + 1]
    if 'tier23-newmodels' in rel: fit = {'PHerc0813': 'exp30k-z12000', 'PHerc0191': 'exp30k-z11200'}.get(sc)
    if 'rowness-0191-clearband' in rel: sc, fit = 'PHerc0191', 'exp30k-z11200'
    m = re.search(r'(?<![A-Za-z0-9])(w\d{3})(?![0-9])', name or '') or re.search(r'/(w\d{3})/', rel)
    return sc, fit, (m.group(1) if m else None)

def run_of(rel):
    parts = rel.split('/')
    for key in ('runs', 'runs-aws'):
        if key in parts and parts.index(key) + 1 < len(parts): return parts[parts.index(key) + 1]
    if 'aws-results' in parts: return 'aws-results'
    return None

def flag(n, aR, aB, wR, wB):
    if n is None or n < 3 or aR is None: return None
    return int(aR >= 0.015 or (aR - aB) >= 0.010 or (wR is not None and wB is not None and wR >= (0.035 if n >= 4 else 0.030) and wR >= 2 * wB))

def collect(host, root):
    rows, aucs = [], []
    for top in ('data', 'runs'):
        base = os.path.join(root, top)
        for dp, dn, fn in os.walk(base):
            dn[:] = [d for d in dn if not d.endswith(('.zarr', '.tifxyz')) and d not in ('source', 'renders', 'maps', '.venv', 'stroke-score-src')]
            for f in fn:
                full = os.path.join(dp, f); rel = os.path.relpath(full, root)
                try:
                    if f.endswith('.json') and '__strokes_' in f:
                        j = json.load(open(full)); r, b = j['sides']['reading'], j['sides']['blind']
                        name = re.sub(r'_66$', '', j.get('name', '')); models = sorted(MODEL_ALIAS.get(m, m) for m in j.get('models', []))
                        sc, fit, w = where(name, rel); tt = (j.get('top_reading_tiles') or [{}])[0]
                        aR, aB = r['stroke_frac'], b['stroke_frac']; wR, wB = (r.get('window') or {}).get('max'), (b.get('window') or {}).get('max')
                        rows.append((host, rel, 'stroke-score', sc, fit, w, name, run_of(rel), ','.join(models), len(models), int(j['depth']),
                                     aR, aB, wR, wB, None, None, tt.get('damage'), flag(len(models), aR, aB, wR, wB)))
                    elif f.endswith('__post.json'):
                        j = json.load(open(full)); name = re.sub(r'_66$', '', j['name']); sc, fit, w = where(name, rel)
                        models = sorted(MODEL_ALIAS.get(m, m) for m in j['models'])
                        for d, r in j['depths'].items():
                            tt = (r.get('top_tiles') or [{}])[0]
                            rows.append((host, rel, 'post', sc, fit, w, name, run_of(rel), ','.join(models), len(models), int(d),
                                         r['area_R'], r['area_B'], r['window_R'], r['window_B'], r['row_R'], r['row_B'], tt.get('damage'),
                                         flag(len(models), r['area_R'], r['area_B'], r['window_R'], r['window_B'])))
                    elif f == 'rowness.txt':
                        for line in open(full):
                            m = re.match(r'(\S+) d([+-]\d+) models=(\d+)\s+row_R ([\d.]+) .* row_B ([\d.]+)', line)
                            if not m: continue
                            name = m.group(1); sc, fit, w = where(name, rel)
                            rows.append((host, rel + '#' + name, 'rowness', sc, fit, w, name, run_of(rel), 'dnative,ink9-42,ink9-43', int(m.group(3)),
                                         int(m.group(2)), None, None, None, None, float(m.group(4)), float(m.group(5)), None, None))
                    elif f.startswith('eval') and f.endswith('.json'):
                        j = json.load(open(full))
                        for key, auc, r in j['rows']:
                            aucs.append((host, rel, j['name'], key[0], int(key[1]), key[2], auc, r))
                except Exception as e:
                    print(f'skip {rel}: {e}', file=sys.stderr)
    return rows, aucs

if sys.argv[1] == '--merge':
    out = sys.argv[2]; db = sqlite3.connect(out); db.executescript('drop table if exists scores; drop table if exists control_auc;' + SCHEMA)
    for src in sys.argv[3:]:
        db.execute('attach ? as s', (src,)); db.execute('insert or replace into scores select * from s.scores')
        db.execute('insert or replace into control_auc select * from s.control_auc'); db.commit(); db.execute('detach s')
else:
    host, root, out = sys.argv[1], os.path.abspath(sys.argv[2]), sys.argv[3]
    db = sqlite3.connect(out); db.executescript('drop table if exists scores; drop table if exists control_auc;' + SCHEMA)
    rows, aucs = collect(host, root)
    db.executemany('insert or replace into scores values (' + ','.join('?' * 19) + ')', rows)
    db.executemany('insert or replace into control_auc values (?,?,?,?,?,?,?,?)', aucs)
db.commit()
print(f'{out}: {db.execute("select count(*) from scores").fetchone()[0]} score rows, {db.execute("select count(*) from control_auc").fetchone()[0]} control AUC rows')
for r in db.execute('select scroll, fit, source, models, count(*), sum(flag_v01) from scores group by 1,2,3,4 order by 1,2,3'):
    print('  ', ' | '.join('' if x is None else str(x) for x in r))
