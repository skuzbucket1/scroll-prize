"""Is a bright mark on one winding writing, or structure that runs through the stack? For a window on a winding (full
resolution, reading orientation) this shows the reading-side ensemble, the blind side and the CT layer 33+d, and the
same place on neighbouring windings, found through the 3D meshes (the neighbour's mesh node nearest to the window's
centre). Writing sits on one turn and on the reading side; a crack or a fold shows in the CT and lines up on
consecutive turns. Windows are given as y,x (top left, render pixels of the main winding) or picked as the `top`
non-overlapping windows with the highest mean reading-minus-blind ensemble.
Usage: neighbour_view.py <scroll dir (data/PHercNNNN)> <fit> <winding> <neighbours,> <out dir> [--models readerv2,d9v4c] (all options: --help)
       [--depth 0] [--win y,x ...] [--top 3] [--h-mm 8] [--w-mm 14] [--um 9.362] [--shrink 2]"""
import argparse, json, os, sys
import cv2, numpy as np, tifffile, zarr
from scipy.spatial import cKDTree
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, 'stroke-score-src'))
from stroke_score.core import ensemble

ap = argparse.ArgumentParser()
ap.add_argument('scroll'); ap.add_argument('fit'); ap.add_argument('w'); ap.add_argument('nb'); ap.add_argument('out')
ap.add_argument('--models', default='readerv2,d9v4c'); ap.add_argument('--depth', type=int, default=0)
ap.add_argument('--win', nargs='*', default=[]); ap.add_argument('--top', type=int, default=3)
ap.add_argument('--h-mm', type=float, default=8.0); ap.add_argument('--w-mm', type=float, default=14.0)
ap.add_argument('--um', type=float, default=9.362); ap.add_argument('--shrink', type=int, default=2)
a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
s = 25 + a.depth; h, w = int(a.h_mm * 1000 / a.um), int(a.w_mm * 1000 / a.um)


def load(name):
    maps = f'{a.scroll}/ink/{a.fit}/maps'
    paths = {m: (f'{maps}/{name}__{m}__L66s{s}_reverse.tif', f'{maps}/{name}__{m}__L66s{s}.tif') for m in a.models.split(',')}
    if not all(os.path.exists(p) and os.path.exists(q) for p, q in paths.values()):
        return None
    valid = None
    for p, q in paths.values():
        v = (tifffile.imread(p) > 0) | (tifffile.imread(q) > 0); valid = v if valid is None else valid & v
    E, _ = ensemble(paths, valid)
    mdir = f'{a.scroll}/geometry/{a.fit}/flattened/{name}/tifxyz/flatten.tifxyz'
    X, Y, Z = (tifffile.imread(f'{mdir}/{k}.tif').astype(np.float64) for k in 'xyz')
    sc = json.load(open(f'{mdir}/meta.json'))['scale'][0]
    ok = (X >= 0) & (Y >= 0) & (Z >= 0); rr, cc = np.nonzero(ok)
    return dict(name=name, E=E, valid=valid, ct=zarr.open(f'{a.scroll}/renders/{a.fit}/{name}.zarr', mode='r')['0'],
                nodes=np.stack([Z[rr, cc], Y[rr, cc], X[rr, cc]], 1), rc=np.stack([rr, cc], 1) / sc, tree=None, XYZ=(X, Y, Z), sc=sc)


main = load(a.w)
others = [o for o in (load(n) for n in a.nb.split(',') if n) if o is not None]
H, W = main['valid'].shape
if a.win:
    wins = [tuple(int(v) for v in t.split(',')) for t in a.win]
else:                                                   # top windows by mean reading - blind, at 1/8 resolution
    f = 8; D = cv2.GaussianBlur(main['E']['reading'] - main['E']['blind'], (0, 0), 2)[::f, ::f].astype(np.float32)
    V = main['valid'][::f, ::f].astype(np.float32); D[V == 0] = 0
    kh, kw = max(1, h // f), max(1, w // f)
    S = cv2.boxFilter(D, -1, (kw, kh), normalize=True, borderType=cv2.BORDER_CONSTANT)
    C = cv2.boxFilter(V, -1, (kw, kh), normalize=True, borderType=cv2.BORDER_CONSTANT); S[C < 0.6] = -1e9
    wins = []
    for _ in range(a.top):
        y, x = np.unravel_index(np.argmax(S), S.shape)
        if S[y, x] < -1e8:
            break
        wins.append((int(y * f - h / 2), int(x * f - w / 2)))
        S[max(0, y - kh):y + kh, max(0, x - kw):x + kw] = -1e9


def crop(o, yc, xc, lo_hi=None):
    Hh, Ww = o['valid'].shape; y0 = int(max(0, min(yc - h // 2, Hh - h))); x0 = int(max(0, min(xc - w // 2, Ww - w)))
    v = o['valid'][y0:y0 + h, x0:x0 + w]; out = []
    lo, hi = np.percentile(o['E']['reading'][o['valid']], [1, 99.7])
    for side in ('reading', 'blind'):
        c = cv2.GaussianBlur(o['E'][side], (0, 0), 1.5)[y0:y0 + h, x0:x0 + w]
        im = np.clip((c - lo) / (hi - lo) * 255, 0, 255).astype(np.uint8); im[~v] = 0; out.append(im)
    ct = np.asarray(o['ct'][33 + a.depth, y0:y0 + h, x0:x0 + w]).astype(np.float32); vv = ct[ct > 0]
    clo, chi = np.percentile(vv, [1, 99.5]) if vv.size else (0, 255)
    out.append(np.clip((ct - clo) / max(chi - clo, 1) * 255, 0, 255).astype(np.uint8))
    pad = lambda im: cv2.copyMakeBorder(im, 0, h - im.shape[0], 0, w - im.shape[1], cv2.BORDER_CONSTANT, value=0)
    return [pad(im)[::-1, ::-1] for im in out], (y0, x0)                  # reading orientation: rotated 180 degrees


def at3d(o, y, x):
    """3D position (zyx) of the valid mesh node nearest to render pixel (y, x)."""
    i = int(np.argmin(((o['rc'] - [y, x]) ** 2).sum(1))); return o['nodes'][i]


mm5 = 5000 / a.um
for k, (y0, x0) in enumerate(wins):
    yc, xc = y0 + h // 2, x0 + w // 2; p = at3d(main, yc, xc)
    rows = []
    order = sorted([main] + others, key=lambda o: o['name'])
    for o in order:
        if o is main:
            pan, (yy, xx) = crop(o, yc, xc); lab = f'{o["name"]} (this winding)  y {yy} x {xx}'
        else:
            if o['tree'] is None:
                o['tree'] = cKDTree(o['nodes'])
            d, i = o['tree'].query(p); r, c = o['rc'][i]
            pan, (yy, xx) = crop(o, r, c); lab = f'{o["name"]}  same place, {d * a.um / 1000:.2f} mm away'
        tiles = []
        for im, nm in zip(pan, ('ink, reading side', 'ink, blind side', f'CT layer {33 + a.depth}')):
            t = cv2.cvtColor(im, cv2.COLOR_GRAY2BGR)
            t = cv2.resize(t, (w // a.shrink, h // a.shrink), interpolation=cv2.INTER_AREA)
            cv2.putText(t, f'{lab}: {nm}', (8, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)
            b = int(mm5 / a.shrink); cv2.line(t, (10, t.shape[0] - 10), (10 + b, t.shape[0] - 10), (255, 255, 255), 2)
            cv2.putText(t, '5 mm', (10, t.shape[0] - 16), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1, cv2.LINE_AA)
            tiles.append(cv2.copyMakeBorder(t, 2, 2, 2, 2, cv2.BORDER_CONSTANT, value=(30, 30, 30)))
        rows.append(np.concatenate(tiles, 1))
    img = np.concatenate(rows, 0)
    fn = os.path.join(a.out, f'{a.w}_d{a.depth:+d}_win{k + 1}.jpg'); cv2.imwrite(fn, img, [cv2.IMWRITE_JPEG_QUALITY, 90])
    rb = float((main['E']['reading'] - main['E']['blind'])[y0:y0 + h, x0:x0 + w][main['valid'][y0:y0 + h, x0:x0 + w]].mean())
    print(f'{a.w} window {k + 1}: y {y0} x {x0} (render px), mean reading - blind {rb:+.3f} -> {fn}')
