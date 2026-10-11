"""Row and shape scores of search windings inside the render-valid area (all 66 layers > 0; the row score leaves out its own
0.5 mm edge margin), as in post_models.py:
the like-for-like counterpart of the known-text controls cut into 10.3 mm strips.
Usage: band_nulls.py <scroll> <fit> <models,> <depths,> w..."""
import sys, os, numpy as np, tifffile, cv2
from dataclasses import replace
sys.path.insert(0, os.path.expanduser('~/scroll-prizes/bin/stroke-score-src'))
from stroke_score.core import Params, ensemble, row_score, shape_score, valid_mask
sc, fit, models, depths = sys.argv[1], sys.argv[2], sys.argv[3].split(','), [int(x) for x in sys.argv[4].split(',')]
P = f'/mnt/nvme/scroll-prizes/data/{sc}'; M = f'{P}/ink/{fit}/maps'; p = Params(um=9.362)
for w in sys.argv[5:]:
    z = f'{P}/renders/{fit}/{w}.zarr'
    if not os.path.isdir(z + '/0'):
        continue
    rv = valid_mask(z)
    for d in depths:
        s = 25 + d; paths = {m: (f'{M}/{w}__{m}__L66s{s}_reverse.tif', f'{M}/{w}__{m}__L66s{s}.tif') for m in models}
        if not all(os.path.exists(a) and os.path.exists(b) for a, b in paths.values()):
            continue
        fp = None
        for a, b in paths.values():
            v = (tifffile.imread(a) > 0) | (tifffile.imread(b) > 0); fp = v if fp is None else fp & v
        E, _ = ensemble(paths, fp)
        vb = fp & rv
        (rr, ra), (rb, rba) = row_score(E['reading'], vb, p), row_score(E['blind'], vb, p)
        sr, sb = shape_score(E['reading'], vb, p, ra), shape_score(E['blind'], vb, p, rba)
        f = lambda x: 'nan' if x['score'] is None else f"{x['score']:.3f}"
        print(f'{sc} {w} d{d:+d} {len(models)}m row {rr:.3f} / {rb:.3f} shape {f(sr)} / {f(sb)} marks {sr["marks"]}', flush=True)
print('BANDNULLS-EXIT')
