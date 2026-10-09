#!/usr/bin/env python3
"""stroke_score.py - rank areas of a 66-layer surface by stroke-like ink in the four-model ensemble, reading vs blind side.

  python stroke_score.py --surface <name>.zarr --maps <run_ink.sh outputs> --out <dir> --um 9.362 --depth 1 [--name N]

Per side (reading = "reverse" maps, blind = "forward" maps), at one depth:
  ensemble   per model z = (map - mean) / sd with the READING side's mean and sd over valid pixels at this depth
             (the same normalisation as ensemble_maps.py); ensemble E = mean of the model z-scores.
  background E minus its masked Gaussian mean (sigma --bg-mm), so slow brightness trends do not count as ink.
  strokes    pixels with E - background > --thr, 8-connected components whose area lies in [--amin-mm2, --amax-mm2]
             (letter-stroke sized; specks and broad blooms are dropped).
  tiles      square windows of --tile-mm on a --step-mm grid; score = fraction of the tile's valid pixels covered by
             strokes; tiles with < 60 % valid pixels are skipped.
The blind side is the null for the same sheet: real text should give reading tiles well above every blind tile.
Outputs <name>__strokes_d+NN.json (parameters, per-side tile statistics, top reading tiles in READING orientation =
rotated 180 deg, as in ensemble_maps.py) and <name>__strokes_d+NN.png (reading tile scores over blind, side by side).
"""
import argparse, json, os, time
import numpy as np
import cv2

MODELS = [('dnative', 'dnative'), ('hecate', 'hecate'),
          ('ink9-42', 'hybrid_3d2d-seed42'), ('ink9-43', 'hybrid_3d2d-seed43')]
N66, MID = 66, 33


def map_path(maps, name, mk, direction, d):
    rev = '_reverse' if direction == 'reverse' else ''
    if mk == 'hecate':
        p = os.path.join(maps, f'{name}__hecate__L66zc{32.5 + d:.2f}{rev}.png')
    else:
        p = os.path.join(maps, f'{name}__{mk}__L66s{d + 25}{rev}.tif')
    return p if os.path.isfile(p) else None


def read_map(path, shape):
    import tifffile
    if path.lower().endswith('.png'):
        a = cv2.imread(path, cv2.IMREAD_UNCHANGED)
        if a.ndim == 3:
            a = a[..., 0]
        a = a.astype(np.float32) / (65535. if a.dtype == np.uint16 else 255.)
        if a.shape != tuple(shape):
            a = cv2.resize(a, (shape[1], shape[0]), interpolation=cv2.INTER_LINEAR)
    else:
        a = tifffile.imread(path)
        if a.dtype == np.uint8:
            a = np.clip((a.astype(np.float32) - 64.) / 128., 0, 1)
        elif a.dtype == np.uint16:
            a = a.astype(np.float32) / 65535.
        else:
            a = a.astype(np.float32)
        if a.shape != tuple(shape):
            raise ValueError(f'{path}: shape {a.shape} != surface {tuple(shape)}')
    return np.ascontiguousarray(a, dtype=np.float32)


def valid_mask(surface, cache):
    if cache and os.path.isfile(cache):
        return cv2.imread(cache, cv2.IMREAD_UNCHANGED) > 0
    import zarr
    st = zarr.open_group(surface, mode='r')['0']
    H, W = int(st.shape[1]), int(st.shape[2])
    v = np.zeros((H, W), bool)
    for r0 in range(0, H, 128):
        v[r0:r0 + 128] = (np.asarray(st[:, r0:r0 + 128, :]) > 0).all(0)
    if cache:
        cv2.imwrite(cache, v.astype(np.uint8) * 255)
    return v


def masked_blur(E, valid, sigma_px):
    """Gaussian mean of E over valid pixels, computed at 1/f scale (sigma >> pixel)."""
    f = max(1, int(sigma_px // 8))
    H, W = E.shape
    w = valid.astype(np.float32)
    small = lambda a: cv2.resize(a, (max(1, W // f), max(1, H // f)), interpolation=cv2.INTER_AREA)
    num, den = small(E * w), small(w)
    s = sigma_px / f
    num = cv2.GaussianBlur(num, (0, 0), s, borderType=cv2.BORDER_REFLECT)
    den = cv2.GaussianBlur(den, (0, 0), s, borderType=cv2.BORDER_REFLECT)
    bg = num / np.maximum(den, 1e-3)
    return cv2.resize(bg, (W, H), interpolation=cv2.INTER_LINEAR)


def strokes(E, valid, a):
    bg = masked_blur(E, valid, a.bg_mm * 1000 / a.um)
    m = ((E - bg) > a.thr) & valid
    n, lab, st, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8), connectivity=8)
    px_mm2 = (a.um / 1000.) ** 2
    area = st[:, cv2.CC_STAT_AREA] * px_mm2
    keep = (area >= a.amin_mm2) & (area <= a.amax_mm2)
    keep[0] = False
    return keep[lab], int(keep.sum()), n - 1


def tile_scores(S, valid, a):
    t = max(8, int(round(a.tile_mm * 1000 / a.um)))
    step = max(4, int(round(a.step_mm * 1000 / a.um)))
    H, W = S.shape
    cs = lambda x: np.pad(x.astype(np.float64), ((1, 0), (1, 0))).cumsum(0).cumsum(1)
    I_s, I_v = cs(S & valid), cs(valid)
    ys = np.arange(0, max(1, H - t + 1), step)
    xs = np.arange(0, max(1, W - t + 1), step)
    box = lambda I: I[ys[:, None] + t, xs[None, :] + t] - I[ys[:, None], xs[None, :] + t] \
        - I[ys[:, None] + t, xs[None, :]] + I[ys[:, None], xs[None, :]]
    nv, ns = box(I_v), box(I_s)
    tv = min(t, H) * min(t, W)
    sc = np.where(nv >= 0.6 * tv, ns / np.maximum(nv, 1), np.nan)
    return sc, ys, xs, t


def summary(sc):
    v = sc[np.isfinite(sc)]
    if v.size == 0:
        return dict(n_tiles=0)
    return dict(n_tiles=int(v.size), max=float(v.max()), p99=float(np.percentile(v, 99)),
                p95=float(np.percentile(v, 95)), median=float(np.median(v)), mean=float(v.mean()))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--surface', required=True)
    ap.add_argument('--maps', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--name')
    ap.add_argument('--um', type=float, required=True, help='render pixel size in micrometres')
    ap.add_argument('--depth', type=int, default=1)
    ap.add_argument('--thr', type=float, default=2.0, help='ensemble z above background')
    ap.add_argument('--bg-mm', type=float, default=1.5)
    ap.add_argument('--amin-mm2', type=float, default=0.02)
    ap.add_argument('--amax-mm2', type=float, default=1.5)
    ap.add_argument('--tile-mm', type=float, default=4.0)
    ap.add_argument('--step-mm', type=float, default=1.0)
    ap.add_argument('--top', type=int, default=10)
    ap.add_argument('--models', default='dnative,hecate,ink9-42,ink9-43', help='subset of the ensemble (comma list)')
    ap.add_argument('--tag', default='', help='suffix for the output names (e.g. a model subset)')
    ap.add_argument('--edge-mm', type=float, default=0.5, help='ignore this margin inside the valid area')
    ap.add_argument('--void-frac', type=float, default=0.0,
                    help='CT voids: smoothed CT (layers 33+d-1..33+d+1) below p1 + frac*(p99.5-p1) of the valid CT')
    ap.add_argument('--void-dilate-mm', type=float, default=0.25)
    ap.add_argument('--hole-mm2', type=float, default=0.5, help='invalid holes smaller than this get no edge margin')
    ap.add_argument('--no-png', action='store_true')
    ap.add_argument('--crops', type=int, default=0, help='write review crops (reading E | blind E | CT) of the top N tiles')
    ap.add_argument('--zrange', type=float, nargs=2, default=(-1.0, 4.0), help='fixed ensemble-z stretch of the crops')
    a = ap.parse_args()
    t0 = time.time()
    name = a.name or os.path.basename(a.surface.rstrip('/'))[:-5]
    os.makedirs(a.out, exist_ok=True)
    valid = valid_mask(a.surface, os.path.join(a.out, f'{name}__valid.png'))
    H, W = valid.shape
    d = a.depth
    import zarr
    st = zarr.open_group(a.surface, mode='r')['0']
    ct = np.asarray(st[MID + d - 1:MID + d + 2]).astype(np.float32).mean(0)
    ct = cv2.GaussianBlur(ct, (0, 0), 2.0)
    cp1, cp99 = (float(x) for x in np.percentile(ct[valid], [1, 99.5]))
    void = (ct < cp1 + a.void_frac * (cp99 - cp1)) & valid
    r = int(round(a.void_dilate_mm * 1000 / a.um))
    if r > 0:
        void = cv2.dilate(void.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))) > 0
    # pinholes (isolated zero voxels) must not punch edge-margin discs: fill holes < --hole-mm2 before eroding
    n, lab, cst, _ = cv2.connectedComponentsWithStats((~valid).astype(np.uint8), connectivity=8)
    small = cst[:, cv2.CC_STAT_AREA] * (a.um / 1000.) ** 2 < a.hole_mm2
    small[0] = False
    filled = valid | small[lab]
    r = int(round(a.edge_mm * 1000 / a.um))
    inner = cv2.erode(filled.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))) > 0 \
        if r > 0 else valid
    use = inner & valid & ~void
    maps = {}
    want = a.models.split(',')
    for sn, mk in MODELS:
        if sn not in want:
            continue
        pr, pf = map_path(a.maps, name, mk, 'reverse', d), map_path(a.maps, name, mk, 'forward', d)
        if pr and pf:
            maps[sn] = (pr, pf)
    if len(maps) < len(want):
        raise SystemExit(f'only {sorted(maps)} have both sides at d{d:+d}')
    E = {'reverse': np.zeros((H, W), np.float32), 'forward': np.zeros((H, W), np.float32)}
    norm = {}
    for sn, (pr, pf) in maps.items():
        R = read_map(pr, (H, W))
        v = R[valid].astype(np.float64)
        mu, sd = float(v.mean()), float(v.std()) + 1e-6
        norm[sn] = dict(mean=mu, sd=sd)
        E['reverse'] += (R - mu) / sd
        E['forward'] += (read_map(pf, (H, W)) - mu) / sd
    out = dict(name=name, depth=d, models=sorted(maps), um=a.um, H=H, W=W, valid_px=int(valid.sum()),
               used_px=int(use.sum()), void_px=int(void.sum()), ct_p1=cp1, ct_p99_5=cp99,
               params=dict(thr=a.thr, bg_mm=a.bg_mm, amin_mm2=a.amin_mm2, amax_mm2=a.amax_mm2,
                           tile_mm=a.tile_mm, step_mm=a.step_mm, edge_mm=a.edge_mm, hole_mm2=a.hole_mm2, void_frac=a.void_frac,
                           void_dilate_mm=a.void_dilate_mm), norm=norm, sides={})
    grids = {}
    Ez = {}
    for side, label in (('reverse', 'reading'), ('forward', 'blind')):
        Es = E[side] / len(maps)
        Ez[label] = Es
        S, nk, nc = strokes(Es, valid, a)
        S &= use
        sc, ys, xs, t = tile_scores(S, use, a)
        grids[label] = sc
        out['sides'][label] = dict(components_kept=nk, components_all=nc,
                                   stroke_frac=float(S[use].mean()), tiles=summary(sc))
    # top reading tiles, coordinates in reading orientation (rotated 180 deg) and in raw render pixels
    sc = grids['reading']
    blind_max = out['sides']['blind']['tiles'].get('max', float('nan'))
    order = np.argsort(np.where(np.isfinite(sc), -sc, np.inf), axis=None)
    top = []
    for k in order:
        if len(top) >= a.top or not np.isfinite(sc.flat[k]):
            break
        i, j = np.unravel_index(k, sc.shape)
        y, x = int(ys[i]), int(xs[j])
        if any(abs(y - q['raw_y']) < t and abs(x - q['raw_x']) < t for q in top):
            continue
        vt, ut = valid[y:y + t, x:x + t], use[y:y + t, x:x + t]
        top.append(dict(score=float(sc[i, j]), blind=float(grids['blind'][i, j]), raw_y=y, raw_x=x,
                        damage=round(1 - float(ut.sum()) / max(float(vt.sum()), 1), 3),
                        read_y=H - y - t, read_x=W - x - t, size_px=t))
    out['top_reading_tiles'] = top
    rs = out['sides']['reading']['tiles']
    out['ratio_max_reading_over_max_blind'] = float(rs['max'] / blind_max) if rs.get('max') and blind_max > 0 else None
    out['seconds'] = round(time.time() - t0, 1)
    stem = os.path.join(a.out, f'{name}__strokes{a.tag}_d{d:+03d}')
    json.dump(out, open(stem + '.json', 'w'), indent=1)
    if not a.no_png:
        hi = max(np.nanmax(grids['reading']), np.nanmax(grids['blind']), 1e-6)
        ims = []
        for label in ('reading', 'blind'):
            g = grids[label][::-1, ::-1]
            b = np.where(np.isfinite(g), np.clip(g / hi, 0, 1) * 255, 0).astype(np.uint8)
            ims.append(cv2.resize(b, (b.shape[1] * 4, b.shape[0] * 4), interpolation=cv2.INTER_NEAREST))
        sep = np.full((ims[0].shape[0], 8), 128, np.uint8)
        cv2.imwrite(stem + '.png', np.concatenate([ims[0], sep, ims[1]], axis=1))
    if a.crops:
        lo, hi = a.zrange
        for r, q in enumerate(top[:a.crops], 1):
            y0, x0, t = q['raw_y'], q['raw_x'], q['size_px']
            ya, yb = max(0, y0 - t // 2), min(H, y0 + t + t // 2)
            xa, xb = max(0, x0 - t // 2), min(W, x0 + t + t // 2)
            pan = []
            for label in ('reading', 'blind'):
                c = np.clip((Ez[label][ya:yb, xa:xb] - lo) / (hi - lo), 0, 1) * 255
                c[~use[ya:yb, xa:xb]] *= 0.35
                pan.append(c.astype(np.uint8))
            ct = np.asarray(st[MID + d, ya:yb, xa:xb]).astype(np.float32)
            v = ct[valid[ya:yb, xa:xb]]
            if v.size:
                p1, p99 = np.percentile(v, [1, 99.5])
                ct = np.clip((ct - p1) / max(p99 - p1, 1), 0, 1) * 255
            pan.append(ct.astype(np.uint8))
            pan = [np.ascontiguousarray(x[::-1, ::-1]) for x in pan]          # reading orientation
            sep = np.full((pan[0].shape[0], 6), 128, np.uint8)
            cv2.imwrite(f'{stem}__top{r:02d}.png', np.concatenate([pan[0], sep, pan[1], sep, pan[2]], axis=1))
    print(json.dumps({k: out[k] for k in ('name', 'depth', 'models', 'ratio_max_reading_over_max_blind')}),
          json.dumps(out['sides']), f'{out["seconds"]}s', flush=True)


if __name__ == '__main__':
    main()
