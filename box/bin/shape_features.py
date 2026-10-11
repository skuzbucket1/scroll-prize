"""Component shape features of the above-background marks of a mean-z ensemble, reading and blind side, for designing a
stroke-shape score: area (mm2), length and width (ellipse axes from second moments, mm), elongation (length / width),
peak and mean height above the local background (z), and edge contrast (mean inside minus mean in a 2-pixel ring outside).
Usage: shape_features.py <cases.json> <out.npz>
cases.json: [{"label": .., "maps": dir, "name": .., "models": "a,b", "depth": d, "um": 9.362, "render": zarr or null,
              "crop": [y0, y1, x0, x1] or null}, ...]"""
import json, os, sys
import cv2, numpy as np, tifffile
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, 'stroke-score-src'))
from stroke_score.core import Params, ensemble, masked_blur, valid_mask


def features(D, valid, um, thr):
    m = (D > thr) & valid
    n, lab, st, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8), connectivity=8)
    if n <= 1:
        return np.zeros((0, 8), np.float32)
    ys, xs = np.nonzero(lab); l = lab[ys, xs]; d = D[ys, xs].astype(np.float64)
    m00 = np.bincount(l, minlength=n).astype(np.float64); m00[0] = 1
    cx, cy = np.bincount(l, xs, n) / m00, np.bincount(l, ys, n) / m00
    dx, dy = xs - cx[l], ys - cy[l]
    sxx, syy, sxy = np.bincount(l, dx * dx, n) / m00, np.bincount(l, dy * dy, n) / m00, np.bincount(l, dx * dy, n) / m00
    tr, det = sxx + syy, sxx * syy - sxy ** 2
    disc = np.sqrt(np.maximum(tr * tr / 4 - det, 0))
    l1, l2 = tr / 2 + disc, np.maximum(tr / 2 - disc, 0)
    length, width = 4 * np.sqrt(l1) * um / 1000, 4 * np.sqrt(l2) * um / 1000 + um / 1000
    peak = np.full(n, -np.inf); np.maximum.at(peak, l, d)
    mean = np.bincount(l, d, n) / m00
    ring = (cv2.dilate(m.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0) & ~m & valid
    rl = cv2.dilate(lab.astype(np.float32), np.ones((5, 5), np.uint8)).astype(np.int64)[ring]
    rmean = np.bincount(rl, D[ring].astype(np.float64), n) / np.maximum(np.bincount(rl, minlength=n), 1)
    area = st[:, cv2.CC_STAT_AREA] * (um / 1000) ** 2
    f = np.stack([area, length, width, length / width, peak, mean, mean - rmean, st[:, cv2.CC_STAT_AREA]], 1)[1:]
    return f.astype(np.float32)


cases = json.load(open(sys.argv[1])); out = {}
for c in cases:
    um = c.get('um', 9.362); s = 25 + c['depth']; p = Params(um=um)
    paths = {m: (f"{c['maps']}/{c['name']}__{m}__L66s{s}_reverse.tif", f"{c['maps']}/{c['name']}__{m}__L66s{s}.tif") for m in c['models'].split(',')}
    valid = None
    for a, b in paths.values():
        v = (tifffile.imread(a) > 0) | (tifffile.imread(b) > 0); valid = v if valid is None else valid & v
    if c.get('render'):
        valid &= valid_mask(c['render'])
    r = int(round(0.5 * 1000 / um))
    valid = cv2.erode(valid.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))) > 0
    E, _ = ensemble(paths, valid)
    y0, y1, x0, x1 = c.get('crop') or [0, valid.shape[0], 0, valid.shape[1]]
    for side in ('reading', 'blind'):
        D = E[side] - masked_blur(E[side], valid, p.bg_mm * 1000 / um)
        f = features(D[y0:y1, x0:x1], valid[y0:y1, x0:x1], um, p.thr)
        out[f"{c['label']}|{side}"] = f
        big = f[f[:, 0] >= 0.05]
        print(f"{c['label']:34s} {side:7s} comps {len(f):5d} (>=0.05 mm2: {len(big):4d})  elong med {np.median(big[:, 3]) if len(big) else 0:.2f}  "
              f"peak med {np.median(big[:, 4]) if len(big) else 0:.2f}  contrast med {np.median(big[:, 6]) if len(big) else 0:.2f}  "
              f"valid px {int(valid[y0:y1, x0:x1].sum())}", flush=True)
np.savez_compressed(sys.argv[2], **out)
