"""Shared conventions and metrics for every analysis script (2026-10-15 audit, notes A2/A7/A11/A12/B3/B12).

One place for the things a script must not get slightly wrong on its own:
  - AUC with ties averaged (uint8 maps tie heavily; argsort ranks bias the result) and a letter-level bootstrap CI;
  - "valid" pixels from the CT render, not from the ink map (map > 0 drops quiet papyrus);
  - map file names: villa models <prefix>__<model>__L66s<25+d>[_reverse].tif, Hecate <prefix>__hecate__L66zc<32.5+d>[_reverse].png;
    render layer k samples (k - 32.5) voxels along the normal, depth d = k - 33; reading side = the _reverse maps;
    reading orientation = rotate 180°;
  - voxel size per scroll (never a default: PHerc0841 is 9.366 µm, PHerc0343 and PHerc0175A 8.64 µm);
  - mesh-to-mesh distance along the normal (nearest-node distance is biased by up to half a node spacing);
  - the sign of a mesh's normal against the scroll centre.
Scripts fail loudly: missing maps, unknown scrolls and empty masks raise instead of returning a number.
On the box this file is ~/scroll-prizes/bin/conventions.py; scripts run with python -I add that folder to sys.path.
Scrolls we don't publish yet are added from scrolls_private.json next to this file (not in git; same fields as SCROLLS).
Self-test: python3 conventions.py"""
import json, os, re

import numpy as np

# ---- scrolls ------------------------------------------------------------------------------------------------------
# volume = the eligible scan we read; voxel_um from its name; z_top_to_bottom / left_handed = what the spiral fit was
# told; reading_checked = side_check.py result (render +layer points away from the centre, mesh on the inner face).
SCROLLS = {
    'PHerc0343': dict(volume='20250521140437-8.640um-1.2m-116keV-masked.zarr', reading_checked='side_check 16/16 (2026-10-10)'),
    'PHerc0841': dict(volume='20250821151531-9.366um-1.2m-113keV-masked.zarr', reading_checked=None),
    'PHerc0139': dict(volume='20250728140407-9.362um-1.2m-113keV-masked.zarr', reading_checked=None),
    'PHerc0191': dict(volume='20250821151635-9.362um-1.2m-113keV-masked.zarr', reading_checked='side_check 60/60 w073 (2026-10-10)'),
    'PHerc0813': dict(volume='20250821151723-9.362um-1.2m-113keV-masked.zarr', reading_checked='side_check 60/60 w088 (2026-10-10)'),
    'PHerc0846A': dict(volume='20250728152254-9.362um-1.2m-113keV-masked.zarr', reading_checked=None),
    'PHerc0175A': dict(volume='20250521115057-8.640um-1.2m-116keV-masked.zarr', left_handed=False, z_top_to_bottom=True,
                       reading_checked=None),
}
_PRIVATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scrolls_private.json')
if os.path.exists(_PRIVATE):
    SCROLLS.update(json.load(open(_PRIVATE)))
BUCKET = 'https://vesuvius-challenge-open-data.s3.amazonaws.com'


def voxel_um_from_name(volume):
    m = re.search(r'-(\d+\.\d+)um-', os.path.basename(volume.rstrip('/')))
    if not m:
        raise ValueError(f'no voxel size in volume name {volume!r}')
    return float(m.group(1))


def voxel_um(scroll):
    """Voxel size of the scroll's eligible scan in µm (raises for a scroll not in SCROLLS)."""
    if scroll not in SCROLLS:
        raise KeyError(f'{scroll}: unknown scroll; add it to conventions.SCROLLS with its volume name')
    return voxel_um_from_name(SCROLLS[scroll]['volume'])


def volume_url(scroll):
    return f'{BUCKET}/{scroll}/volumes/{SCROLLS[scroll]["volume"]}'


# ---- renders and map names ----------------------------------------------------------------------------------------
N_LAYERS = 66
SURFACE_LAYER = 33          # d = k - 33; layer k samples (k - 32.5) voxels along the normal
VILLA_WINDOW0 = 25          # villa models read a 17-layer window starting at layer s = 25 + d
VILLA_MODELS = ('readerv2', 'd9v4c', 'dnative', 'hybrid_3d2d-seed42', 'hybrid_3d2d-seed43')
SIX_MODELS = VILLA_MODELS + ('hecate',)


def map_name(prefix, model, d, reverse):
    """File name of one ink map. reverse=True is the reading side."""
    sfx = '_reverse' if reverse else ''
    if model == 'hecate':
        return f'{prefix}__hecate__L66zc{SURFACE_LAYER - 0.5 + d:.2f}{sfx}.png'
    return f'{prefix}__{model}__L66s{VILLA_WINDOW0 + d}{sfx}.tif'


_NAME = re.compile(r'^(?P<prefix>.+?)__(?P<model>[^_]+(?:_[^_]+)*?)__L66(?:s(?P<s>-?\d+)|zc(?P<zc>-?\d+\.\d+))(?P<rev>_reverse)?\.(?:tif|png)$')


def parse_map_name(fname):
    """-> (prefix, model, d, reverse); raises on a name that does not follow map_name()."""
    m = _NAME.match(os.path.basename(fname))
    if not m:
        raise ValueError(f'not an ink-map name: {fname}')
    d = int(m['s']) - VILLA_WINDOW0 if m['s'] is not None else round(float(m['zc']) - (SURFACE_LAYER - 0.5))
    return m['prefix'], m['model'], d, m['rev'] is not None


def load_map(folder, prefix, model, d, reverse):
    """Ink map as float32 (raw values; see background()). Raises if the file is missing or empty."""
    f = os.path.join(folder, map_name(prefix, model, d, reverse))
    if not os.path.exists(f) or os.path.getsize(f) == 0:
        raise FileNotFoundError(f)
    if f.endswith('.png'):
        import cv2
        a = cv2.imread(f, cv2.IMREAD_UNCHANGED)
        if a is None:
            raise IOError(f'unreadable {f}')
    else:
        import tifffile
        a = tifffile.imread(f)
    return np.squeeze(a).astype(np.float32)


def background(a, valid):
    """The map's own baseline: median over valid pixels (villa maps sit near 64, Hecate near 0; audit B12).
    Compare or average models only after subtracting it."""
    v = a[valid]
    if v.size == 0:
        raise ValueError('empty valid mask')
    return float(np.median(v))


def to_display(a):
    """Reading orientation: rotate 180° (works for (H, W) and (H, W, C))."""
    return a[::-1, ::-1]


# ---- valid pixels from the CT -------------------------------------------------------------------------------------
def ct_valid(layers, lo=20, hi=46, erode_px=0):
    """Pixels where the render has CT in every layer lo..hi-1 (default d -13..+12); layers = (n, H, W) array or zarr.
    erode_px trims the edge where the models see padding."""
    a = np.asarray(layers[lo:hi])
    v = (a > 0).all(0)
    if erode_px:
        import cv2
        v = cv2.erode(v.astype(np.uint8), np.ones((2 * erode_px + 1, 2 * erode_px + 1), np.uint8)) > 0
    if not v.any():
        raise ValueError('no valid CT pixels')
    return v


def resize_mask(v, shape):
    import cv2
    return cv2.resize(v.astype(np.uint8), (shape[1], shape[0]), interpolation=cv2.INTER_NEAREST) > 0


# ---- AUC ----------------------------------------------------------------------------------------------------------
def auc(pos, neg):
    """P(score_pos > score_neg) + 0.5 P(equal): Mann-Whitney with average ranks for ties."""
    from scipy.stats import rankdata
    pos = np.asarray(pos, np.float64).ravel(); neg = np.asarray(neg, np.float64).ravel()
    if pos.size == 0 or neg.size == 0:
        raise ValueError(f'AUC needs both classes (pos {pos.size}, neg {neg.size})')
    r = rankdata(np.concatenate([pos, neg]), method='average')
    return float((r[:pos.size].sum() - pos.size * (pos.size + 1) / 2) / (pos.size * neg.size))


def auc_masked(score, pos_mask, valid, neg_mask=None):
    """AUC of score over valid pixels: pos_mask & valid against (neg_mask or ~pos_mask) & valid."""
    neg_mask = ~pos_mask if neg_mask is None else neg_mask
    return auc(score[pos_mask & valid], score[neg_mask & valid])


def _hist_auc(hp, hn):
    """AUC from two histograms over the same ascending bins (ties within a bin count one half)."""
    cn = np.cumsum(hn, -1) - hn
    return ((hp * (cn + 0.5 * hn)).sum(-1)) / (hp.sum(-1) * hn.sum(-1))


def auc_bootstrap(score, pos_mask, valid, neg_mask=None, n=1000, block=64, seed=0, bins=2048):
    """Point AUC and a 95 % interval that respects spatial correlation: letters (connected components of the positive
    mask) and negative blocks (block x block px) are resampled with replacement. -> (auc, lo, hi, n_letters, n_blocks).
    The interval uses the scores binned to <= bins levels (exact for uint8 maps); the point value is exact."""
    from scipy import ndimage
    neg_mask = ~pos_mask if neg_mask is None else neg_mask
    P, N = pos_mask & valid, neg_mask & valid
    point = auc(score[P], score[N])
    s = score[P | N]
    u = np.unique(s)
    edges = u if u.size <= bins else np.unique(np.quantile(s, np.linspace(0, 1, bins + 1)))
    q = lambda x: np.clip(np.searchsorted(edges, x, side='right') - 1, 0, len(edges) - 1)
    lab, k = ndimage.label(P)
    hp = np.zeros((k, len(edges))); np.add.at(hp, (lab[P] - 1, q(score[P])), 1)
    yy, xx = np.nonzero(N); nbx = score.shape[1] // block + 1; bid = (yy // block) * nbx + xx // block
    ub, bidx = np.unique(bid, return_inverse=True)
    hn = np.zeros((len(ub), len(edges))); np.add.at(hn, (bidx, q(score[N])), 1)
    rng = np.random.default_rng(seed)
    cp = np.stack([np.bincount(rng.integers(0, k, k), minlength=k) for _ in range(n)]).astype(np.float64)
    cn = np.stack([np.bincount(rng.integers(0, len(ub), len(ub)), minlength=len(ub)) for _ in range(n)]).astype(np.float64)
    a = _hist_auc(cp @ hp, cn @ hn)
    lo, hi = np.percentile(a, [2.5, 97.5])
    return point, float(lo), float(hi), int(k), int(len(ub))


# ---- meshes (tifxyz) ----------------------------------------------------------------------------------------------
def load_tifxyz(folder):
    """-> P (H, W, 3) as (z, y, x) voxels, ok (H, W) valid nodes. Node (i, j) = render pixel (20 i, 20 j) at scale 0.05."""
    import tifffile
    X, Y, Z = (tifffile.imread(os.path.join(folder, f'{c}.tif')).astype(np.float64) for c in 'xyz')
    ok = (X > 0) & (Y > 0) & (Z > 0) & np.isfinite(X) & np.isfinite(Y) & np.isfinite(Z)
    return np.stack([Z, Y, X], -1), ok


def grid_normals(P):
    """Unit normals of a (H, W, 3) node grid, n = dP/drow x dP/dcol (sign: see normal_sign)."""
    n = np.cross(np.gradient(P, axis=0), np.gradient(P, axis=1))
    return n / (np.linalg.norm(n, axis=-1, keepdims=True) + 1e-12)


def normal_offset(P_from, ok_from, P_to, ok_to, max_dist=40.0):
    """For each valid node of mesh A ('from'): distance to mesh B measured along B's normal at B's nearest node, plus the
    tangential residual. Nearest-node distance alone is biased by up to half a node spacing (~14 voxels at 20 px/node).
    -> dict(idx (m, 2) node indices in A, signed (m,) along B's normal, tangential (m,), node_spacing of B).
    Keep pairs with tangential < node_spacing to stay on B's footprint."""
    from scipy.spatial import cKDTree
    nB = grid_normals(P_to)
    B, nb = P_to[ok_to], nB[ok_to]
    d, nn = cKDTree(B).query(P_from[ok_from], distance_upper_bound=max_dist)
    f = np.isfinite(d)
    v = P_from[ok_from][f] - B[nn[f]]
    s = np.einsum('ij,ij->i', v, nb[nn[f]])
    t = np.linalg.norm(v - s[:, None] * nb[nn[f]], axis=1)
    step = np.nanmedian(np.linalg.norm(np.diff(P_to, axis=1), axis=-1)[ok_to[:, 1:] & ok_to[:, :-1]])
    return dict(idx=np.argwhere(ok_from)[f], signed=s, tangential=t, node_spacing=float(step))


def centre_at(umbilicus_json, z):
    """Scroll centre (y, x) at height z from an umbilicus.json (control_points with x, y, z)."""
    cps = sorted(json.load(open(umbilicus_json))['control_points'], key=lambda c: c['z'])
    zs = [c['z'] for c in cps]
    return np.interp(z, zs, [c['y'] for c in cps]), np.interp(z, zs, [c['x'] for c in cps])


def normal_sign(P, ok, umbilicus_json):
    """Share of valid nodes whose grid normal points away from the scroll axis (radially outward)."""
    n = grid_normals(P)[ok]; p = P[ok]
    cy, cx = centre_at(umbilicus_json, p[:, 0])
    r = np.stack([np.zeros_like(cy), p[:, 1] - cy, p[:, 2] - cx], 1)
    return float((np.einsum('ij,ij->i', n, r) > 0).mean())


# ---- self-test ----------------------------------------------------------------------------------------------------
def _selftest():
    from scipy.stats import mannwhitneyu
    rng = np.random.default_rng(3)
    a, b = rng.integers(60, 70, 4000), rng.integers(58, 68, 9000)          # heavy ties, like uint8 maps
    u = mannwhitneyu(a, b).statistic / (a.size * b.size)
    assert abs(auc(a, b) - u) < 1e-12, (auc(a, b), u)
    old = np.argsort(np.argsort(np.concatenate([a, b])))
    old = (old[:a.size].sum() - a.size * (a.size - 1) / 2) / (a.size * b.size)
    print(f'ties: average-rank AUC {auc(a, b):.4f}, old argsort AUC {old:.4f}')
    assert abs(_hist_auc(np.bincount(a - 58, minlength=12)[None].astype(float), np.bincount(b - 58, minlength=12)[None].astype(float))[0] - u) < 1e-12
    for m, d, r in (('readerv2', 0, True), ('d9v4c', -15, False), ('hybrid_3d2d-seed42', 7, True), ('hecate', -3, True), ('hecate', 15, False)):
        nm = map_name('exp30k-z12000_w088_66', m, d, r)
        assert parse_map_name(nm) == ('exp30k-z12000_w088_66', m, d, r), (nm, parse_map_name(nm))
    assert map_name('c0841_w00_66', 'hecate', -15, False) == 'c0841_w00_66__hecate__L66zc17.50.png'
    assert voxel_um('PHerc0841') == 9.366 and voxel_um('PHerc0343') == 8.64 and voxel_um('PHerc0175A') == 8.64
    img = rng.random((300, 300)); pos = np.zeros((300, 300), bool); pos[50:60, 40:200] = True; pos[150:160, 40:200] = True
    img[pos] += 0.3
    pt, lo, hi, k, nb = auc_bootstrap(img, pos, np.ones_like(pos), n=200, block=32)
    assert lo <= pt <= hi and k == 2, (pt, lo, hi, k)
    print(f'bootstrap: AUC {pt:.3f} [{lo:.3f}, {hi:.3f}] from {k} letters, {nb} blocks')
    print('conventions self-test OK')


if __name__ == '__main__':
    _selftest()
