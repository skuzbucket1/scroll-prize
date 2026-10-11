"""Row-structure score (see rowness.py): best 2 x 2.4 cm window of (max autocorrelation of the across-row stroke-density
profile at lags 3.5-8 mm) x (profile std) x 100, on the background-subtracted ensemble thresholded at 2.0."""
import numpy as np, cv2
def row_score(E, valid, um, ds=4):
    px = 1000.0 / um; H, W = E.shape
    e = cv2.resize(np.where(valid, E, 0).astype(np.float32), (W // ds, H // ds), interpolation=cv2.INTER_AREA)
    v = cv2.resize(valid.astype(np.float32), (W // ds, H // ds), interpolation=cv2.INTER_AREA) > 0.99
    p = px / ds; sig = 1.5 * p
    num = cv2.GaussianBlur(np.where(v, e, 0), (0, 0), sig); den = cv2.GaussianBlur(v.astype(np.float32), (0, 0), sig) + 1e-6
    S = (np.where(v, e - num / den, 0) > 2.0) & v
    ww, wh = int(20 * p), int(24 * p); lags = np.arange(int(3.5 * p), int(8 * p) + 1)
    best, where = 0.0, None
    for y0 in range(0, max(1, S.shape[0] - wh + 1), max(1, wh // 4)):
        for x0 in range(0, max(1, S.shape[1] - ww + 1), max(1, ww // 4)):
            vv = v[y0:y0 + wh, x0:x0 + ww]
            if vv.mean() < 0.7: continue
            prof = S[y0:y0 + wh, x0:x0 + ww].sum(1) / np.maximum(vv.sum(1), 1)
            q = prof - prof.mean(); den2 = (q * q).sum()
            if den2 <= 0: continue
            ac = np.array([(q[:-L] * q[L:]).sum() / den2 for L in lags if L < len(q)])
            if ac.size == 0: continue
            sc = max(float(ac.max()), 0.0) * float(prof.std()) * 100
            if sc > best: best, where = sc, [int(y0 * ds), int(x0 * ds)]
    return best, where
