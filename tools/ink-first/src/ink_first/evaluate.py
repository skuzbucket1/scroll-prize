"""Evaluation against known text: correlation and AUC on the covered pixels, a null from shifted references (a single far
shift is not a valid null: lines of text repeat, so use many shifts), coarse density-map correlation, and per-patch
statistics for comparing blocks with and without text."""
from __future__ import annotations

import numpy as np

from .mosaic import centre as patch_centre

SHIFTS = [(dy, dx) for dy in range(-480, 481, 120) for dx in range(-480, 481, 120) if max(abs(dy), abs(dx)) >= 240]


def auc(score: np.ndarray, positive: np.ndarray) -> float:
    s, p = np.asarray(score, float).ravel(), np.asarray(positive, bool).ravel()
    n1 = int(p.sum()); n0 = p.size - n1
    if n1 == 0 or n0 == 0:
        return float('nan')
    rk = np.argsort(np.argsort(s, kind='stable'), kind='stable') + 1.0
    return float((rk[p].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def shift_null(img: np.ndarray, ref: np.ndarray, mask: np.ndarray, shifts=SHIFTS) -> dict:
    """Correlation of img with ref on mask, against the same with ref shifted by many offsets (np.roll)."""
    a = np.nan_to_num(img)
    al = float(np.corrcoef(a[mask], ref[mask])[0, 1])
    nul = np.array([np.corrcoef(a[mask], np.roll(np.roll(ref, dy, 0), dx, 1)[mask])[0, 1] for dy, dx in shifts])
    return dict(r=al, null_mean=float(nul.mean()), null_sd=float(nul.std()), null_max=float(nul.max()),
                z=float((al - nul.mean()) / max(nul.std(), 1e-9)))


def best_alignment(img: np.ndarray, ref: np.ndarray, mask: np.ndarray, search: int = 16, step: int = 2) -> tuple:
    """The shift of ref (a few px: 2.4 um references vs 9 um meshes) that maximises the correlation with img."""
    a = np.nan_to_num(img)
    return max(((dy, dx) for dy in range(-search, search + 1, step) for dx in range(-search, search + 1, step)),
               key=lambda t: np.corrcoef(a[mask], np.roll(np.roll(ref, t[0], 0), t[1], 1)[mask])[0, 1])


def density_cells(img: np.ndarray, ref: np.ndarray, cov: np.ndarray, cell_px: int, min_cov: float = 0.5, seed: int = 0) -> dict:
    """Correlation of cell means (a coarse ink-density map) with a shuffled-cell null."""
    n_r, n_c = img.shape[0] // cell_px, img.shape[1] // cell_px; I, R = [], []
    for i in range(n_r):
        for j in range(n_c):
            sl = (slice(i * cell_px, (i + 1) * cell_px), slice(j * cell_px, (j + 1) * cell_px))
            if cov[sl].mean() < min_cov:
                continue
            I.append(np.nanmean(img[sl])); R.append(ref[sl][cov[sl]].mean())
    I, R = np.array(I), np.array(R); rng = np.random.default_rng(seed)
    if len(I) < 5:
        return dict(cells=len(I), r=float('nan'), null_sd=float('nan'))
    return dict(cells=len(I), r=float(np.corrcoef(I, R)[0, 1]), null_sd=float(np.std([np.corrcoef(I, rng.permutation(R))[0, 1] for _ in range(200)])))


def patch_stats(P, ink_map: np.ndarray, centre: int = 192) -> np.ndarray:
    """Per patch: mean, SD (contrast), 95th percentile, share above 0.5 and 0.8 of the raw map (no per-patch normalisation)."""
    S = int(P['size']); rows = []
    for rc in P['rowcol']:
        v = patch_centre(ink_map, rc, S, centre)
        rows.append((v.mean(), v.std(), np.percentile(v, 95), (v > 0.5).mean(), (v > 0.8).mean()))
    return np.array(rows, np.float32)


STAT_COLS = ('mean', 'sd', 'p95', 'frac50', 'frac80')
