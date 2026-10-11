"""On a fleet worker (or anywhere): scores and small previews for ink maps of ANY model set, without the per-model naming
rules of stroke_score.py / ensemble_maps.py. Per depth: mean-z ensemble (reading-side normalisation), the stroke score
(tools/stroke-score core, standard parameters; CT void mask if the render is given), the row-structure score (rowness.py),
and JPEG previews (reading ensemble, blind ensemble with the same stretch, CT layer 33+d), half resolution, render orientation.
Usage: post_models.py <maps dir> <name> <um> <models,comma> <depths,comma> <out dir> [render.zarr]"""
import json, os, sys, numpy as np, tifffile, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, 'stroke-score-src')); sys.path.insert(0, HERE)
from stroke_score.core import Params, ensemble, usable_area, score
import importlib.util
spec = importlib.util.spec_from_file_location('rowness_mod', os.path.join(HERE, 'rowness_lib.py')); rl = importlib.util.module_from_spec(spec); spec.loader.exec_module(rl)
mdir, name, um, models, depths, out = sys.argv[1], sys.argv[2], float(sys.argv[3]), sys.argv[4].split(','), [int(x) for x in sys.argv[5].split(',')], sys.argv[6]
Z = sys.argv[7] if len(sys.argv) > 7 else None
os.makedirs(out, exist_ok=True); p = Params(um=um); res_all = {'name': name, 'models': models, 'um': um, 'depths': {}}
zarr_a = None
if Z and os.path.isdir(os.path.join(Z, '0')):
    import zarr; zarr_a = zarr.open(Z, mode='r')['0']
for d in depths:
    s = 25 + d; paths = {m: (f'{mdir}/{name}__{m}__L66s{s}_reverse.tif', f'{mdir}/{name}__{m}__L66s{s}.tif') for m in models}
    if not all(os.path.exists(a) and os.path.exists(b) for a, b in paths.values()): continue
    valid = None
    for a, b in paths.values():
        v = (tifffile.imread(a) > 0) | (tifffile.imread(b) > 0); valid = v if valid is None else valid & v
    E, _ = ensemble(paths, valid)
    ct = np.asarray(zarr_a[33 + d]) if zarr_a is not None else None
    use, _ = usable_area(valid, p, ct) if ct is not None else usable_area(valid, p)
    sc, _ = score(E, valid, use, p)
    R, B = sc['sides']['reading'], sc['sides']['blind']
    rr, rw = rl.row_score(E['reading'], valid, um); rb, _ = rl.row_score(E['blind'], valid, um)
    res_all['depths'][d] = {'area_R': R['stroke_frac'], 'area_B': B['stroke_frac'], 'window_R': R['window']['max'], 'window_B': B['window']['max'],
                            'row_R': rr, 'row_B': rb, 'row_at': rw, 'top_tiles': sc['top_reading_tiles'][:5]}
    lo, hi = np.percentile(E['reading'][valid], [1, 99.7])
    for side in ('reading', 'blind'):
        im = np.clip((E[side] - lo) / (hi - lo) * 255, 0, 255).astype(np.uint8); im[~valid] = 0
        im = cv2.resize(im, (im.shape[1] // 2, im.shape[0] // 2), interpolation=cv2.INTER_AREA)
        cv2.imwrite(f'{out}/{name}__ens_{side}__d{d:+03d}.jpg', im, [cv2.IMWRITE_JPEG_QUALITY, 85])
    if ct is not None:
        v = ct[ct > 0]; clo, chi = (np.percentile(v, [1, 99.5]) if v.size else (0, 255))
        im = np.clip((ct.astype(np.float32) - clo) / max(chi - clo, 1) * 255, 0, 255).astype(np.uint8)
        im = cv2.resize(im, (im.shape[1] // 2, im.shape[0] // 2), interpolation=cv2.INTER_AREA)
        cv2.imwrite(f'{out}/{name}__ct__d{d:+03d}.jpg', im, [cv2.IMWRITE_JPEG_QUALITY, 85])
    print(f"{name} d{d:+d} area_R {R['stroke_frac']:.4f} area_B {B['stroke_frac']:.4f} win_R {R['window']['max']:.4f} win_B {B['window']['max']:.4f} row_R {rr:.3f} row_B {rb:.3f}")
json.dump(res_all, open(f'{out}/{name}__post.json', 'w'), indent=1, default=float)
