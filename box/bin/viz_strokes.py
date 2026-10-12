"""'What stroke-score sees': one row window of a winding, in reading orientation. Left: the CT surface layer in grey with the
reading-side ink marks over it, long thin marks (letter-stroke shaped: >= 1 mm, >= 2x as long as wide) in orange and the
other marks (blobs) in blue. Middle: the same for the blind side. Right: the across-row stroke-density profile (median of
four strips), the signal the row score measures. Colours: Okabe-Ito orange #E69F00 / blue #0072B2 (colour-blind safe).
Usage: viz_strokes.py <surface.zarr> <maps dir> <name> <models,> <depth> <um> <out.png> [--at y0 x0] [--title T]"""
import argparse, os, sys
import cv2, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, 'stroke-score-src'))
from stroke_score.cli import nieuwlaar_paths
from stroke_score.core import Params, ensemble, masked_blur, row_score, valid_mask

ap = argparse.ArgumentParser()
for k in ('surface', 'maps', 'name', 'models'):
    ap.add_argument(k)
ap.add_argument('depth', type=int); ap.add_argument('um', type=float); ap.add_argument('out')
ap.add_argument('--at', type=int, nargs=2); ap.add_argument('--title', default='')
a = ap.parse_args()
import zarr
p = Params(um=a.um); valid = valid_mask(a.surface)
maps = {m: nieuwlaar_paths(a.maps, a.name, m, a.depth) for m in a.models.split(',')}
E, _ = ensemble(maps, valid)
at = list(a.at) if a.at else row_score(E['reading'], valid, p)[1]
px = 1000.0 / a.um; h, w = int(p.row_window_mm[1] * px), int(p.row_window_mm[0] * px)
y0, x0 = at; y1, x1 = min(valid.shape[0], y0 + h), min(valid.shape[1], x0 + w)
r = int(round(p.row_edge_mm * px))
v = cv2.erode(valid.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))) > 0
ct = np.asarray(zarr.open(a.surface, mode='r')['0'][33 + a.depth, y0:y1, x0:x1]).astype(np.float32)
vv = ct[ct > 0]; lo, hi = np.percentile(vv, [1, 99.5]) if vv.size else (0, 255)
grey = np.clip((ct - lo) / max(hi - lo, 1) * 255, 0, 255).astype(np.uint8)
ORANGE, BLUE = (0, 159, 230), (178, 114, 0)                                  # BGR of #E69F00, #0072B2


def panel(side):
    D = (E[side] - masked_blur(E[side], v, p.bg_mm * px))[y0:y1, x0:x1]
    m = (D > p.thr) & v[y0:y1, x0:x1]
    n, lab, st, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8), connectivity=8)
    img = cv2.cvtColor((grey * 0.55).astype(np.uint8), cv2.COLOR_GRAY2BGR)
    prof = np.zeros(y1 - y0)
    for k in range(1, n):
        area = st[k, cv2.CC_STAT_AREA] * (a.um / 1000) ** 2
        if area < p.shape_amin_mm2:
            continue
        ys, xs = np.nonzero(lab == k)
        cov = np.cov(np.stack([xs, ys])) if len(xs) > 2 else np.eye(2)
        ev = np.sort(np.linalg.eigvalsh(cov))[::-1]
        length, width = 4 * np.sqrt(ev[0]) / px, 4 * np.sqrt(max(ev[1], 0)) / px + 1 / px
        img[ys, xs] = ORANGE if (length >= p.shape_len_mm and length >= p.shape_elong * width) else BLUE
    b = np.linspace(0, x1 - x0, 5).astype(int)
    vs = v[y0:y1, x0:x1]
    dens = np.stack([m[:, a_:c_].sum(1) / np.maximum(vs[:, a_:c_].sum(1), 1) for a_, c_ in zip(b[:-1], b[1:])])
    prof = np.median(dens, 0)
    img[~vs] = (img[~vs] * 0.3).astype(np.uint8)
    return img[::-1, ::-1], prof[::-1]


R, pr = panel('reading'); B, pb = panel('blind')
rows = np.nonzero(v[y0:y1, x0:x1][::-1, ::-1].mean(1) > 0.05)[0]                 # crop to the band (reading orientation)
if rows.size:
    t0, t1 = max(0, rows[0] - 20), min(R.shape[0], rows[-1] + 20); R, B, pr, pb = R[t0:t1], B[t0:t1], pr[t0:t1], pb[t0:t1]
H = R.shape[0]
gap = np.full((H, 10, 3), 255, np.uint8)
pan = np.concatenate([R, gap, B], 1)
PW, CW = 1360, 230; scale = PW / pan.shape[1]; pan = cv2.resize(pan, (PW, int(H * scale)), interpolation=cv2.INTER_AREA)
Hs = pan.shape[0]; chart = np.full((Hs, CW, 3), 24, np.uint8); mx = max(pr.max(), pb.max(), 1e-6)
ys = np.linspace(0, H - 1, Hs).astype(int)
for y, k in enumerate(ys):
    cv2.line(chart, (10, y), (10 + int(pr[k] / mx * (CW - 20)), y), ORANGE, 1)
for y in range(Hs - 1):
    cv2.line(chart, (10 + int(pb[ys[y]] / mx * (CW - 20)), y), (10 + int(pb[ys[y + 1]] / mx * (CW - 20)), y + 1), (210, 210, 210), 2)
body = np.concatenate([pan, np.full((Hs, 10, 3), 255, np.uint8), chart], 1)
head = np.full((70, 1600, 3), 255, np.uint8)
cv2.putText(head, a.title, (8, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (30, 30, 30), 2, cv2.LINE_AA)
cv2.putText(head, 'reading side', (8, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (60, 60, 60), 1, cv2.LINE_AA)
cv2.putText(head, 'blind side (same sheet)', (int((R.shape[1] + 10) * scale) + 8, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (60, 60, 60), 1, cv2.LINE_AA)
cv2.putText(head, 'rows: reading', (PW + 18, 44), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 120, 190), 1, cv2.LINE_AA); cv2.putText(head, 'vs blind (grey)', (PW + 18, 62), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (90, 90, 90), 1, cv2.LINE_AA)
foot = np.full((40, 1600, 3), 255, np.uint8)
cv2.rectangle(foot, (8, 12), (28, 28), ORANGE, -1); cv2.putText(foot, 'long thin marks (stroke-shaped)', (36, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (40, 40, 40), 1, cv2.LINE_AA)
cv2.rectangle(foot, (330, 12), (350, 28), BLUE, -1); cv2.putText(foot, 'round marks (blobs)', (358, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (40, 40, 40), 1, cv2.LINE_AA)
sb = int(5000 / a.um * scale); cv2.line(foot, (PW - sb, 20), (PW, 20), (40, 40, 40), 3); cv2.putText(foot, '5 mm', (PW - sb, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (40, 40, 40), 1, cv2.LINE_AA)
cv2.imwrite(a.out, np.concatenate([head, body, foot], 0))
print(a.out, 'window', at)
