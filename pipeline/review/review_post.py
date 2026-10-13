"""Review sheet for one winding scored by post_models.py: the whole winding (reading ensemble, blind ensemble with the
same stretch, CT layer 33+d) with the best row window marked, the window zoomed (reading | blind | CT), and the reading
side of the neighbouring windings w-2..w+2 with the same relative position marked (text does not repeat turn after
turn; sheet structure does). Works from the post JPEGs (half resolution, render orientation).
Usage: review_post.py <post dir of the scroll> <w> <depth> <out.jpg>"""
import json, os, re, sys
import cv2, numpy as np

post, w, d, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
WD = 1800


def load(name, side):
    f = os.path.join(post, name, f'{name}__{"ct" if side == "ct" else "ens_" + side}__d{d:+03d}.jpg')
    return cv2.imread(f, cv2.IMREAD_GRAYSCALE) if os.path.exists(f) else None


def label(im, text):
    c = np.zeros((im.shape[0] + 22, im.shape[1]), np.uint8); c[22:] = im
    cv2.putText(c, text, (6, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.55, 255, 1, cv2.LINE_AA); return c


def fit(im, width):
    return cv2.resize(im, (width, max(1, int(im.shape[0] * width / im.shape[1]))), interpolation=cv2.INTER_AREA)


j = json.load(open(os.path.join(post, w, f'{w}__post.json'))); r = j['depths'][str(d)]
y0, x0 = [v // 2 for v in (r.get('row_at') or [0, 0])]          # post JPEGs are half resolution
wh, ww = int(24 * 1000 / j['um'] / 2), int(20 * 1000 / j['um'] / 2)
rows = []
for side, tag in (('reading', 'READING'), ('blind', 'BLIND (same stretch)'), ('ct', f'CT layer {33 + d}')):
    im = load(w, side)
    if im is None:
        continue
    H, W = im.shape; s = WD / W; small = fit(im, WD)
    cv2.rectangle(small, (int(x0 * s), int(y0 * s)), (int(min(W, x0 + ww) * s), int(min(H, y0 + wh) * s)), 255, 2)
    rows.append(label(small, f'{w} d{d:+d} {tag}   row_R {r["row_R"]:.2f}  row_B {r["row_B"]:.2f}  area {r["area_R"]:.4f}/{r["area_B"]:.4f}'))
zoom = [load(w, s) for s in ('reading', 'blind', 'ct')]
zoom = [z[y0:y0 + wh, x0:x0 + ww] for z in zoom if z is not None]
if zoom:
    zh = min(z.shape[0] for z in zoom)
    gap = np.full((zh, 8), 128, np.uint8)
    strip = np.concatenate(sum([[z[:zh], gap] for z in zoom], [])[:-1], axis=1)
    rows.append(label(fit(strip, WD), 'row window zoom: reading | blind | CT  (render orientation; text reads rotated 180 deg)'))
k = int(re.search(r'(\d{3})', w).group(1)); rel = (x0 + ww / 2) / max(1, load(w, 'reading').shape[1])
for dw in (-2, -1, 1, 2):
    nb = re.sub(r'\d{3}', f'{k + dw:03d}', w, count=1); im = load(nb, 'reading')
    if im is None:
        continue
    small = fit(im, WD); cx = int(rel * WD); hw = int(ww / im.shape[1] * WD / 2)
    cv2.rectangle(small, (max(0, cx - hw), 0), (min(WD - 1, cx + hw), small.shape[0] - 1), 255, 2)
    nj = os.path.join(post, nb, f'{nb}__post.json'); nr = json.load(open(nj))['depths'].get(str(d), {}) if os.path.exists(nj) else {}
    rows.append(label(small, f'neighbour {nb} d{d:+d} READING (same relative position)   row_R {nr.get("row_R", float("nan")):.2f}'))
sheet = np.concatenate([np.pad(x, ((0, 6), (0, WD - x.shape[1])), constant_values=0) for x in rows], axis=0)
cv2.imwrite(out, sheet, [cv2.IMWRITE_JPEG_QUALITY, 85]); print(out, sheet.shape)
