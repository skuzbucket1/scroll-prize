"""Stroke score: how much stroke-sized ink an ink-model ensemble shows on the reading side of a segment, compared with
the blind side of the same sheet.

Per side (reading and blind), at one depth:
  ensemble    each model's map is turned into a z-score with the READING side's mean and SD over valid pixels; the
              ensemble E is the mean of the model z-scores (the normalisation used by Erwin Nieuwlaar's ensemble_maps.py).
  background  E minus its masked Gaussian mean (sigma `bg_mm`), so slow brightness trends do not count as ink.
  strokes     pixels more than `thr` above the background, kept as 8-connected components whose area lies between
              `amin_mm2` and `amax_mm2` (pen-stroke sized: specks and broad blooms are dropped).
  usable area valid pixels (CT > 0 in every render layer) minus an `edge_mm` margin; holes smaller than `hole_mm2`
              (isolated zero voxels) are filled first so they do not punch margins into the surface.
  scores      area: share of the usable area covered by strokes; tiles: best `tile_mm` square; window: best
              `window_mm` square (20 mm = 4 cm2, the First Letters area), clamped to the surface height.
The blind side is the null for the same sheet: text should raise the reading side only.

Added in 0.2:
  row score   text at 9 um shows as ROWS of strokes. In the best `row_window_mm` window (along x across y), the across-row
              profile of above-background pixel density (median of `row_strips` strips along the window, so lone blobs do
              not count) is autocorrelated at line-spacing lags `row_lag_mm`; the score is max(autocorrelation) x profile
              SD x 100. Known text scores 2.0-4.5 on the reading side, depending on the model set; see the README.
  shape       in the row window, the share of the marks' area in long thin marks (>= `shape_len_mm`, >= `shape_elong` x as
              long as wide): letters are strokes, crack edges and damage are blobs.
  profile     the reading/blind stroke density along the winding in `profile_bins` bins of the segment length, so that
              `stroke-score rank` can tell a pattern that repeats on neighbouring windings (sheet structure) from one
              that does not (text columns do not line up turn after turn).
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass

import cv2
import numpy as np


@dataclass
class Params:
    um: float                      # render pixel size in micrometres
    thr: float = 2.0               # ensemble z above background
    bg_mm: float = 1.5
    amin_mm2: float = 0.02
    amax_mm2: float = 1.5
    tile_mm: float = 4.0
    step_mm: float = 1.0
    window_mm: float = 20.0
    window_min_frac: float = 0.3
    tile_min_frac: float = 0.6
    edge_mm: float = 0.5
    hole_mm2: float = 0.5
    void_frac: float = 0.0         # optional CT-void mask (off by default; it over-masked the PHerc. 343 control)
    void_dilate_mm: float = 0.25
    top: int = 10
    row_window_mm: tuple = (20.0, 24.0)   # row score window: along the winding x across it
    row_lag_mm: tuple = (3.5, 8.0)        # Herculaneum line spacing is about 4.5-6 mm
    row_ds: int = 4                       # row score computed at 1/row_ds resolution
    row_min_cov: float = 0.5              # profile rows (across the window) with less valid area are left out
    row_min_mm: float = 8.0               # ... and a window needs this much of usable rows (search bands are ~10 mm tall)
    row_edge_mm: float = 0.5              # left out along the edge of the valid area (ink models light up mesh borders)
    row_strips: int = 4                   # per-row density = median over this many strips along the window (rows must run across it)
    profile_bins: int = 200
    shape_amin_mm2: float = 0.05          # shape score: marks at least this big count ...
    shape_len_mm: float = 1.0             # ... and are strokes when at least this long ...
    shape_elong: float = 2.0              # ... and at least this many times as long as wide
    shape_min_marks: int = 8              # fewer marks in the window: no shape score


def read_map(path: str, shape: tuple[int, int]) -> np.ndarray:
    """Ink map as float32 0..1 on the render grid.

    uint8 TIFFs (villa ink models store trunc(255 p)) get the display stretch clip((v - 64) / 128, 0, 1), which undoes
    the models' label smoothing; PNGs (Hecate, 9.6 um grid) are scaled to 0..1 and resized to the render grid.
    """
    if path.lower().endswith('.png'):
        a = cv2.imread(path, cv2.IMREAD_UNCHANGED)
        if a is None:
            raise IOError(path)
        if a.ndim == 3:
            a = a[..., 0]
        a = a.astype(np.float32) / (65535. if a.dtype == np.uint16 else 255.)
        if a.shape != tuple(shape):
            a = cv2.resize(a, (shape[1], shape[0]), interpolation=cv2.INTER_LINEAR)
    else:
        import tifffile
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


def map_footprint(path: str, shape: tuple[int, int]) -> np.ndarray:
    """Where an ink map has data (raw value > 0). Not read_map(...) > 0: the display stretch zeroes everything below 64."""
    if path.lower().endswith('.png'):
        a = cv2.imread(path, cv2.IMREAD_UNCHANGED)
        if a is None:
            raise IOError(path)
        a = (a[..., 0] if a.ndim == 3 else a) > 0
        return cv2.resize(a.astype(np.uint8), (shape[1], shape[0]), interpolation=cv2.INTER_NEAREST) > 0 if a.shape != tuple(shape) else a
    import tifffile
    return tifffile.imread(path) > 0


def valid_mask(surface: str, cache: str | None = None) -> np.ndarray:
    """Pixels whose CT is > 0 in every layer of the render (array "0" of a zarr group, shape (layers, H, W))."""
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


def masked_blur(E: np.ndarray, valid: np.ndarray, sigma_px: float) -> np.ndarray:
    """Gaussian mean of E over valid pixels, computed at a reduced scale (sigma is much larger than a pixel)."""
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


def strokes(E: np.ndarray, valid: np.ndarray, p: Params) -> tuple[np.ndarray, int, int]:
    """Boolean mask of stroke-sized components; returns (mask, components kept, components before the size filter)."""
    bg = masked_blur(E, valid, p.bg_mm * 1000 / p.um)
    m = ((E - bg) > p.thr) & valid
    n, lab, st, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8), connectivity=8)
    area = st[:, cv2.CC_STAT_AREA] * (p.um / 1000.) ** 2
    keep = (area >= p.amin_mm2) & (area <= p.amax_mm2)
    keep[0] = False
    return keep[lab], int(keep.sum()), n - 1


def tile_scores(S: np.ndarray, valid: np.ndarray, p: Params, tile_mm: float, min_frac: float):
    """Share of valid pixels covered by strokes in square tiles (clamped to the surface) on a `step_mm` grid."""
    t = max(8, int(round(tile_mm * 1000 / p.um)))
    step = max(4, int(round(p.step_mm * 1000 / p.um)))
    H, W = S.shape
    ty, tx = min(t, H), min(t, W)
    cs = lambda x: np.pad(x.astype(np.float64), ((1, 0), (1, 0))).cumsum(0).cumsum(1)
    I_s, I_v = cs(S & valid), cs(valid)
    ys = np.arange(0, H - ty + 1, step)
    xs = np.arange(0, W - tx + 1, step)
    box = lambda I: I[ys[:, None] + ty, xs[None, :] + tx] - I[ys[:, None], xs[None, :] + tx] \
        - I[ys[:, None] + ty, xs[None, :]] + I[ys[:, None], xs[None, :]]
    nv, ns = box(I_v), box(I_s)
    sc = np.where(nv >= min_frac * ty * tx, ns / np.maximum(nv, 1), np.nan)
    return sc, ys, xs, t


def summary(sc: np.ndarray) -> dict:
    v = sc[np.isfinite(sc)]
    if v.size == 0:
        return dict(n_tiles=0)
    return dict(n_tiles=int(v.size), max=float(v.max()), p99=float(np.percentile(v, 99)),
                p95=float(np.percentile(v, 95)), median=float(np.median(v)), mean=float(v.mean()))


def row_score(E: np.ndarray, valid: np.ndarray, p: Params) -> tuple[float, list | None]:
    """Row structure of one ensemble side: best window of max autocorrelation (line-spacing lags) x SD x 100 of the
    across-row density profile of pixels more than `thr` above the masked background (no size filter), at 1/row_ds scale.
    The profile is the median over `row_strips` strips along the window, so a line of writing, which runs across the whole
    window, counts and a lone bright blob (one strip) does not. Strip rows less than `row_min_cov` valid are left out; a
    profile row needs all strips but one, and a window `row_min_mm` of usable rows, so gaps in the mesh and bands shorter
    than the window do not disqualify it. A margin of `row_edge_mm` along the edge of the valid area is left out: ink
    models draw bright lines along mesh borders, and in a 1 cm band the two borders look like rows. Pass the render's
    valid area (`valid_mask`), not the ink maps' footprint, which spills past the mesh.
    Returns (score, [y, x] of the window's top-left corner in render pixels)."""
    ds = max(1, int(p.row_ds)); H, W = E.shape
    e = cv2.resize(np.where(valid, E, 0).astype(np.float32), (max(1, W // ds), max(1, H // ds)), interpolation=cv2.INTER_AREA)
    v = cv2.resize(valid.astype(np.float32), (max(1, W // ds), max(1, H // ds)), interpolation=cv2.INTER_AREA) > 0.99
    px = 1000.0 / p.um / ds; sig = p.bg_mm * px
    r = int(round(p.row_edge_mm * px))
    if r > 0:
        v = cv2.erode(v.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))) > 0
    num = cv2.GaussianBlur(np.where(v, e, 0), (0, 0), sig); den = cv2.GaussianBlur(v.astype(np.float32), (0, 0), sig) + 1e-6
    S = (np.where(v, e - num / den, 0) > p.thr) & v
    ww, wh = int(p.row_window_mm[0] * px), int(p.row_window_mm[1] * px)
    lags = np.arange(int(p.row_lag_mm[0] * px), int(p.row_lag_mm[1] * px) + 1)
    k = max(1, int(p.row_strips))
    best, where = 0.0, None
    for y0 in range(0, max(1, S.shape[0] - wh + 1), max(1, wh // 4)):
        for x0 in range(0, max(1, S.shape[1] - ww + 1), max(1, ww // 4)):
            Sw, vv = S[y0:y0 + wh, x0:x0 + ww], v[y0:y0 + wh, x0:x0 + ww]
            b = np.linspace(0, Sw.shape[1], k + 1).astype(int)
            n = np.stack([vv[:, a:c].sum(1) for a, c in zip(b[:-1], b[1:])]).astype(np.float64)
            dens = np.stack([Sw[:, a:c].sum(1) for a, c in zip(b[:-1], b[1:])]) / np.maximum(n, 1)
            ok = n >= p.row_min_cov * np.diff(b)[:, None]
            good = ok.sum(0) >= max(1, k - 1)
            if good.sum() < p.row_min_mm * px:
                continue
            prof = np.zeros(Sw.shape[0])
            prof[good] = np.nanmedian(np.where(ok, dens, np.nan)[:, good], axis=0)
            q = np.where(good, prof - prof[good].mean(), 0.0); d2 = float((q * q).sum())
            if d2 <= 0:
                continue
            ac = [float((q[:-L] * q[L:]).sum()) / d2 for L in lags if L < len(q)]
            if not ac:
                continue
            sc = max(max(ac), 0.0) * float(prof[good].std()) * 100
            if sc > best:
                best, where = sc, [int(y0 * ds), int(x0 * ds)]
    return float(best), where


def shape_score(E: np.ndarray, valid: np.ndarray, p: Params, at: list | None) -> dict:
    """Stroke shape in the row window at `at` ([y, x], render px): the share of the area of the above-background marks
    (pixels more than `thr` above the masked background, components of at least `shape_amin_mm2`) that lies in marks at
    least `shape_len_mm` long and `shape_elong` times as long as wide (ellipse axes from the second moments). Letter
    strokes are long and thin; the bright marks crack edges and damage give are mostly round blobs. The valid area loses
    `row_edge_mm` along its edge, as for the row score. Also reports `horiz`, the share of the long marks' area lying within
    30 degrees of the winding direction (render x): streaks along a crack edge are long but nearly all horizontal (PHerc0813
    false alarms 0.80-1.00; known text at most 0.61). Returns dict(score, marks, horiz); score None with too few marks."""
    if at is None:
        return dict(score=None, marks=0, horiz=None)
    px = 1000.0 / p.um
    y0, x0 = at; y1, x1 = y0 + int(p.row_window_mm[1] * px), x0 + int(p.row_window_mm[0] * px)
    r = int(round(p.row_edge_mm * px))
    v = valid if r <= 0 else cv2.erode(valid.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))) > 0
    D = E - masked_blur(E, v, p.bg_mm * px)
    m = ((D > p.thr) & v)[y0:y1, x0:x1]
    n, lab, st, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8), connectivity=8)
    area = st[:, cv2.CC_STAT_AREA].astype(np.float64)
    ys, xs = np.nonzero(lab); l = lab[ys, xs]
    m00 = np.maximum(np.bincount(l, minlength=n).astype(np.float64), 1)
    dx, dy = xs - (np.bincount(l, xs, n) / m00)[l], ys - (np.bincount(l, ys, n) / m00)[l]
    sxx, syy, sxy = np.bincount(l, dx * dx, n) / m00, np.bincount(l, dy * dy, n) / m00, np.bincount(l, dx * dy, n) / m00
    half, disc = (sxx + syy) / 2, np.sqrt(np.maximum(((sxx - syy) / 2) ** 2 + sxy ** 2, 0))
    length, width = 4 * np.sqrt(half + disc) / px, 4 * np.sqrt(np.maximum(half - disc, 0)) / px + 1 / px
    big = area * (p.um / 1000.) ** 2 >= p.shape_amin_mm2; big[0] = False
    if big.sum() < p.shape_min_marks:
        return dict(score=None, marks=int(big.sum()), horiz=None)
    stroke = big & (length >= p.shape_len_mm) & (length >= p.shape_elong * width)
    angle = np.abs(np.degrees(0.5 * np.arctan2(2 * sxy, sxx - syy)))
    horiz = float(area[stroke & (angle < 30)].sum() / area[stroke].sum()) if stroke.any() else None
    return dict(score=float(area[stroke].sum() / area[big].sum()), marks=int(big.sum()), horiz=horiz)


def along_profile(S: np.ndarray, use: np.ndarray, p: Params) -> list:
    """Stroke density along the winding (render x) in `profile_bins` equal bins of the segment length, smoothed over 2 mm."""
    col_s, col_u = (S & use).sum(0).astype(np.float64), use.sum(0).astype(np.float64)
    k = max(1, int(2.0 * 1000 / p.um)); ker = np.ones(k) / k
    cs, cu = np.convolve(col_s, ker, 'same'), np.convolve(col_u, ker, 'same')
    dens = np.where(cu > 0, cs / np.maximum(cu, 1e-9), np.nan)
    edges = np.linspace(0, len(dens), p.profile_bins + 1).astype(int)
    out = []
    for a, b in zip(edges[:-1], edges[1:]):
        seg = dens[a:max(b, a + 1)]; seg = seg[np.isfinite(seg)]
        out.append(round(float(seg.mean()), 5) if seg.size else None)
    return out


def usable_area(valid: np.ndarray, p: Params, ct: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray]:
    """Valid pixels minus the edge margin (and, if `void_frac` > 0, minus dark CT voids). Returns (use, void)."""
    # As in the original script, the void mask is always computed when the CT is given: with void_frac 0 it removes
    # pixels darker than the 1st percentile of the smoothed CT (about 1 %), widened by void_dilate_mm.
    void = np.zeros_like(valid)
    if ct is not None:
        c = cv2.GaussianBlur(ct.astype(np.float32), (0, 0), 2.0)
        lo, hi = np.percentile(c[valid], [1, 99.5])
        void = (c < lo + p.void_frac * (hi - lo)) & valid
        r = int(round(p.void_dilate_mm * 1000 / p.um))
        if r > 0:
            void = cv2.dilate(void.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))) > 0
    n, lab, cst, _ = cv2.connectedComponentsWithStats((~valid).astype(np.uint8), connectivity=8)
    small = cst[:, cv2.CC_STAT_AREA] * (p.um / 1000.) ** 2 < p.hole_mm2
    small[0] = False
    filled = valid | small[lab]
    r = int(round(p.edge_mm * 1000 / p.um))
    inner = cv2.erode(filled.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))) > 0 \
        if r > 0 else valid
    return inner & valid & ~void, void


def ensemble(maps: dict[str, tuple[str, str]], valid: np.ndarray) -> tuple[dict[str, np.ndarray], dict]:
    """maps: model -> (reading map path, blind map path). Returns {'reading': E, 'blind': E} and the per-model norms."""
    H, W = valid.shape
    E = {'reading': np.zeros((H, W), np.float32), 'blind': np.zeros((H, W), np.float32)}
    norm = {}
    for model in sorted(maps):
        pr, pb = maps[model]
        R = read_map(pr, (H, W))
        v = R[valid].astype(np.float64)
        mu, sd = float(v.mean()), float(v.std()) + 1e-6
        norm[model] = dict(mean=mu, sd=sd)
        E['reading'] += (R - mu) / sd
        E['blind'] += (read_map(pb, (H, W)) - mu) / sd
    for k in E:
        E[k] /= max(len(maps), 1)
    return E, norm


def score(E: dict[str, np.ndarray], valid: np.ndarray, use: np.ndarray, p: Params) -> tuple[dict, dict]:
    """Scores for both sides plus the top reading tiles. Returns (result dict, tile grids for figures)."""
    H, W = valid.shape
    sides, grids = {}, {}
    for label in ('reading', 'blind'):
        S, nk, nc = strokes(E[label], valid, p)
        S &= use
        sc, ys, xs, t = tile_scores(S, use, p, p.tile_mm, p.tile_min_frac)
        w2, _, _, _ = tile_scores(S, use, p, p.window_mm, p.window_min_frac)
        grids[label] = sc
        rs, rw = row_score(E[label], valid, p)
        sides[label] = dict(components_kept=nk, components_all=nc, stroke_frac=float(S[use].mean()) if use.any() else float('nan'),
                            tiles=summary(sc), window=summary(w2), row=dict(score=rs, at=rw), shape=shape_score(E[label], valid, p, rw),
                            profile=along_profile(S, use, p))
    sc = grids['reading']
    order = np.argsort(np.where(np.isfinite(sc), -sc, np.inf), axis=None)
    top = []
    for k in order:
        if len(top) >= p.top or not np.isfinite(sc.flat[k]):
            break
        i, j = np.unravel_index(k, sc.shape)
        y, x = int(ys[i]), int(xs[j])
        if any(abs(y - q['raw_y']) < t and abs(x - q['raw_x']) < t for q in top):
            continue
        vt, ut = valid[y:y + t, x:x + t], use[y:y + t, x:x + t]
        top.append(dict(score=float(sc[i, j]), blind=float(grids['blind'][i, j]), raw_y=y, raw_x=x,
                        damage=round(1 - float(ut.sum()) / max(float(vt.sum()), 1), 3),
                        read_y=H - y - t, read_x=W - x - t, size_px=t))
    rs, bs = sides['reading']['tiles'], sides['blind']['tiles']
    ratio = float(rs['max'] / bs['max']) if rs.get('max') and bs.get('max', 0) > 0 else None
    return dict(sides=sides, top_reading_tiles=top, ratio_max_reading_over_max_blind=ratio), grids


def write_outputs(stem: str, result: dict, grids: dict, E: dict, use: np.ndarray, valid: np.ndarray,
                  ct_layer=None, crops: int = 0, zrange=(-1.0, 4.0), png: bool = True) -> None:
    """<stem>.json, <stem>.png (reading tile scores | blind) and <stem>__topNN.png review crops (reading | blind | CT),
    all in reading orientation (rotated 180 degrees from the render)."""
    json.dump(result, open(stem + '.json', 'w'), indent=1)
    if png:
        hi = max(np.nanmax(grids['reading']) if np.isfinite(grids['reading']).any() else 0,
                 np.nanmax(grids['blind']) if np.isfinite(grids['blind']).any() else 0, 1e-6)
        ims = []
        for label in ('reading', 'blind'):
            g = grids[label][::-1, ::-1]
            b = np.where(np.isfinite(g), np.clip(g / hi, 0, 1) * 255, 0).astype(np.uint8)
            ims.append(cv2.resize(b, (b.shape[1] * 4, b.shape[0] * 4), interpolation=cv2.INTER_NEAREST))
        cv2.imwrite(stem + '.png', np.concatenate([ims[0], np.full((ims[0].shape[0], 8), 128, np.uint8), ims[1]], axis=1))
    H, W = valid.shape
    lo, hi = zrange
    for r, q in enumerate(result['top_reading_tiles'][:crops], 1):
        y0, x0, t = q['raw_y'], q['raw_x'], q['size_px']
        ya, yb = max(0, y0 - t // 2), min(H, y0 + t + t // 2)
        xa, xb = max(0, x0 - t // 2), min(W, x0 + t + t // 2)
        pan = []
        for label in ('reading', 'blind'):
            c = np.clip((E[label][ya:yb, xa:xb] - lo) / (hi - lo), 0, 1) * 255
            c[~use[ya:yb, xa:xb]] *= 0.35
            pan.append(c.astype(np.uint8))
        if ct_layer is not None:
            ct = np.asarray(ct_layer[ya:yb, xa:xb]).astype(np.float32)
            v = ct[valid[ya:yb, xa:xb]]
            if v.size:
                p1, p99 = np.percentile(v, [1, 99.5])
                ct = np.clip((ct - p1) / max(p99 - p1, 1), 0, 1) * 255
            pan.append(ct.astype(np.uint8))
        pan = [np.ascontiguousarray(x[::-1, ::-1]) for x in pan]
        sep = np.full((pan[0].shape[0], 6), 128, np.uint8)
        parts = [pan[0]]
        for x in pan[1:]:
            parts += [sep, x]
        cv2.imwrite(f'{stem}__top{r:02d}.png', np.concatenate(parts, axis=1))


def run(surface: str, maps: dict[str, tuple[str, str]], out_dir: str, name: str, depth: int, p: Params,
        mid_layer: int = 33, tag: str = '', crops: int = 0, png: bool = True, zrange=(-1.0, 4.0)) -> dict:
    """Score one 66-layer render at one depth and write the outputs. Returns the result dict."""
    import zarr
    t0 = time.time()
    os.makedirs(out_dir, exist_ok=True)
    valid = valid_mask(surface, os.path.join(out_dir, f'{name}__valid.png'))
    st = zarr.open_group(surface, mode='r')['0']
    ct = np.asarray(st[mid_layer + depth - 1:mid_layer + depth + 2]).astype(np.float32).mean(0)
    use, void = usable_area(valid, p, ct)
    E, norm = ensemble(maps, valid)
    res, grids = score(E, valid, use, p)
    cp1, cp99 = (float(x) for x in np.percentile(cv2.GaussianBlur(ct, (0, 0), 2.0)[valid], [1, 99.5]))
    result = dict(name=name, depth=depth, models=sorted(maps), um=p.um, H=int(valid.shape[0]), W=int(valid.shape[1]),
                  valid_px=int(valid.sum()), used_px=int(use.sum()), void_px=int(void.sum()), ct_p1=cp1, ct_p99_5=cp99,
                  params={k: v for k, v in asdict(p).items() if k not in ('um', 'top')}, norm=norm)
    result.update(res)
    result['seconds'] = round(time.time() - t0, 1)
    stem = os.path.join(out_dir, f'{name}__strokes{tag}_d{depth:+03d}')
    write_outputs(stem, result, grids, E, use, valid, ct_layer=st[mid_layer + depth] if crops else None,
                  crops=crops, zrange=zrange, png=png)
    return result
