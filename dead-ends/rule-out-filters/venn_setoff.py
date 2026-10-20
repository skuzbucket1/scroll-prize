"""Rule-out filters for false marks, round 3b (2026-10-18; dead end, see README.md; pass line written before the run).
Venn round 3b, the SET-OFF circle: in carbonised rolls ink can print onto the facing turn and layers stick to their neighbours
(sovrapposti / sottoposti), so a mark that repeats at the same place on the neighbouring turn is structure or an offset. Per mark: its
3D point (its mesh node), the nearest node of the neighbouring turns w-1 and w+1 of the same band (<= 40 voxels), and there the
strongest Reader v2 contrast (d +1, 3 mm local mean, 0.3 mm around the point) on either face; setoff = the largest of these
(lower = ink). Marks with no read neighbour within reach are not measured (kept).
Calibration: letter marks = marks of our own PHerc. 343 fit (exp30k-z9300 w047-w050, the end-to-end control: Reader v2 in-sample)
within 0.4 mm of a Nieuwlaar letter point (letters3d.npz, projected onto the winding's nearest node <= 15 voxels); blank hits = the
Venn round 2 marks on the blank windings (PHerc0813 z12000, PHerc0191 z11200) whose neighbours are read. Threshold keeps 90 % of the
343 letter marks; PASS if it removes >= 30 % of the blank hits. No held-out yardstick exists for this circle (0841 is single segments).
Usage (villa venv): venn_setoff.py <bm round 2 dir> <bm 343 dir> <out dir>"""
import csv, json, os, re, sys
import cv2, numpy as np, tifffile
from scipy.spatial import cKDTree

bm2, bm343, out = sys.argv[1:4]; os.makedirs(out, exist_ok=True)
D = os.environ.get('DATA', 'data'); E = f'{D}/PHerc0343/endtoend'          # DATA: the data folder holding PHerc0343/endtoend
BANDS = {'0813': (f'{D}/PHerc0813/ink/exp30k-z12000/maps', '{w}', f'{D}/PHerc0813/geometry/exp30k-z12000/flattened/{{w}}/tifxyz/flatten.tifxyz', 9.362),
         '0191': (f'{D}/PHerc0191/ink/exp30k-z11200/maps', '{w}', f'{D}/PHerc0191/geometry/exp30k-z11200/flattened/{{w}}/tifxyz/flatten.tifxyz', 9.362),
         '343': (f'{E}/results/exp30k-z9300_{{w}}/maps', 'exp30k-z9300_{w}_66', f'{E}/data/geometry/exp30k-z9300/flattened/{{w}}/tifxyz/flatten.tifxyz', 8.64)}
cache = {}


def winding(band, w):
    k = (band, w)
    if k in cache:
        return cache[k]
    mdir, pre, mesh, um = BANDS[band]; mdir, pre, mesh = mdir.format(w=w), pre.format(w=w), mesh.format(w=w)
    f = f'{mdir}/{pre}__readerv2__L66s26_reverse.tif'
    if not (os.path.exists(f) and os.path.exists(f'{mesh}/x.tif')):
        cache[k] = None; return None
    X, Y, Z = (tifffile.imread(f'{mesh}/{c}.tif').astype(np.float64) for c in 'xyz'); ok = (X > 0) & (Y > 0) & (Z > 0)
    P = np.stack([X, Y, Z], -1); idx = np.argwhere(ok)
    mm = um / 1000; k3 = int(3 / mm) | 1; C = []
    for rev in ('_reverse', ''):
        a = tifffile.imread(f'{mdir}/{pre}__readerv2__L66s26{rev}.tif').astype(np.float32); v = cv2.erode((a > 0).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
        s = cv2.GaussianBlur(a, (0, 0), 1.5); vf = v.astype(np.float32)
        C.append(cv2.dilate((s - cv2.blur(s * vf, (k3, k3)) / np.maximum(cv2.blur(vf, (k3, k3)), 1e-3)) * vf, np.ones((int(0.6 / mm) | 1,) * 2, np.uint8)))
    cache[k] = dict(P=P, ok=ok, tree=cKDTree(P[ok]), idx=idx, itree=cKDTree(idx), C=C); return cache[k]


def node_point(W, cy, cx):
    r, c = int(round(cy / 20)), int(round(cx / 20)); h, w = W['ok'].shape; r, c = min(max(r, 0), h - 1), min(max(c, 0), w - 1)
    if W['ok'][r, c]:
        return W['P'][r, c]
    d, j = W['itree'].query([r, c]); return W['P'][tuple(W['idx'][j])] if d <= 3 else None


def setoff(band, w, cy, cx):
    W = winding(band, w)
    if W is None:
        return np.nan
    p = node_point(W, cy, cx)
    if p is None:
        return np.nan
    n = int(w[1:]); best = np.nan
    for m in (n - 1, n + 1):
        N = winding(band, f'w{m:03d}')
        if N is None:
            continue
        d, j = N['tree'].query(p)
        if d > 40:
            continue
        r, c = N['idx'][j]; y, x = int(r * 20), int(c * 20)
        for Cf in N['C']:
            if 0 <= y < Cf.shape[0] and 0 <= x < Cf.shape[1]:
                best = np.nanmax([best, float(Cf[y, x])])
    return best


rows = []
for r in csv.DictReader(open(f'{bm2}/marks.tsv'), delimiter='\t'):          # blank hits
    m = re.match(r'^blank-exp30k-z(12000|11200)-(w\d+)$', r['name'])
    if m:
        rows.append(dict(cls='blank', band='0813' if m.group(1) == '12000' else '0191', w=m.group(2), cy=float(r['cy']), cx=float(r['cx'])))
L = np.load(f'{E}/letters3d.npz'); LP = L['zyx'][:, ::-1]                    # letter points, x y z
for r in csv.DictReader(open(f'{bm343}/marks.tsv'), delimiter='\t'):        # our 343 fit: letter marks
    w = r['name'].split('_')[-1]; rows.append(dict(cls='343?', band='343', w=w, cy=float(r['cy']), cx=float(r['cx'])))
lp = {}
for w in sorted({r['w'] for r in rows if r['band'] == '343'}):
    W = winding('343', w)
    if W is None:
        continue
    d, j = W['tree'].query(LP); near = d <= 15; rc = W['idx'][j[near]] * 20
    lp[w] = cKDTree(rc) if near.any() else None; print('343', w, 'letter points on it:', int(near.sum()), flush=True)
mm343 = 8.64 / 1000
for r in rows:
    if r['band'] == '343':
        t = lp.get(r['w'])
        r['cls'] = '343 letter' if t is not None and t.query([r['cy'], r['cx']])[0] * mm343 <= 0.4 else '343 other'
for i, r in enumerate(rows):
    r['setoff'] = setoff(r['band'], r['w'], r['cy'], r['cx'])
    if i % 200 == 0:
        print(i, len(rows), flush=True)
with open(f'{out}/setoff.tsv', 'w') as fo:
    fo.write('cls\tband\tw\tcy\tcx\tsetoff\n')
    for r in rows:
        fo.write(f"{r['cls']}\t{r['band']}\t{r['w']}\t{r['cy']:.1f}\t{r['cx']:.1f}\t{r['setoff']:.2f}\n")
G = {c: np.array([r['setoff'] for r in rows if r['cls'] == c]) for c in ('343 letter', '343 other', 'blank')}
pos = G['343 letter'][np.isfinite(G['343 letter'])]
rep = [f"Venn round 3b, set-off (Reader v2 d +1 contrast at the same 3D place on the neighbouring turns; lower = ink)",
       f"marks: 343 letter {G['343 letter'].size} (measured {pos.size}), 343 other {G['343 other'].size}, blank {G['blank'].size} "
       f"(measured {np.isfinite(G['blank']).sum()})"]
if pos.size >= 8:
    t = float(np.percentile(pos, 90)); keep = lambda a: np.mean([(not np.isfinite(x)) or x <= t for x in a]) if a.size else np.nan
    rem = 1 - keep(G['blank'])
    rep += [f"threshold (keeps 90 % of the measured 343 letter marks): {t:.1f}",
            f"keep 343 letters {keep(G['343 letter']):.0%}, keep 343 other marks {keep(G['343 other']):.0%}, remove blank hits {rem:.0%}  -> "
            f"{'PASS' if rem >= 0.30 else 'fail'} (pass line: >= 30 %)",
            f"medians: 343 letter {np.nanmedian(G['343 letter']):.1f}, 343 other {np.nanmedian(G['343 other']):.1f}, blank {np.nanmedian(G['blank']):.1f}"]
else:
    rep.append(f'too few measured 343 letter marks ({pos.size})')
open(f'{out}/report.txt', 'w').write('\n'.join(rep) + '\n'); print('\n'.join(rep)); print('SETOFF-DONE')
