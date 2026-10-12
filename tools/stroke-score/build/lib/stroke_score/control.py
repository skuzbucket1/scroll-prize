"""Known-text control kit: public segments with known text at the 9 um scan type, and an evaluator that scores ANY ink
model's maps on them the same way as on a search winding (stroke score, row score) plus AUC against a reference.

  stroke-score control list
  stroke-score control fetch 0841-ag2814 controls/            # mesh + reference map + labels (no CT; < 70 MB)
  stroke-score control eval --control 0841-ag2814 --fetched controls/ --maps maps/ --name c0841_ag2814_66 --depth 1 \
                            [--models auto] [--surface render.zarr]

How to make the maps: render the fetched mesh as a 66-layer surface volume from the public CT (the URL is printed by
`list`), e.g. `vc_render_tifxyz --volume <cache> --remote-url <volume URL> --group-idx 0 --scale 1 --segmentation <mesh>
--num-slices 66 --slice-step 1 --zarr-output <name>.zarr`, then run your model on a 17-layer window centred on layer 33 + d
for both directions (reading side = the reversed layer order for these renders), writing <name>__<model>__L66s<25+d>.tif
and ..._reverse.tif; or any naming via a JSON map list.
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.request

import cv2
import numpy as np

S3 = 'https://vesuvius-challenge-open-data.s3.amazonaws.com'
CONTROLS = {
    '0139-w047': dict(
        scroll='PHerc0139', um=9.362, name='c0139_w047_66',
        volume=f'{S3}/PHerc0139/volumes/20250728140407-9.362um-1.2m-113keV-masked.zarr',
        mesh='PHerc0139/segments/20260206000001-w047_2026020613/mesh/20260206000001-on-20250728140407-9.362um.tifxyz/',
        reference='PHerc0139/segments/20260206000001-w047_2026020613/ink-detection/PHerc0139-20260206000001-2.399um-0.22m-78keV-volume-'
                  '20260102150214-20260417190342-new_canon_autoresearch_recipe-tile256-stride128.tif',
        labels=None, supervision=None,
        note='Known text over most of the segment. Held out by ink_9um, dense_native and Reader v2; d9v2/d9v3/d9v4C and '
             'Scheirer ft_s42 trained on it (do not evaluate those here). Reference = a 2.4 um / 78 keV ink prediction.'),
    '0841-ag2814': dict(
        scroll='PHerc0841', um=9.366, name='c0841_ag2814_66',
        volume=f'{S3}/PHerc0841/volumes/20250821151531-9.366um-1.2m-113keV-masked.zarr',
        mesh='PHerc0841/segments/20260221022814-auto_grown_20260220174252405/mesh/20260221022814-on-20250821151531-9.366um.tifxyz/',
        reference='PHerc0841/segments/20260221022814-auto_grown_20260220174252405/ink-detection/PHerc0841-20260221022814-2.403um-0.22m-'
                  '77keV-volume-20260319124803-20260417190342-new_canon_autoresearch_recipe-tile256-stride128.tif',
        labels='PHerc0841/segments/20260221022814-auto_grown_20260220174252405/ink-labels/2.403um-volume-20260319124803/20260918/inklabels.zarr/',
        supervision='PHerc0841/segments/20260221022814-auto_grown_20260220174252405/ink-labels/2.403um-volume-20260319124803/20260918/supervision.zarr/',
        note='A scroll ink_9um, dense_native, Reader v2, d9v2/d9v3/d9v4C and ft_s42 did not train on (Hecate may have). '
             'Human ink labels (two text rows) with a supervision mask; scored inside the mask.'),
}


def _keys(prefix: str) -> list:
    out, token = [], None
    while True:
        url = f'{S3}/?list-type=2&prefix={prefix}' + (f'&continuation-token={urllib.request.quote(token)}' if token else '')
        x = urllib.request.urlopen(url, timeout=60).read().decode()
        out += re.findall(r'<Key>([^<]+)</Key>', x)
        m = re.search(r'<NextContinuationToken>([^<]+)</NextContinuationToken>', x)
        if not m:
            return out
        token = m.group(1)


def _get(key: str, dest: str) -> None:
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if not os.path.exists(dest):
        urllib.request.urlretrieve(f'{S3}/{key}', dest + '.part'); os.replace(dest + '.part', dest)


def fetch(cid: str, out: str) -> None:
    c = CONTROLS[cid]; d = os.path.join(out, cid)
    for k in _keys(c['mesh']):
        _get(k, os.path.join(d, 'mesh.tifxyz', os.path.relpath(k, c['mesh'])))
    _get(c['reference'], os.path.join(d, 'reference.tif'))
    for what in ('labels', 'supervision'):
        if c[what]:
            for k in _keys(c[what]):
                _get(k, os.path.join(d, f'{what}.zarr', os.path.relpath(k, c[what])))
    json.dump({k: v for k, v in c.items()}, open(os.path.join(d, 'control.json'), 'w'), indent=1)
    print(f'{cid} -> {d} (mesh, reference' + (', labels' if c['labels'] else '') + ')')


def _load2d(p: str) -> np.ndarray:
    if p.endswith('.zarr'):
        import zarr
        return np.asarray(zarr.open(p, mode='r')['0'])
    import tifffile
    return tifffile.imread(p)


def _auc(score: np.ndarray, pos: np.ndarray, valid: np.ndarray) -> float:
    s, p = score[valid], pos[valid]
    n1 = int(p.sum()); n0 = p.size - n1
    if n1 == 0 or n0 == 0:
        return float('nan')
    r = np.argsort(np.argsort(s, kind='stable'), kind='stable').astype(np.float64) + 1
    return float((r[p].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def _shift(a: np.ndarray, dy: int, dx: int) -> np.ndarray:
    H, W = a.shape; out = np.zeros_like(a)
    ys, yd = (slice(dy, None), slice(0, H - dy)) if dy >= 0 else (slice(0, H + dy), slice(-dy, None))
    xs, xd = (slice(dx, None), slice(0, W - dx)) if dx >= 0 else (slice(0, W + dx), slice(-dx, None))
    out[ys, xs] = a[yd, xd]; return out


def evaluate(a) -> dict:
    from .cli import MODELS, nieuwlaar_paths
    from .core import Params, ensemble, map_footprint, read_map, row_score, score, shape_score, usable_area, valid_mask
    c = CONTROLS[a.control]; d = os.path.join(a.fetched, a.control); name = a.name or c['name']
    models = [m for m in MODELS if nieuwlaar_paths(a.maps, name, m, a.depth)] if a.models == 'auto' else a.models.split(',')
    maps = {m: nieuwlaar_paths(a.maps, name, m, a.depth) for m in models}
    maps = {m: v for m, v in maps.items() if v}
    if not maps:
        sys.exit(f'no maps for {name} at d{a.depth:+d} in {a.maps}')
    import tifffile
    H, W = tifffile.imread(next(iter(maps.values()))[0]).shape if not next(iter(maps.values()))[0].endswith('.png') else (None, None)
    p = Params(um=c['um'])
    if a.surface:
        valid = valid_mask(a.surface)
    else:
        valid = np.ones((H, W), bool)
        for pr, pb in maps.values():
            valid &= map_footprint(pr, (H, W)) | map_footprint(pb, (H, W))
    H, W = valid.shape
    use, _ = usable_area(valid, p)
    E, _ = ensemble(maps, valid)
    res, _ = score(E, valid, use, p)
    ref = cv2.resize(_load2d(os.path.join(d, 'labels.zarr' if c['labels'] else 'reference.tif')).astype(np.float32), (W, H), interpolation=cv2.INTER_AREA)
    msk = cv2.resize(_load2d(os.path.join(d, 'supervision.zarr')).astype(np.float32), (W, H), interpolation=cv2.INTER_NEAREST) > 0 if c['supervision'] else None
    v0 = cv2.erode(valid.astype(np.uint8), np.ones((31, 31), np.uint8)) > 0
    # global shift of the reference (the 2.4 um meshes are an affine map of the 9 um ones, a few pixels off): best r
    e4 = cv2.resize(E['reading'], (W // 4, H // 4), interpolation=cv2.INTER_AREA); r4 = cv2.resize(ref, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    m4 = cv2.resize(v0.astype(np.float32), (W // 4, H // 4), interpolation=cv2.INTER_AREA) > 0.99
    best = max(((dy, dx) for dy in range(-4, 5) for dx in range(-4, 5)),
               key=lambda t: np.corrcoef(e4[m4], np.roll(np.roll(r4, t[0], 0), t[1], 1)[m4])[0, 1])
    cand = [(4 * best[0] + i, 4 * best[1] + j) for i in range(-3, 4) for j in range(-3, 4)]
    dy, dx = max(cand, key=lambda t: np.corrcoef(E['reading'][v0], _shift(ref, *t)[v0])[0, 1])
    ref_s = _shift(ref, dy, dx); valid_eval = v0.copy()
    if msk is not None:
        valid_eval &= _shift(msk.astype(np.float32), dy, dx) > 0
    pos = ref_s >= 128
    table = {}
    for side in ('reading', 'blind'):
        table[f'ensemble/{side}'] = (_auc(E[side], pos, valid_eval), float(np.corrcoef(E[side][valid_eval], ref_s[valid_eval])[0, 1]))
        for m, (pr, pb) in maps.items():
            x = read_map(pr if side == 'reading' else pb, (H, W))
            table[f'{m}/{side}'] = (_auc(x, pos, valid_eval), float(np.corrcoef(x[valid_eval], ref_s[valid_eval])[0, 1]))
    R, B = res['sides']['reading'], res['sides']['blind']
    out = dict(control=a.control, name=name, depth=a.depth, models=sorted(maps), shift=[dy, dx], positives=float(pos[valid_eval].mean()),
               stroke=dict(area_R=R['stroke_frac'], area_B=B['stroke_frac'], window_R=R['window'].get('max'), window_B=B['window'].get('max'),
                           row_R=R['row']['score'], row_B=B['row']['score']),
               auc_r={k: dict(auc=v[0], r=v[1]) for k, v in table.items()})
    print(f"{a.control} {name} d{a.depth:+d} models={','.join(sorted(maps))} shift={dy},{dx}")
    s = out['stroke']
    print(f"  stroke score: area {s['area_R']:.4f} / {s['area_B']:.4f}  window {s['window_R']:.4f} / {s['window_B']:.4f}  "
          f"row {s['row_R']:.2f} / {s['row_B']:.2f}   (reading / blind)")
    if a.band_mm:
        # the row score as a search band of this height would see it: horizontal strips every 2 mm
        h, st, rs = int(a.band_mm * 1000 / c['um']), int(2000 / c['um']), []
        for y0 in range(0, H - h + 1, st):
            vb = np.zeros_like(valid); vb[y0:y0 + h] = valid[y0:y0 + h]
            if vb[y0:y0 + h].mean() >= 0.3:
                (rr, ra), (rb, rba) = row_score(E['reading'], vb, p), row_score(E['blind'], vb, p)
                sr, sb = shape_score(E['reading'], vb, p, ra)['score'], shape_score(E['blind'], vb, p, rba)['score']
                rs.append((rr, rb, sr if sr is not None else float('nan'), sb if sb is not None else float('nan')))
        if rs:
            R_, B_, SR, SB = np.array(rs).T
            out['band'] = dict(mm=a.band_mm, strips=len(rs), reading=dict(median=float(np.median(R_)), p25=float(np.percentile(R_, 25)),
                               max=float(R_.max())), blind=dict(median=float(np.median(B_)), max=float(B_.max())),
                               shape=dict(reading_median=float(np.nanmedian(SR)), blind_median=float(np.nanmedian(SB))),
                               rows=[list(x) for x in rs])
            print(f"  row score in {a.band_mm:g} mm bands ({len(rs)} strips): reading median {np.median(R_):.2f}, p25 "
                  f"{np.percentile(R_, 25):.2f}, max {R_.max():.2f}; blind median {np.median(B_):.2f}, max {B_.max():.2f}; "
                  f"shape median {np.nanmedian(SR):.2f} / {np.nanmedian(SB):.2f}")
    for k, v in sorted(table.items()):
        print(f'  {k:28s} AUC {v[0]:.3f}  r {v[1]:.3f}')
    if a.out:
        json.dump(out, open(a.out, 'w'), indent=1)
    return out


def add_parser(sub) -> None:
    c = sub.add_parser('control', help='known-text controls at the 9 um scan type: list, fetch, evaluate your maps')
    cs = c.add_subparsers(dest='ccmd', required=True)
    l = cs.add_parser('list'); l.set_defaults(fn=lambda a: [print(f'{k}: {v["scroll"]} {v["um"]} um\n  volume {v["volume"]}\n  mesh   {S3}/{v["mesh"]}\n  {v["note"]}') for k, v in CONTROLS.items()] and 0)
    f = cs.add_parser('fetch'); f.add_argument('control', choices=sorted(CONTROLS)); f.add_argument('out')
    f.set_defaults(fn=lambda a: fetch(a.control, a.out) or 0)
    e = cs.add_parser('eval')
    e.add_argument('--control', required=True, choices=sorted(CONTROLS)); e.add_argument('--fetched', required=True)
    e.add_argument('--maps', required=True); e.add_argument('--name'); e.add_argument('--depth', type=int, default=1)
    e.add_argument('--models', default='auto'); e.add_argument('--surface', help='the 66-layer render (for the valid mask)')
    e.add_argument('--band-mm', type=float, help='also score the rows in horizontal strips this tall (your search band height, e.g. 10.3)')
    e.add_argument('--out', help='write the result JSON here')
    e.set_defaults(fn=lambda a: evaluate(a) and 0)
