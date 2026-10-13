"""Row-structure score of an ink-ensemble map: does the reading side show ROWS of stroke-like marks at line spacing?
Ensemble (mean of per-model z-scores, reading-side normalisation), background-subtracted (1.5 mm Gaussian), strokes =
pixels > thr. In sliding windows (W mm along the winding x H mm across), the across-row (y) profile of stroke density is
autocorrelated; score = max autocorrelation at lags 3.5-8 mm (Herculaneum line spacing ~4.5-6 mm) times the stroke density
contrast. Reported per side: best window score, and the reading/blind ratio of best scores.
Usage: rowness.py <maps dir> <name> <um> <models,comma> <d> [d...]"""
import sys, numpy as np, tifffile, cv2
mdir, name, um, models = sys.argv[1], sys.argv[2], float(sys.argv[3]), sys.argv[4].split(',')
px = 1000.0 / um                                     # px per mm
def load(m, d, side):
    s = 25 + d; return tifffile.imread(f'{mdir}/{name}__{m}__L66s{s}{"_reverse" if side=="reading" else ""}.tif').astype(np.float32)
def ens(d):
    out = {}
    rd = {m: load(m, d, 'reading') for m in models}; bl = {m: load(m, d, 'blind') for m in models}
    valid = np.logical_and.reduce([(rd[m] > 0) | (bl[m] > 0) for m in models])
    for side, src in (('reading', rd), ('blind', bl)):
        zs = []
        for m in models:
            v = rd[m][valid]; zs.append((src[m] - v.mean()) / (v.std() + 1e-6))
        out[side] = np.mean(zs, 0)
    return out, valid
def score_side(E, valid, ds=4):
    # downsample by ds for speed
    H, W = E.shape; e = cv2.resize(np.where(valid, E, 0).astype(np.float32), (W // ds, H // ds), interpolation=cv2.INTER_AREA)
    v = cv2.resize(valid.astype(np.float32), (W // ds, H // ds), interpolation=cv2.INTER_AREA) > 0.99
    p = px / ds; sig = 1.5 * p
    num = cv2.GaussianBlur(np.where(v, e, 0), (0, 0), sig); den = cv2.GaussianBlur(v.astype(np.float32), (0, 0), sig) + 1e-6
    hp = np.where(v, e - num / den, 0)
    S = (hp > 2.0) & v
    ww, wh = int(20 * p), int(24 * p)                  # window 2 cm along x, 2.4 cm across
    lags = np.arange(int(3.5 * p), int(8 * p) + 1)
    best = 0.0; where = None
    for y0 in range(0, max(1, S.shape[0] - wh + 1), max(1, wh // 4)):
        for x0 in range(0, max(1, S.shape[1] - ww + 1), max(1, ww // 4)):
            vv = v[y0:y0 + wh, x0:x0 + ww]
            if vv.mean() < 0.7: continue
            prof = S[y0:y0 + wh, x0:x0 + ww].sum(1) / np.maximum(vv.sum(1), 1)
            if prof.mean() <= 0: continue
            q = prof - prof.mean(); den2 = (q * q).sum()
            if den2 <= 0: continue
            ac = np.array([(q[:-L] * q[L:]).sum() / den2 for L in lags if L < len(q)])
            sc = max(float(ac.max()), 0.0) * float(prof.std()) * 100
            if sc > best: best, where = sc, (y0 * ds, x0 * ds)
    return best, where
for d in map(int, sys.argv[5:]):
    E, valid = ens(d)
    r, rw = score_side(E['reading'], valid); b, bw = score_side(E['blind'], valid)
    print(f'{name} d{d:+d} models={len(models)}  row_R {r:.3f} at {rw}  row_B {b:.3f}  ratio {r / (b + 1e-6):.2f}')
