"""Update the row-score fields of post_models.py results (__post.json) to the current stroke-score row score, without
redoing the stroke score, tiles and previews (the row score is the only part that changed). Rebuilds the mean-z ensemble
from the maps and rewrites row_R, row_B, row_at, row_at_B and row_strips. Skips results that already have row_strips.
Usage: rerow_post.py <maps dir> <post dir> [--force]"""
import glob, json, os, sys
import numpy as np, tifffile
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, 'stroke-score-src'))
from stroke_score.core import Params, ensemble, row_score

mdir, post = sys.argv[1], sys.argv[2]; force = '--force' in sys.argv
for f in sorted(glob.glob(os.path.join(post, '**', '*__post.json'), recursive=True)):
    j = json.load(open(f)); p = Params(um=j['um'])
    if not force and all('row_strips' in r for r in j['depths'].values()):
        continue
    for d, r in j['depths'].items():
        s = 25 + int(d); paths = {m: (f'{mdir}/{j["name"]}__{m}__L66s{s}_reverse.tif', f'{mdir}/{j["name"]}__{m}__L66s{s}.tif') for m in j['models']}
        valid = None
        for a, b in paths.values():
            v = (tifffile.imread(a) > 0) | (tifffile.imread(b) > 0); valid = v if valid is None else valid & v
        E, _ = ensemble(paths, valid)
        (rr, ra), (rb, rba) = row_score(E['reading'], valid, p), row_score(E['blind'], valid, p)
        print(f"{j['name']} d{int(d):+d} row {r['row_R']:.3f}/{r['row_B']:.3f} -> {rr:.3f}/{rb:.3f}", flush=True)
        r.update(row_R=rr, row_B=rb, row_at=ra, row_at_B=rba, row_strips=p.row_strips)
    json.dump(j, open(f + '.tmp', 'w'), indent=1, default=float); os.replace(f + '.tmp', f)
