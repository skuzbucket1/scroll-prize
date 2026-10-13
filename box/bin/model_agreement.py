"""Do the six ink models agree that a spot is one-sided (reading side brighter than the blind side)? On known letters they
should all agree; on a false alarm (blobs at a crack or a hole) often only some do. Per tile: for each model, the mean
reading-minus-blind map value in units of that model's own reading-side spread over the render (Nieuwlaar's display
rules: villa maps v -> clip((v - 64) / 128, 0, 1), Hecate v / 255 resized to the render grid; reading = _reverse maps),
and the number of models above `thr`.
Tiles: with --boxes, every letter box is a tile ('letter') and a grid of `tile`-pixel squares away from the boxes gives
'background' tiles; with --bare, every box of that file is a 'bare' tile (known bare papyrus, e.g. tiles inside a
supervision mask with no labelled ink); with --window y0 x0 h w, a grid of tiles inside the window ('window').
--swap treats the plain maps as the reading side (for a render whose mesh normal points into the papyrus).
--relative subtracts each model's median reading - blind over the render before scaling, so that a render whose blind
face is globally brighter (PHerc0841 ag2814) is judged on local one-sidedness only.
Usage: model_agreement.py <render.zarr> <maps dir> <name> <depth> <out.tsv> [--boxes letter_boxes.json] [--bare bare_boxes.json] [--swap] [--relative] [--window y0 x0 h w]
       [--tile 300] [--thr 0.2] [--models dnative,hybrid_3d2d-seed42,hybrid_3d2d-seed43,hecate,readerv2,d9v4c] [--label ...]"""
import argparse, json, os
import cv2, numpy as np, tifffile, zarr

ap = argparse.ArgumentParser()
for k in ('render', 'maps', 'name'):
    ap.add_argument(k)
ap.add_argument('depth', type=int); ap.add_argument('out'); ap.add_argument('--boxes'); ap.add_argument('--bare'); ap.add_argument('--swap', action='store_true'); ap.add_argument('--relative', action='store_true')
ap.add_argument('--window', type=int, nargs=4)
ap.add_argument('--tile', type=int, default=300); ap.add_argument('--thr', type=float, default=0.2); ap.add_argument('--label', default='')
ap.add_argument('--models', default='dnative,hybrid_3d2d-seed42,hybrid_3d2d-seed43,hecate,readerv2,d9v4c')
a = ap.parse_args()
R = zarr.open(a.render, mode='r')['0']; H, W = R.shape[1:]; valid = np.asarray(R[33 + a.depth]) > 0


def load(m, rev):
    suf = '_reverse' if rev else ''
    if m == 'hecate':
        f = os.path.join(a.maps, f'{a.name}__hecate__L66zc{32.5 + a.depth:.2f}{suf}.png')
        if not os.path.exists(f):
            return None
        v = cv2.imread(f, cv2.IMREAD_UNCHANGED); v = v[..., 0] if v.ndim == 3 else v
        return cv2.resize(v.astype(np.float32) / 255.0, (W, H), interpolation=cv2.INTER_LINEAR)
    f = os.path.join(a.maps, f'{a.name}__{m}__L66s{25 + a.depth}{suf}.tif')
    return np.clip((tifffile.imread(f).astype(np.float32) - 64) / 128, 0, 1) if os.path.exists(f) else None


Z = {}
for m in a.models.split(','):
    r, b = load(m, not a.swap), load(m, a.swap)
    if r is None or b is None:
        print('missing', m); continue
    sd = r[valid].std() or 1.0; off = float(np.median((r - b)[valid])) if a.relative else 0.0
    Z[m] = (r - b - off) / sd
tiles = []
if a.boxes:
    boxes = np.array([l['box'] for l in json.load(open(a.boxes))['letters']]).round().astype(int)
    near = np.zeros((H, W), bool)
    for x0, y0, x1, y1 in boxes:
        tiles.append(('letter', y0, x0, y1 - y0, x1 - x0)); near[max(0, y0 - 150):y1 + 150, max(0, x0 - 150):x1 + 150] = True
    for y in range(0, H - a.tile, a.tile):
        for x in range(0, W - a.tile, a.tile):
            if not near[y:y + a.tile, x:x + a.tile].any() and valid[y:y + a.tile, x:x + a.tile].mean() > 0.8:
                tiles.append(('background', y, x, a.tile, a.tile))
if a.bare:
    for l in json.load(open(a.bare))['letters']:
        x0, y0, x1, y1 = (int(round(v)) for v in l['box']); tiles.append(('bare', y0, x0, y1 - y0, x1 - x0))
if a.window:
    wy, wx, wh, ww = a.window
    for y in range(wy, wy + wh - a.tile + 1, a.tile):
        for x in range(wx, wx + ww - a.tile + 1, a.tile):
            if valid[y:y + a.tile, x:x + a.tile].mean() > 0.8:
                tiles.append(('window', y, x, a.tile, a.tile))
models = list(Z)
with open(a.out, 'w') as fo:
    fo.write('set\tclass\ty\tx\th\tw\t' + '\t'.join(models) + '\tmodels_one_sided\tmean\n')
    summ = {}
    for cl, y, x, h, w in tiles:
        v = valid[y:y + h, x:x + w]
        vals = [float(Z[m][y:y + h, x:x + w][v].mean()) for m in models]
        k = sum(val > a.thr for val in vals); summ.setdefault(cl, []).append((k, float(np.mean(vals))))
        fo.write(f'{a.label}\t{cl}\t{y}\t{x}\t{h}\t{w}\t' + '\t'.join(f'{val:+.3f}' for val in vals) + f'\t{k}\t{np.mean(vals):+.3f}\n')
for cl, L in summ.items():
    ks = np.array([t[0] for t in L]); mu = np.array([t[1] for t in L])
    print(f'{a.label} d{a.depth:+d} {cl}: {len(L)} tiles; models one-sided (of {len(models)}): mean {ks.mean():.1f}, '
          f'all {np.mean(ks == len(models)):.0%}, at least {len(models) - 1}: {np.mean(ks >= len(models) - 1):.0%}, at most 2: {np.mean(ks <= 2):.0%}; '
          f'mean reading - blind {mu.mean():+.2f}')
