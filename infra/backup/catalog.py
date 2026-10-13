#!/usr/bin/env python3
"""Artifact catalog: walk the project's data on this host and write one row per artifact into SQLite.
A zarr store or tifxyz mesh directory is one artifact; public scan inputs under <scroll>/source/ are listed per top-level
store without walking their chunks. Kinds come from the data layout (docs/DATA_LAYOUT.md); "critical" follows the backup
set in infra/backup/backup_r2.sh (infra/backup/windings_of_interest.tsv decides which ink maps count).
Usage: catalog.py <host: mac|box> <root> <out.sqlite>      (stdlib only; the Mac's system python works)"""
import hashlib, json, os, re, sqlite3, sys, time

host, root, out = sys.argv[1], os.path.abspath(sys.argv[2]), sys.argv[3]
interest = set()
for cand in (os.path.join(os.path.dirname(os.path.abspath(__file__)), 'windings_of_interest.tsv'),
             os.path.join(root, 'backup/windings_of_interest.tsv')):   # second: the box's layout before 2026-10-13
    if os.path.exists(cand):
        for line in open(cand):
            if line.startswith('#') or not line.strip(): continue
            sc, fit, w = line.split('\t')[:3]; interest.add((sc, fit, w))
        break

STORE_SUFFIXES = ('.zarr', '.tifxyz')
SKIP_DIRS = {'.git', '__pycache__', '.venv', 'stroke-score-src', 'prior-art', 'claims', 'claims3', 'claims-a3', 'claims-a4'}
W_RE = re.compile(r'(?<![A-Za-z0-9])(w\d{3})(?![0-9])|_(w\d{3})(?![0-9])')
D_RE = re.compile(r'(?:L66s(\d+)|L66zc(\d+\.\d+)|__d([+-]\d{2})|_d([+-]?\d+)\b)')
MODELS = {'hybrid_3d2d-seed42': 'ink9-42', 'hybrid_3d2d-seed43': 'ink9-43', 'dnative': 'dnative', 'hecate': 'hecate',
          'readerv2': 'readerv2', 'd9v4c': 'd9v4c', 'ink9-42': 'ink9-42', 'ink9-43': 'ink9-43'}

def dir_size(p):
    t = 0
    for dp, dn, fn in os.walk(p):
        for f in fn:
            try: t += os.lstat(os.path.join(dp, f)).st_size
            except OSError: pass
    return t

def sha1(p, limit=64 << 20):
    try:
        if os.path.getsize(p) > limit: return None
        h = hashlib.sha1()
        with open(p, 'rb') as f:
            for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
        return h.hexdigest()
    except OSError: return None

def classify(rel, is_store):
    parts = rel.split('/')
    scroll = next((x for x in parts if re.fullmatch(r'PHerc[0-9A-Za-z]+', x)), None)
    fit = None
    for key in ('geometry', 'renders', 'ink', 'scores'):
        if key in parts:
            i = parts.index(key)
            if i + 1 < len(parts): fit = parts[i + 1]
    m = W_RE.search(rel); w = (m.group(1) or m.group(2)) if m else None
    model = next((v for k, v in MODELS.items() if f'__{k}__' in rel or f'/{k}/' in rel), None)
    depth = None; dm = D_RE.search(os.path.basename(rel))
    if dm:
        if dm.group(1): depth = int(dm.group(1)) - 25
        elif dm.group(2): depth = round(float(dm.group(2)) - 32.5)
        elif dm.group(3): depth = int(dm.group(3))
        elif dm.group(4): depth = int(dm.group(4))
    side = 'reading' if ('_reverse' in rel or '_reading' in rel or 'ens_reading' in rel) else ('blind' if ('blind' in rel or re.search(r'__L66s\d+\.tif$', rel)) else None)
    run = None
    if 'runs' in parts:
        i = parts.index('runs'); run = parts[i + 1] if i + 1 < len(parts) else None
    for key in ('runs-aws',):
        if key in parts:
            i = parts.index(key); run = parts[i + 1] if i + 1 < len(parts) else run
    b = os.path.basename(rel)
    if parts[0] == 'memory': kind = 'memory'
    elif '/source/' in f'/{rel}/' or parts[0] == 'source': kind = 'public-input'
    elif '/inputs/' in f'/{rel}/': kind = 'fit-input'
    elif '/geometry/' in f'/{rel}/':
        kind = ('mesh-flattened' if '/flattened/' in rel else 'mesh-snapped' if '/snapped/' in rel else
                'fit' if '/fit' in rel else 'geometry-qa' if '/qa/' in rel else 'geometry')
    elif '/renders/' in f'/{rel}/' and is_store: kind = 'render'
    elif '/maps/' in rel and b.endswith(('.tif', '.png')): kind = 'ink-map'
    elif b.endswith('__post.json') or ('__strokes_' in b and b.endswith('.json')) or b.endswith('__stats.json'): kind = 'score'
    elif '/strokes/' in rel or ('/scores/' in rel and b.endswith('.png')) or '/post/' in rel and b.endswith('.jpg'): kind = 'score-figure'
    elif b in ('ranking.tsv', 'rowness.txt') or b.startswith('eval'): kind = 'ranking'
    elif re.search(r'/(ens3|ens4|ensemble|ensemble3)/', rel): kind = 'ensemble-image'
    elif '/sqm/' in rel or b.startswith('sqm'): kind = 'scan-quality'
    elif '/previews/' in rel or '/preview' in rel: kind = 'preview-image'
    elif parts[0] == 'data' and len(parts) > 1 and parts[1] == 'ref': kind = 'reference'
    elif b in ('ranking.tsv', 'rowness.txt') or b.startswith('eval'): kind = 'ranking'
    elif '/reviews/' in rel: kind = 'review-image'
    elif b == 'run.json': kind = 'run-record'
    elif b.endswith('.log') or b in ('progress.txt', 'timings.tsv'): kind = 'log'
    elif '/refs/' in rel: kind = 'reference'
    elif is_store and b.endswith('.tifxyz'): kind = 'mesh'
    else: kind = 'other'
    if parts[0] == 'data' and len(parts) > 1 and parts[1] == 'controls9um': kind = 'control-' + kind
    critical = kind in ('memory', 'score-figure', 'scan-quality', 'reference', 'fit', 'mesh-snapped', 'mesh-flattened', 'geometry-qa', 'score', 'ranking', 'run-record',
                        'review-image', 'control-ink-map', 'control-reference', 'control-score', 'control-ranking', 'control-other') \
        or (kind == 'fit-input' and re.search(r'umbilicus|spiral-scroll\.json|/qa/', rel)) \
        or (kind in ('ink-map', 'ensemble-image') and (scroll, fit, w) in interest) \
        or ('runs-aws' in parts or 'aws-results' in parts)
    return dict(scroll=scroll, fit=fit, winding=w, model=model, depth=depth, side=side, run_id=run, kind=kind, critical=int(bool(critical)))

db = sqlite3.connect(out); db.execute('drop table if exists artifacts')
db.execute('''create table artifacts (host text, path text, kind text, scroll text, fit text, winding text, model text, depth int,
              side text, run_id text, size int, mtime real, sha1 text, critical int, is_store int, primary key (host, path))''')
rows = []; t0 = time.time()
for top in ('data', 'runs', 'memory', 'backup'):
    base = os.path.join(root, top)
    if not os.path.isdir(base): continue
    for dp, dn, fn in os.walk(base, followlinks=False):
        rel_dp = os.path.relpath(dp, root)
        if any(x in SKIP_DIRS for x in rel_dp.split('/')): dn[:] = []; continue
        if re.match(r'^data/[^/]+/source(/[^/]+)?$', rel_dp):
            # public inputs (scan volume, Lasagna, tracks, surface prediction, normal grids): one row per store, not walked
            if re.match(r'^data/[^/]+/source/[^/]+$', rel_dp):
                for d in dn:
                    rel = os.path.join(rel_dp, d); c = classify(rel, True)
                    rows.append((host, rel, 'public-input', c['scroll'], None, None, None, None, None, None, None,
                                 os.lstat(os.path.join(dp, d)).st_mtime, None, 0, 1))
                dn[:] = []; continue
        for d in list(dn):
            full = os.path.join(dp, d)
            if os.path.islink(full): dn.remove(d); continue
            if d.endswith(STORE_SUFFIXES):
                rel = os.path.relpath(full, root); c = classify(rel, True)
                size = None if c['kind'] == 'public-input' else dir_size(full)
                rows.append((host, rel, c['kind'], c['scroll'], c['fit'], c['winding'], c['model'], c['depth'], c['side'], c['run_id'],
                             size, os.lstat(full).st_mtime, None, c['critical'], 1)); dn.remove(d)
        for f in fn:
            full = os.path.join(dp, f)
            if os.path.islink(full) or f == '.DS_Store': continue
            rel = os.path.relpath(full, root); c = classify(rel, False); st = os.lstat(full)
            if c['kind'] == 'public-input': continue
            rows.append((host, rel, c['kind'], c['scroll'], c['fit'], c['winding'], c['model'], c['depth'], c['side'], c['run_id'],
                         st.st_size, st.st_mtime, sha1(full) if c['critical'] else None, c['critical'], 0))
db.executemany('insert or replace into artifacts values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', rows); db.commit()
n = db.execute('select count(*), sum(size) from artifacts').fetchone()
print(f'{host}: {n[0]} artifacts, {(n[1] or 0) / 2**30:.1f} GiB catalogued in {time.time() - t0:.0f}s -> {out}')
for r in db.execute('select kind, count(*), round(sum(coalesce(size,0))/1073741824.0, 2), sum(critical) from artifacts group by kind order by 3 desc'):
    print(f'  {r[0]:22s} {r[1]:7d} items {r[2]:8.2f} GiB  critical {r[3]}')
