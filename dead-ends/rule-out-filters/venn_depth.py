"""Rule-out filters for false marks, round 3a (2026-10-18; dead end, see README.md; pass line written before the run).
Venn round 3a, the DEPTH circle: ink sits on the surface, so Reader v2's contrast at a real letter should peak with the slab at the
surface and fall off when it moves away; structure (fibres, cracks, lumps) persists through depth. Per mark of the Venn round 2 (d +1,
contrast >= 75): depth_peak = c(+1) - mean(c(-6), c(+6), c(+9)), c = Reader v2's mean contrast over the mark (3 mm local mean), each
depth on its own map. Higher = ink. Images: the three PHerc0841 sheets and 30 blank windings (Reader v2 maps at d -6 / +6 / +9),
PHerc. 343 (c343 crop, maps from 10-14: rows / cols 512 on in the control frame; in-sample). Letter marks: centre on a label widened
0.2 mm (as venn.py round 2). Threshold keeps 90 % of the 0841 letter marks; PASS if it removes >= 30 % of the blank hits.
Usage (villa venv): venn_depth.py <bm round 2 dir> <labels2.json> <venn3 dir> <out dir>"""
import csv, json, os, sys
import cv2, numpy as np, tifffile, zarr

bm, labels, V3, out = sys.argv[1:5]; os.makedirs(out, exist_ok=True); LO = 55
specs = json.load(open(f'{bm}/specs.json')); plan = json.load(open(f'{V3}/plan.json')); LJ = json.load(open(labels))
C343 = tuple(os.environ['C343'].split(':')) if os.environ.get('C343') else None   # '<maps dir>:<prefix>:<r0>:<c0>' (PHerc. 343 crop; optional)
if C343:
    C343 = (C343[0], C343[1], int(C343[2]), int(C343[3]))
rows = list(csv.DictReader(open(f'{bm}/marks.tsv'), delimiter='\t')); by = {}
for r in rows:
    if r['name'] in plan or r['name'] == 'c343':
        by.setdefault(r['name'], []).append(r)


def contrast(a, v, k):
    s = cv2.GaussianBlur(a, (0, 0), 1.5); vf = v.astype(np.float32)
    return (s - cv2.blur(s * vf, (k, k)) / np.maximum(cv2.blur(vf, (k, k)), 1e-3)) * vf


def lab_mask(spec, shape):
    ld = lambda p: cv2.imread(p, 0).astype(np.float32) if p.endswith('.png') else np.squeeze(np.asarray(zarr.open(p, mode='r')['0'])).astype(np.float32)
    L, Vs = ld(spec['labels']), ld(spec['sup'])
    L = cv2.resize(L, shape[::-1], interpolation=cv2.INTER_AREA); Vs = cv2.resize(Vs, shape[::-1], interpolation=cv2.INTER_NEAREST) > 0
    L = L / max(L.max(), 1e-6) > 0.5; dy, dx = spec.get('roll', [0, 0]); return np.roll(L, (dy, dx), (0, 1)), np.roll(Vs, (dy, dx), (0, 1))


res = []
for name, R_ in by.items():
    D, pre, render, mesh, um, group, rot = specs[name].split(':'); mm = float(um) / 1000; k = int(3 / mm) | 1
    if name == 'c343' and not C343:
        continue                                             # PHerc. 343 crop not given (env C343)
    if name == 'c343':
        md, mp, oy, ox = C343; get = lambda s: tifffile.imread(f'{md}/{mp}__readerv2__L66s{s}_reverse.tif').astype(np.float32)
    else:
        oy = ox = 0; p = plan[name]
        get = lambda s, p=p, D=D, pre=pre: tifffile.imread(f'{D}/{pre}__readerv2__L66s{s}_reverse.tif' if s == 26 else f"{p['out']}/{p['prefix']}__readerv2__L66s{s}_reverse.tif").astype(np.float32)
    try:
        M = {s: get(s) for s in (26, 19, 31, 34)}
    except FileNotFoundError as e:
        print('SKIP', name, e, flush=True); continue
    H, W = M[26].shape
    for s in M:
        if M[s].shape != (H, W):
            M[s] = cv2.resize(M[s], (W, H))
    v = np.all([M[s] > 0 for s in M], 0); v = cv2.erode(v.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    Cs = {s: contrast(M[s], v, k) for s in M}
    pos = None
    if name in LJ:                                                     # letter marks (0841: labels in the map's frame; 343: control frame)
        sh = tifffile.imread(f'{D}/{pre}__readerv2__L66s26_reverse.tif').shape; L, Vs = lab_mask(LJ[name], sh)
        g = int(0.2 / mm) * 2 + 1; Lw = cv2.dilate(L.astype(np.uint8), np.ones((g, g), np.uint8)) > 0; pos = (Lw, Vs)
    for r in R_:
        y0, x0, h, w = (int(float(r[c])) for c in ('y0', 'x0', 'h', 'w')); cy, cx = int(float(r['cy'])), int(float(r['cx']))
        cls = 'blank' if group == 'blank' else None
        if pos is not None:
            Lw, Vs = pos
            if not Vs[cy, cx]:
                continue
            cls = ('0841' if group == '0841' else '343') + (' letter' if Lw[cy, cx] else ' other')
        if cls is None:
            continue
        y0, x0, cy, cx = y0 - oy, x0 - ox, cy - oy, cx - ox
        if not (0 <= cy < H and 0 <= cx < W):
            continue
        m = np.zeros((H, W), bool); ys, xs = slice(max(y0, 0), min(y0 + h, H)), slice(max(x0, 0), min(x0 + w, W))
        m[ys, xs] = Cs[26][ys, xs] >= LO; m &= v
        if m.sum() < 5:
            continue
        c = {s: float(Cs[s][m].mean()) for s in Cs}
        res.append(dict(name=name, cls=cls, peak=c[26] - np.mean([c[19], c[31], c[34]]), **{f'c{s}': c[s] for s in c}))
    print(name, group, len(R_), 'marks', flush=True)
with open(f'{out}/depth.tsv', 'w') as fo:
    fo.write('name\tcls\tpeak\tc26\tc19\tc31\tc34\n')
    for r in res:
        fo.write(f"{r['name']}\t{r['cls']}\t{r['peak']:.2f}\t{r['c26']:.2f}\t{r['c19']:.2f}\t{r['c31']:.2f}\t{r['c34']:.2f}\n")
G = {c: np.array([r['peak'] for r in res if r['cls'] == c]) for c in ('0841 letter', '0841 other', '343 letter', '343 other', 'blank')}
rep = ['Venn round 3a, depth (Reader v2 contrast at d +1 minus the mean at d -6, +6, +9; higher = ink)',
       '; '.join(f'{c} {a.size} (median {np.median(a):.1f})' for c, a in G.items() if a.size)]
if G['0841 letter'].size >= 8:
    t = float(np.percentile(G['0841 letter'], 10)); keep = lambda a: float(np.mean(a >= t)) if a.size else np.nan; rem = 1 - keep(G['blank'])
    rep += [f'threshold (keeps 90 % of the 0841 letter marks): {t:.2f}',
            f"keep 0841 letters {keep(G['0841 letter']):.0%}, 0841 other {keep(G['0841 other']):.0%}, 343 letters {keep(G['343 letter']):.0%}; "
            f"remove blank hits {rem:.0%} -> {'PASS' if rem >= 0.30 else 'fail'} (pass line: >= 30 %)"]
else:
    rep.append(f"too few 0841 letter marks ({G['0841 letter'].size})")
open(f'{out}/report.txt', 'w').write('\n'.join(rep) + '\n'); print('\n'.join(rep)); print('DEPTH-DONE')
