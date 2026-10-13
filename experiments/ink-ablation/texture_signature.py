"""What does real 9.36 µm ink do to the CT texture? (2026-10-13, idea 2 step 1b; the ablations showed the models read fine
texture, about 75 µm, in the layers just above the surface, not brightness.) On a 66-layer control render with human
labels, per layer 33+d (d = -7..+9, the 17 layers the models see at d +1), five local texture measures compared on ink
and on bare papyrus inside the supervision mask (labels shifted as in deweave.py):
  sd75      local standard deviation in a 75 µm window (fine contrast)
  band1     energy of the 20-40 µm band (difference of Gaussians, smoothed over 0.2 mm)
  band2     energy of the 40-100 µm band
  coher     orientation coherence of the 2D structure tensor (1 = strongly oriented, like the weave's fibres)
  horiz     share of the gradient energy across the fibres along the winding (|g_y|^2 / |g|^2): how much the texture is
            horizontal stripes
  xcorr     correlation of this layer with the next one in 75 µm windows (does ink tie neighbouring layers together?)
For each: AUC (ink vs bare; 0.5 = no difference) and the ratio of the means. Then a logistic model on all measures x
layers, trained on the first control and scored on the second (and the other way round): if hand-made texture features
carry the signal, it should reach well above 0.5 on the segment it never saw.
Usage: texture_signature.py <out.txt> <render.zarr> <labels.zarr> <sup.zarr> <dy> <dx> [<render2> <labels2> <sup2> <dy2> <dx2>]"""
import sys
import cv2, numpy as np, zarr

UM = 9.366; D = range(-7, 10)


def load(rp, lp, sp, dy, dx):
    R = zarr.open(rp, mode='r')['0']; H, W = R.shape[1:]
    ct = np.asarray(R[33 + D[0]:33 + D[-1] + 2]).astype(np.float32); valid = (ct > 0).all(0)
    L = cv2.resize(np.asarray(zarr.open(lp, mode='r')['0']).astype(np.float32), (W, H), interpolation=cv2.INTER_AREA)
    L = np.roll(L / max(float(L.max()), 1e-6) > 0.5, (dy, dx), (0, 1))
    S = np.roll(cv2.resize(np.asarray(zarr.open(sp, mode='r')['0']).astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST) > 0, (dy, dx), (0, 1))
    pos, neg = L & S & valid, ~L & S & valid
    neg &= cv2.erode(neg.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
    return ct, pos, neg


def features(ct):
    """dict name -> (layers, H, W) float32"""
    w75 = max(3, int(round(75 / UM)) | 1); sm = lambda x, s: cv2.GaussianBlur(x, (0, 0), s)
    F = {k: [] for k in ('sd75', 'band1', 'band2', 'coher', 'horiz', 'xcorr')}
    for k in range(len(D)):
        c = ct[k]
        m = cv2.blur(c, (w75, w75)); F['sd75'].append(np.sqrt(np.maximum(cv2.blur(c * c, (w75, w75)) - m * m, 0)))
        g1, g2, g4 = sm(c, 20 / UM / 2), sm(c, 40 / UM / 2), sm(c, 100 / UM / 2)
        F['band1'].append(sm((g1 - g2) ** 2, 200 / UM)); F['band2'].append(sm((g2 - g4) ** 2, 200 / UM))
        gy = cv2.Sobel(sm(c, 1.0), cv2.CV_32F, 0, 1); gx = cv2.Sobel(sm(c, 1.0), cv2.CV_32F, 1, 0)
        jxx, jyy, jxy = sm(gx * gx, 6), sm(gy * gy, 6), sm(gx * gy, 6)
        tr = jxx + jyy + 1e-6; F['coher'].append(np.sqrt((jxx - jyy) ** 2 + 4 * jxy ** 2) / tr); F['horiz'].append(jyy / tr)
        n = ct[k + 1]; mn = cv2.blur(n, (w75, w75))
        cov = cv2.blur(c * n, (w75, w75)) - m * mn
        vn = np.maximum(cv2.blur(n * n, (w75, w75)) - mn * mn, 1e-6); vc = np.maximum(cv2.blur(c * c, (w75, w75)) - m * m, 1e-6)
        F['xcorr'].append(cov / np.sqrt(vc * vn))
    return {k: np.stack(v) for k, v in F.items()}


def auc(p, n):
    r = np.concatenate([p, n]).argsort().argsort().astype(np.float64)
    return float((r[:len(p)].sum() - len(p) * (len(p) - 1) / 2) / (len(p) * len(n)))


def samples(F, pos, neg, rng, k=60000):
    ip = rng.choice(np.flatnonzero(pos), min(int(pos.sum()), k), replace=False)
    im = rng.choice(np.flatnonzero(neg), min(int(neg.sum()), 2 * k), replace=False)
    X = np.concatenate([np.stack([F[f][l].ravel()[np.r_[ip, im]] for f in F for l in range(len(D))], 1)])
    y = np.r_[np.ones(len(ip)), np.zeros(len(im))]
    return X, y, ip, im


out = []; P = lambda *a: (out.append(' '.join(str(x) for x in a)), print(*a, flush=True))
a = sys.argv[1:]; outp = a[0]; segs = [a[1:6]] + ([a[6:11]] if len(a) >= 11 else [])
data = []
rng = np.random.default_rng(0)
for rp, lp, sp, dy, dx in segs:
    ct, pos, neg = load(rp, lp, sp, int(dy), int(dx)); F = features(ct)
    P(f'== {rp.split("/")[-1]}: ink px {int(pos.sum())}, bare px {int(neg.sum())}; AUC ink vs bare per layer (ratio of means)')
    P('d   ' + ''.join(f'{f:>16}' for f in F))
    Xs, ys, ip, im = samples(F, pos, neg, rng)
    for li, d in enumerate(D):
        row = f'{d:+3d} '
        for f in F:
            p, n = F[f][li].ravel()[ip], F[f][li].ravel()[im]
            row += f'{auc(p, n):9.3f} ({p.mean() / (n.mean() + 1e-9):4.2f})'
        P(row)
    data.append((Xs, ys))
if len(data) == 2:
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    for tr, te in ((0, 1), (1, 0)):
        sc = StandardScaler().fit(data[tr][0]); clf = LogisticRegression(max_iter=2000, C=0.1).fit(sc.transform(data[tr][0]), data[tr][1])
        s = clf.decision_function(sc.transform(data[te][0])); y = data[te][1]
        P(f'logistic on texture features, trained on segment {tr + 1}, scored on segment {te + 1}: AUC {auc(s[y == 1], s[y == 0]):.3f}')
open(outp, 'w').write('\n'.join(out) + '\n')
