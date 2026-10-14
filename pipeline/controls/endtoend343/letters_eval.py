"""Do known letters show in OUR read of OUR windings? (2026-10-13; end-to-end positive control)
For every read winding <results>/<fit>_<w>/maps/: the letter samples that lie on it (letters_on_windings.py rule) are put
on its render grid (20 px per node), grown into a letter area (discs of 30 px), and compared with the rest of the winding
(outside a 100 px margin): per model and depth, the mean ink inside the letters and outside on the reading side and on the
other face, and the reading-side AUC letters-vs-rest (a few random pixels per letter disc; 0.5 = no signal). Writes
<out>/eval.tsv and <out>/<w>_letters.jpg (reading side and other face of the two-model mean around the letters, letter
area outlined). Usage: letters_eval.py <letters3d.npz> <flattened root> <results root> <fit> <models,> <out dir>"""
import glob, os, sys
import cv2, numpy as np, tifffile
from scipy.spatial import cKDTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
L = np.load(sys.argv[1]); P = L['zyx'].astype(np.float64); ids = L['id']
froot, rroot, fit, models, out = sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5].split(','), sys.argv[6]
os.makedirs(out, exist_ok=True)


def place(d):
    X, Y, Z = (tifffile.imread(os.path.join(d, f'{c}.tif')).astype(np.float64) for c in 'xyz')
    G = np.stack([Z, Y, X], -1); ok = (X > 0) & (Y > 0) & (Z > 0)
    gy = np.gradient(G, axis=0); gx = np.gradient(G, axis=1); n = np.cross(gx, gy); n /= np.linalg.norm(n, axis=-1, keepdims=True) + 1e-9
    ok &= np.isfinite(n).all(-1); rc = np.argwhere(ok); V = G[ok]; N = n[ok]
    dist, j = cKDTree(V).query(P, distance_upper_bound=60); m = np.isfinite(dist); j = np.where(m, j, 0)
    off = P - V[j]; nn = np.abs((off * N[j]).sum(1)); ip = np.sqrt(np.maximum((off ** 2).sum(1) - nn ** 2, 0))
    hit = m & (nn <= 4) & (ip <= 15)
    return rc[j][hit] * 20, ids[hit]


def auc(a, b):
    r = np.argsort(np.argsort(np.concatenate([a, b]))); return (r[:len(a)].sum() - len(a) * (len(a) - 1) / 2) / (len(a) * len(b))


rng = np.random.default_rng(1); lines = ['winding\tmodel\tdepth\tletters_px\tread_in\tread_out\tblind_in\tblind_out\tAUC_read\tAUC_blind']
for rd in sorted(glob.glob(os.path.join(rroot, f'{fit}_w*'))):
    name = os.path.basename(rd); w = name[len(fit) + 1:]
    fl = os.path.join(froot, w, 'tifxyz', 'flatten.tifxyz')
    if not os.path.isdir(os.path.join(rd, 'maps')) or not os.path.isdir(fl):
        continue
    px, pid = place(fl)
    if len(px) == 0:
        continue
    ens = {}
    for m in models:
        for d in (0, 1):
            s = 25 + d; fr = f'{rd}/maps/{name}_66__{m}__L66s{s}_reverse.tif'; fb = f'{rd}/maps/{name}_66__{m}__L66s{s}.tif'
            if not (os.path.exists(fr) and os.path.exists(fb)):
                continue
            R = tifffile.imread(fr).astype(np.float32); B = tifffile.imread(fb).astype(np.float32)
            H, W = R.shape; valid = (R > 0) | (B > 0)
            Lm = np.zeros((H, W), np.uint8)
            for (y, x) in px:
                if 0 <= y < H and 0 <= x < W:
                    cv2.circle(Lm, (int(x), int(y)), 30, 1, -1)
            Lm = Lm.astype(bool) & valid
            far = ~cv2.dilate(Lm.astype(np.uint8), np.ones((201, 201), np.uint8)).astype(bool) & valid
            if Lm.sum() < 100 or far.sum() < 1000:
                continue
            ai = rng.choice(np.flatnonzero(Lm), min(20000, Lm.sum()), replace=False); ao = rng.choice(np.flatnonzero(far), min(200000, far.sum()), replace=False)
            Rf, Bf = R.ravel(), B.ravel()
            lines.append(f'{w}\t{m}\t{d}\t{int(Lm.sum())}\t{Rf[ai].mean():.1f}\t{Rf[ao].mean():.1f}\t{Bf[ai].mean():.1f}\t{Bf[ao].mean():.1f}\t'
                         f'{auc(Rf[ai], Rf[ao]):.3f}\t{auc(Bf[ai], Bf[ao]):.3f}')
            e = ens.setdefault(d, [np.zeros_like(R), np.zeros_like(B), 0, Lm]); e[0] += R; e[1] += B; e[2] += 1
    if 0 in ens:
        R, B, k, Lm = ens[0]; R /= k; B /= k
        ys, xs = np.nonzero(Lm); y0, y1, x0, x1 = max(ys.min() - 300, 0), ys.max() + 300, max(xs.min() - 300, 0), xs.max() + 300
        v = R[R > 0]; lo, hi = np.percentile(v, [1, 99.7]) if v.size else (0, 255)
        g = lambda A: cv2.cvtColor(np.clip((A[y0:y1, x0:x1] - lo) / max(hi - lo, 1) * 255, 0, 255).astype(np.uint8), cv2.COLOR_GRAY2BGR)
        cs, _ = cv2.findContours(Lm[y0:y1, x0:x1].astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        tiles = []
        for A, lab in ((R, 'reading side'), (B, 'other face')):
            t = g(A); o = t.copy(); cv2.drawContours(o, cs, -1, (0, 0, 0), 7); cv2.drawContours(o, cs, -1, (0, 255, 255), 3)
            for im, l2 in ((t, lab), (o, lab + ' + Nieuwlaar letters')):
                cv2.putText(im, f'{w} d0 {"+".join(models)}: {l2}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2); tiles.append(im)
        sep = np.zeros((tiles[0].shape[0], 16, 3), np.uint8)
        top = np.hstack([tiles[0], sep, tiles[2]]); bot = np.hstack([tiles[1], sep, tiles[3]])
        img = np.vstack([top, np.zeros((16, top.shape[1], 3), np.uint8), bot])
        sc = min(1.0, 3000 / img.shape[1]); img = cv2.resize(img, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA)
        cv2.imwrite(os.path.join(out, f'{w}_letters.jpg'), img, [cv2.IMWRITE_JPEG_QUALITY, 90])
open(os.path.join(out, 'eval.tsv'), 'w').write('\n'.join(lines) + '\n')
print('\n'.join(lines))
