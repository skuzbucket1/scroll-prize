"""Take the papyrus weave out of the CT, then look for ink (2026-10-13, idea 1; Ted: "yes to 1"). Today's tests showed the
ink is in the 8-9 µm CT (about 6 % brighter on strokes) but buried under the weave, which is what every render shows
most. The weave is regular: fibres along the winding (x) on the written face, across it (y) underneath, each coherent
over centimetres, while pen strokes are short (0.1-0.4 mm wide, 1-3 mm long). Two ways to remove it from the CT surface
image at the ink depth (mean of layers 33+d0..33+d1; d 0..+4 by default, where 343's ink signal sits):
  A  along-fibre median: subtract a running median along x (`--fibre-mm`, 4 mm), then along y, computed every 0.25 mm
     and interpolated; long fibres go, short marks stay.
  B  Fourier wedges: in 4.8 mm tiles (50 % overlap, Hann window), damp the spectrum within +-3 degrees of its two
     strongest orientations for wavelengths under 1 mm, then overlap-add.
Scores: AUC of each image (raw, A, B; Gaussian-smoothed at 0.05 mm) for ink against bare papyrus, both inside the known
text: PHerc. 343, strokes vs the papyrus between strokes inside Nieuwlaar's letter boxes (ct_ink_signature.py masks.npz;
the strokes were picked by the ink models, every value scored here is CT); PHerc0841, human ink labels vs unlabelled
papyrus inside the supervision mask (labels shifted by the best offset within +-14 px, found with the ink-model
ensemble as in control_eval.py). AUC above 0.5 = brighter on ink; the ensemble's AUC is printed for reference (0841 only).
Pictures (reading orientation): raw | A | B | ink-model ensemble, letters outlined.
Usage: deweave.py <render.zarr> <name> <um> <out dir> (--masks343 masks.npz | --labels L.zarr --sup S.zarr)
       [--maps dir] [--d0 0] [--d1 4] [--fibre-mm 4]"""
import argparse, glob, json, os
import cv2, numpy as np, tifffile, zarr
from numpy.lib.stride_tricks import sliding_window_view

ap = argparse.ArgumentParser()
for k in ('render', 'name'):
    ap.add_argument(k)
ap.add_argument('um', type=float); ap.add_argument('out'); ap.add_argument('--masks343'); ap.add_argument('--labels'); ap.add_argument('--sup')
ap.add_argument('--maps'); ap.add_argument('--d0', type=int, default=0); ap.add_argument('--d1', type=int, default=4)
ap.add_argument('--fibre-mm', type=float, default=4.0)
a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
R = zarr.open(a.render, mode='r')['0']; H, W = R.shape[1:]
layers = np.asarray(R[33 + a.d0:33 + a.d1 + 1]).astype(np.float32)
valid = (np.asarray(R[33 - 8:33 + 9]) > 0).all(0)
img = layers.mean(0); del layers
med = float(np.median(img[valid])); img[~valid] = med                    # flat fill so filters don't ring at edges


def along_median(x, L, step, axis):
    """Running median of length L along `axis`, sampled every `step` pixels and linearly interpolated back."""
    if axis == 0:
        return along_median(x.T, L, step, 1).T
    h, w = x.shape; L = min(L, w - (w % 2 == 0)); pad = L // 2
    xp = np.pad(x, ((0, 0), (pad, pad)), mode='reflect')
    centres = np.arange(0, w, step)
    m = np.empty((h, len(centres)), np.float32)
    for r0 in range(0, h, 256):                                            # rows in blocks: bounded memory
        v = sliding_window_view(xp[r0:r0 + 256], L, axis=1)[:, centres, :]
        m[r0:r0 + 256] = np.median(v, axis=-1)
    out = np.empty_like(x)
    xs = np.arange(w)
    for r in range(h):
        out[r] = np.interp(xs, centres, m[r])
    return out


def wedges(x, um, tile=512, half_deg=3.0, max_wl_mm=1.0):
    """Damp the two strongest spectral orientations of each tile (wavelengths under max_wl_mm), overlap-add."""
    h, w = x.shape; st = tile // 2
    win = np.outer(np.hanning(tile), np.hanning(tile)).astype(np.float32)
    ky, kx = np.meshgrid(np.fft.fftfreq(tile), np.fft.fftfreq(tile), indexing='ij')
    kr = np.hypot(kx, ky); ang = np.degrees(np.arctan2(ky, kx)) % 180.
    band = kr > um / (max_wl_mm * 1000.)
    xp = np.pad(x, ((st, st + tile), (st, st + tile)), mode='reflect')
    acc = np.zeros_like(xp); wsum = np.zeros_like(xp)
    for y in range(0, h + st, st):
        for xx in range(0, w + st, st):
            t = xp[y:y + tile, xx:xx + tile]; mu = t.mean()
            F = np.fft.fft2((t - mu) * win); P = np.abs(F) ** 2
            hist = np.bincount(np.round(ang[band]).astype(int) % 180, weights=P[band], minlength=180)
            hist = np.convolve(np.r_[hist[-3:], hist, hist[:3]], np.ones(5) / 5, 'same')[3:-3]
            p1 = int(np.argmax(hist)); d = np.abs((np.arange(180) - p1 + 90) % 180 - 90)
            p2 = int(np.argmax(np.where(d >= 20, hist, -1)))
            M = np.ones_like(P)
            for p in (p1, p2):
                dd = np.abs((ang - p + 90) % 180 - 90)
                M *= 1 - np.exp(-(dd / half_deg) ** 2) * band
            r = np.real(np.fft.ifft2(F * M)) + mu * win
            acc[y:y + tile, xx:xx + tile] += r * win; wsum[y:y + tile, xx:xx + tile] += win ** 2
    return (acc / np.maximum(wsum, 1e-3))[st:st + h, st:st + w]


step = max(4, int(round(250 / a.um))); Lf = int(round(a.fibre_mm * 1000 / a.um)) | 1
A1 = img - along_median(img, Lf, step, 1)
A = A1 - along_median(A1, Lf, step, 0)
B = wedges(img, a.um)
# references
ens = None
if a.maps:
    fs = sorted(glob.glob(os.path.join(a.maps, f'{a.name}__*__L66s{25 + 1}_reverse.tif')))
    if fs:
        ens = np.mean([np.clip((tifffile.imread(f).astype(np.float32) - 64) / 128, 0, 1) for f in fs], 0)
if a.masks343:
    z = np.load(a.masks343); pos, neg = z['stroke'] & valid, z['boxbg'] & valid; outline = z['stroke']
else:
    L = cv2.resize(np.asarray(zarr.open(a.labels, mode='r')['0']).astype(np.float32), (W, H), interpolation=cv2.INTER_AREA)
    L = L / max(float(L.max()), 1e-6) > 0.5
    S = cv2.resize(np.asarray(zarr.open(a.sup, mode='r')['0']).astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST) > 0
    if ens is not None:                                                    # label shift that best fits the ensemble
        best = (-2, 0, 0)
        for dy in range(-14, 15, 2):
            for dx in range(-14, 15, 2):
                Ls = np.roll(L, (dy, dx), (0, 1)); m = S & valid
                c = np.corrcoef(ens[m][::7], Ls[m][::7].astype(np.float32))[0, 1]
                best = max(best, (c, dy, dx))
        L = np.roll(L, best[1:], (0, 1)); S = np.roll(S, best[1:], (0, 1)); print('label shift', best[1:], f'r {best[0]:.3f}')
    pos, neg = L & S & valid, ~L & S & valid
    neg &= cv2.erode(neg.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0  # keep a small gap from labelled ink
    outline = L & S


def auc(score):
    rng = np.random.default_rng(0)
    p, n = score[pos], score[neg]
    p = rng.choice(p, min(len(p), 200000), replace=False); n = rng.choice(n, min(len(n), 400000), replace=False)
    r = np.concatenate([p, n]).argsort().argsort().astype(np.float64)
    return float((r[:len(p)].sum() - len(p) * (len(p) - 1) / 2) / (len(p) * len(n)))


sig = 50 / a.um; res = {'name': a.name, 'um': a.um, 'depths': [a.d0, a.d1], 'ink px': int(pos.sum()), 'bare px': int(neg.sum())}
for nm, X in (('raw CT', img), ('A: along-fibre median', A), ('B: Fourier wedges', B)):
    res[f'AUC {nm}'] = round(auc(cv2.GaussianBlur(X, (0, 0), sig)), 4)
if ens is not None:
    res['AUC ink-model ensemble (reference)'] = round(auc(ens), 4)
print(json.dumps(res)); json.dump(res, open(os.path.join(a.out, f'{a.name}_deweave.json'), 'w'), indent=1)
# picture: the known text, reading orientation
ys, xs = np.nonzero(pos | outline); pad = int(1500 / a.um)
y0, y1, x0, x1 = max(0, ys.min() - pad), min(H, ys.max() + pad), max(0, xs.min() - pad), min(W, xs.max() + pad)
cnt, _ = cv2.findContours(outline[y0:y1, x0:x1].astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
panels = []
for nm, X in (('raw CT', img), ('A: along-fibre median removed', A), ('B: Fourier wedges removed', B), ('ink models (reference)', ens)):
    if X is None:
        continue
    c = cv2.GaussianBlur(X, (0, 0), sig)[y0:y1, x0:x1] if nm != 'ink models (reference)' else X[y0:y1, x0:x1]
    v = valid[y0:y1, x0:x1]; lo, hi = np.percentile(c[v], [1, 99])
    g = (np.clip((c - lo) / (hi - lo + 1e-6), 0, 1) * 255).astype(np.uint8); g[~v] = 25
    g = cv2.cvtColor(g, cv2.COLOR_GRAY2BGR); cv2.drawContours(g, cnt, -1, (60, 200, 60), 2)
    g = cv2.rotate(g, cv2.ROTATE_180); f = max(1, g.shape[1] // 1600)
    g = cv2.resize(g, (g.shape[1] // f, g.shape[0] // f), interpolation=cv2.INTER_AREA)
    k = {'raw CT': 'AUC raw CT', 'A: along-fibre median removed': 'AUC A: along-fibre median',
         'B: Fourier wedges removed': 'AUC B: Fourier wedges', 'ink models (reference)': 'AUC ink-model ensemble (reference)'}[nm]
    lab = f'{a.name} d {a.d0:+d}..{a.d1:+d}: {nm}' + (f' (AUC {res[k]:.3f})' if k in res else '')
    g = cv2.copyMakeBorder(g, 30, 4, 4, 4, cv2.BORDER_CONSTANT, value=(22, 22, 22))
    cv2.putText(g, lab, (8, 21), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
    panels.append(g)
wmax = max(p.shape[1] for p in panels)
panels = [cv2.copyMakeBorder(p, 0, 0, 0, wmax - p.shape[1], cv2.BORDER_CONSTANT, value=(22, 22, 22)) for p in panels]
cv2.imwrite(os.path.join(a.out, f'{a.name}_deweave.jpg'), np.concatenate(panels, 0), [cv2.IMWRITE_JPEG_QUALITY, 90])
print('written', a.out)
