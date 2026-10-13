"""Sheet view of ink-first clusters. A patch's centre is 1.1 mm across and a letter 2-4 mm, so no single patch can show
a letter; this lays the patches around a cluster that lie on the same sheet out flat, from their 64 px thumbnails, into
one picture of about a centimetre: CT surface layer | ink on this side | ink on the other side.
Same sheet: grown from a hot patch, neighbour by neighbour (centres within `step` mm), keeping a neighbour when its
centre lies within `plane` voxels of the current patch's tangent plane and its normal is within `angle` degrees (a
flipped normal is the other face of the sheet, or noise: left out, so the picture is never mirrored); each is placed at
its offset along the current patch's u (the scroll axis) and v (along the lines of text). Sheets are grown from every
hot patch within `radius` of the cluster (hottest first, each patch in one sheet); the picture shows the sheet holding
the most hot patches. One point is sampled per 96^3 cell, so where windings are closer than that a sheet has gaps. Rows run along u, columns along v, seen from the side the normal points to (out of the papyrus); the
picture can be upside down but is not mirrored when that side is the written one. Thumbnails are blended with a taper;
blue-grey = no patch there.
Writes <out>/<cluster>_<order>.jpg and <out>/sheets_<order>.tsv (patches on the sheet, area, hot share on each side).
Usage: inkfirst_cluster_view.py <results dir (*/summary.npz)> <clusters_<order>.tsv> <out dir> [--order fwd] [--top 12]
       [--radius 5] [--step 1.8] [--plane 14] [--angle 25] [--hot 0.5] [--model readerv2] [--um 8.64] [--label PHerc0175A]"""
import argparse, glob, os
import cv2, numpy as np
from scipy.spatial import cKDTree

ap = argparse.ArgumentParser()
ap.add_argument('res'); ap.add_argument('clusters'); ap.add_argument('out')
ap.add_argument('--order', default='fwd'); ap.add_argument('--top', type=int, default=12); ap.add_argument('--radius', type=float, default=5.0)
ap.add_argument('--step', type=float, default=1.8); ap.add_argument('--plane', type=float, default=14.0); ap.add_argument('--angle', type=float, default=25.0)
ap.add_argument('--hot', type=float, default=0.5); ap.add_argument('--model', default='readerv2'); ap.add_argument('--um', type=float, default=8.64)
ap.add_argument('--label', default='PHerc0175A')
a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
oth = {'fwd': 'rev', 'rev': 'fwd'}[a.order]; mm = a.um / 1000.0; R = a.radius / mm
lines = [l.rstrip('\n').split('\t') for l in open(a.clusters)]
CL = [dict(zip(lines[0], r)) for r in lines[1:]][:a.top]
cc = np.array([[float(c['z']), float(c['y']), float(c['x'])] for c in CL])
tc = cKDTree(cc)
P = {k: [] for k in ('c', 'n', 'u', 'v', 'ct', 'me', 'ot', 'fr', 'fo', 'air')}; blk = []
for f in sorted(glob.glob(os.path.join(a.res, '**', 'summary.npz'), recursive=True)):
    S = np.load(f); c = S['centre'].astype(np.float64)
    k = np.nonzero([len(x) > 0 for x in tc.query_ball_point(c, R + 64)])[0]
    if not len(k) or f'ink64_{a.model}_{a.order}' not in S.files:
        continue
    for key, val in (('c', c), ('n', S['normal']), ('u', S['u']), ('v', S['v']), ('ct', S['ct64']), ('me', S[f'ink64_{a.model}_{a.order}']),
                     ('ot', S[f'ink64_{a.model}_{oth}']), ('fr', S[f'stats_{a.model}_{a.order}'][:, 2]), ('fo', S[f'stats_{a.model}_{oth}'][:, 2]),
                     ('air', S['air'] if 'air' in S.files else np.zeros(len(c), np.float32))):
        P[key].append(val[k])
    blk += [os.path.basename(os.path.dirname(f))] * len(k)
P = {k: np.concatenate(v) for k, v in P.items()}
T = cKDTree(P['c']); cosmax = np.cos(np.radians(a.angle))
win = np.outer(np.hanning(66)[1:-1], np.hanning(66)[1:-1]).astype(np.float32)
NOPATCH = np.array([70, 52, 40], np.uint8)                                   # BGR blue-grey
px = 2.0                                                                     # voxels per picture pixel (thumbnail spacing)
bar = 1.0 / mm / px                                                          # 1 mm in pixels
rows = []
for ci, c in enumerate(CL):
    cand = np.array(T.query_ball_point(cc[ci], R)); cs = set(cand.tolist())
    def grow(seed, taken):
        pos = {seed: np.zeros(2)}; q = [seed]
        while q:
            p = q.pop(0); n, u, v = P['n'][p], P['u'][p], P['v'][p]
            for j in T.query_ball_point(P['c'][p], a.step / mm):
                if j in pos or j in taken or j not in cs:
                    continue
                dv = P['c'][j] - P['c'][p]
                if abs(dv @ n) > a.plane or P['n'][j] @ n < cosmax:
                    continue
                pos[j] = pos[p] + np.array([dv @ u, dv @ v]); q.append(j)
        return pos
    hot_in = cand[P['fr'][cand] >= a.hot]; hot_in = hot_in[np.argsort(-P['fr'][hot_in])]
    if not len(hot_in):
        hot_in = cand[np.argsort(-P['fr'][cand])][:1]
    taken, sheets = set(), []
    for s0 in hot_in:
        if int(s0) in taken:
            continue
        sh = grow(int(s0), taken); taken |= set(sh); sheets.append(sh)
    nh = [sum(P['fr'][j] >= a.hot for j in sh) for sh in sheets]
    pos = sheets[int(np.lexsort((-np.array([len(sh) for sh in sheets]), -np.array(nh)))[0])]
    ids = np.array(list(pos)); XY = np.array([pos[i] for i in ids])
    lo = XY.min(0) - 64; hi = XY.max(0) + 64
    H, W = int(np.ceil((hi[0] - lo[0]) / px)) + 4, int(np.ceil((hi[1] - lo[1]) / px)) + 4
    acc = np.zeros((3, H, W), np.float32); ws = np.zeros((H, W), np.float32)
    for i, (du, dv) in zip(ids, XY):
        r0, c0 = int(round((du - 63 - lo[0]) / px)), int(round((dv - 63 - lo[1]) / px))
        for k, img in enumerate((P['ct'][i], P['me'][i], P['ot'][i])):
            acc[k, r0:r0 + 64, c0:c0 + 64] += img.astype(np.float32) * win
        ws[r0:r0 + 64, c0:c0 + 64] += win
    cov = ws > 0.05 * ws.max(); img = acc / np.maximum(ws, 1e-6)
    lo_, hi_ = np.percentile(img[0][cov], [1, 99]) if cov.any() else (0, 255)
    ctv = np.clip((img[0] - lo_) / max(hi_ - lo_, 1) * 255, 0, 255).astype(np.uint8)
    panels = [cv2.cvtColor(ctv, cv2.COLOR_GRAY2BGR), cv2.applyColorMap(img[1].astype(np.uint8), cv2.COLORMAP_INFERNO),
              cv2.applyColorMap(img[2].astype(np.uint8), cv2.COLORMAP_INFERNO)]
    names = ['CT, surface layer', f'ink, {a.order} side', f'ink, {oth} side']
    for pnl, nm in zip(panels, names):
        pnl[~cov] = NOPATCH
        cv2.line(pnl, (10, H - 12), (10 + int(round(bar)), H - 12), (255, 255, 255), 2)
        cv2.putText(pnl, '1 mm', (10, H - 18), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(pnl, nm, (10, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)
    sep = np.full((H, 4, 3), 22, np.uint8)
    pic = np.concatenate([panels[0], sep, panels[1], sep, panels[2]], 1)
    hotm, hoto = P['fr'][ids] >= a.hot, P['fo'][ids] >= a.hot
    area = cov.sum() * (px * mm) ** 2
    head = np.full((26, pic.shape[1], 3), 22, np.uint8)
    cv2.putText(head, f"{a.label} {c['cluster']} ({a.order}): {c['patches']} hot patches; {len(ids)} patches on this sheet, {area:.0f} mm2; "
                f"hot on this side {hotm.mean():.0%}, other side {hoto.mean():.0%}; centre z{cc[ci][0]:.0f} y{cc[ci][1]:.0f} x{cc[ci][2]:.0f}",
                (8, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (230, 230, 230), 1, cv2.LINE_AA)
    cv2.imwrite(os.path.join(a.out, f"{c['cluster']}_{a.order}.jpg"), np.concatenate([head, pic], 0), [cv2.IMWRITE_JPEG_QUALITY, 90])
    rows.append((c['cluster'], int(c['patches']), len(ids), area, float(hotm.mean()), float(hoto.mean()), float(np.mean(P['air'][ids] > 0.3)),
                 *cc[ci], ','.join(sorted({blk[i] for i in ids})), len(sheets), int(hotm.sum()), len(hot_in)))
    print(f"{c['cluster']}: {len(ids)} patches on the sheet ({area:.0f} mm2), {int(hotm.sum())} of {len(hot_in)} nearby hot patches on it "
          f"({len(sheets)} sheets); hot {hotm.mean():.0%} this side / {hoto.mean():.0%} other")
with open(os.path.join(a.out, f'sheets_{a.order}.tsv'), 'w') as fo:
    fo.write('cluster\thot_patches\tsheet_patches\tarea_mm2\thot_this_side\thot_other_side\tdamaged\tz\ty\tx\tblocks\tsheets\thot_on_sheet\thot_nearby\n')
    for r in rows:
        fo.write(f'{r[0]}\t{r[1]}\t{r[2]}\t{r[3]:.1f}\t{r[4]:.3f}\t{r[5]:.3f}\t{r[6]:.2f}\t{r[7]:.0f}\t{r[8]:.0f}\t{r[9]:.0f}\t{r[10]}\t{r[11]}\t{r[12]}\t{r[13]}\n')
