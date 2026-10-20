"""Rule-out filters for false marks (2026-10-17; dead end, see README.md). The rule-out "Venn diagram", steps 1-2.
Step 1 (features): for every mark of a brightmarks.py run (Reader v2 at d +1 for this; LAYER=26), the circles we can measure from the
maps and the CT render we hold, each a number per mark:
  other     the other face's contrast / the reading side's at the mark (low = one-sided)                       [lower = ink]
  agree     d9v4C's contrast at the mark (same depth, same 3 mm local mean; raw map units)                       [higher = ink]
  agree_n   the same / d9v4C's own 99.5th percentile contrast in that image (round 2: raw units do not carry across scrolls)
  vfib_lo / vfib_hi   share of the mark's coherent CT pixels whose fibres run within 20 deg of vertical, per CT face (layers
            d -6..-1 / d +1..+6); the recto rule: writing sits on the horizontal-fibre layer                        [lower = ink]
  along_lo / along_hi elongated marks only (long / short axis >= 2): share of the mark's coherent CT pixels whose fibre lies within 20
            deg of the mark's long axis (a fibre bundle follows the fibres)                                         [lower = ink]
  ct        CT at the surface under the mark, percentile of the image (dense debris gives false marks)            [lower = ink]
  edge      distance to the edge of the surface, mm (segment quality)           [higher = ink]
  layout    line grid: in a 20 (along y) x 12 mm window around the mark, the autocorrelation of the reading-side contrast's row
            profile (lines run along the render's x) at lags 2.5-7 mm, its maximum (writing comes in lines a few mm apart) [higher = ink]
            (round 1 used a 12 mm tall window, shorter than twice the longest lag: never computed - a bug, fixed in round 2)
  crackle   fine texture of the CT surface layers (d -2..+2; difference of Gaussians 0.8 / 2.5 px, absolute) inside the mark vs a
            1 mm ring around it (the carbon ink layer cracks into a fine network; Handmer 2023)                    [higher = ink]
Step 2 (calib): marks on known text whose centre lies on a label (labels widened by 0.2 mm for registration) are letter marks (round 1
counted label cover of the mark's bounding box >= 30 %: thin strokes leave most of a box empty, so real letter marks were missed): PHerc0841 w00 + ag2814 (held out
from every model: the yardstick) and PHerc. 343 (secondary: Reader v2 and d9v4C trained on 343). Every mark on the blank windings
(PHerc0813 z12000, PHerc0191 z11200: the triage nulls) is a blank hit. Per circle, the threshold is set on the 0841 letter marks alone
so that it keeps 90 % of them; the circle PASSES if, at that threshold, it removes >= 30 % of the blank hits (pass line written before
the run). Reported too: keep rate on 343 letters. The circles that pass are combined (all must hold). Set-off on the
neighbouring turn and the depth profile: venn_setoff.py, venn_depth.py.
Usage (villa venv): venn.py features <brightmarks out dir> <features.tsv>
                         venn.py calib <brightmarks out dir> <features.tsv> <labels.json> <out dir>
labels.json: {image name: {"labels": path, "sup": path, "roll": [dy, dx], "cls": "0841" | "343"}} (zarr or png masks, resized to the map)."""
import csv, json, os, sys
import cv2, numpy as np, tifffile, zarr

LO = 55; SL = int(os.environ.get('LAYER', 26))
FEAT = ['other', 'agree', 'agree_n', 'vfib_lo', 'vfib_hi', 'along_lo', 'along_hi', 'ct', 'edge', 'layout', 'crackle']
DIRN = dict(other=-1, agree=1, agree_n=1, vfib_lo=-1, vfib_hi=-1, along_lo=-1, along_hi=-1, ct=-1, edge=1, layout=1, crackle=1)


def contrast(a, v, k):
    s = cv2.GaussianBlur(a, (0, 0), 1.5); vf = v.astype(np.float32)
    return (s - cv2.blur(s * vf, (k, k)) / np.maximum(cv2.blur(vf, (k, k)), 1e-3)) * vf


def fibres(ct):
    gx, gy = cv2.Sobel(ct, cv2.CV_32F, 1, 0, ksize=3), cv2.Sobel(ct, cv2.CV_32F, 0, 1, ksize=3)
    jxx, jyy, jxy = [cv2.GaussianBlur(x, (0, 0), 3) for x in (gx * gx, gy * gy, gx * gy)]
    th = 0.5 * np.degrees(np.arctan2(2 * jxy, jxx - jyy)); coh = np.sqrt((jxx - jyy) ** 2 + 4 * jxy ** 2) / (jxx + jyy + 1e-6)
    return (th + 90) % 180, coh > 0.3                                   # fibre direction (across the dominant gradient), coherent


def adiff(a, b):
    d = np.abs(a - b) % 180; return np.minimum(d, 180 - d)


def features(bm, out):
    specs = json.load(open(f'{bm}/specs.json')); rows = list(csv.DictReader(open(f'{bm}/marks.tsv'), delimiter='\t'))
    by = {}
    for r in rows:
        by.setdefault(r['name'], []).append(r)
    cols = ['group', 'name', 'cy', 'cx', 'y0', 'x0', 'h', 'w', 'strength', 'sat_mm2', 'size_mm', 'elong', 'onesided'] + FEAT
    fo = open(out, 'w'); fo.write('\t'.join(cols) + '\n')
    for name, R_ in by.items():
        D, pre, render, mesh, um, group, rot = specs[name].split(':'); um = float(um); mm = um / 1000
        rd = tifffile.imread(f'{D}/{pre}__readerv2__L66s{SL}_reverse.tif').astype(np.float32); H, W = rd.shape
        f9 = f'{D}/{pre}__d9v4c__L66s{SL}_reverse.tif'; d9 = tifffile.imread(f9).astype(np.float32) if os.path.exists(f9) else None
        if d9 is not None and d9.shape != rd.shape:
            d9 = cv2.resize(d9, (W, H))
        v = rd > 0; ct = {}
        if render:
            z = zarr.open(render, mode='r')['0']
            for k, ks in (('lo', range(27, 33)), ('hi', range(34, 40)), ('surf', range(31, 36))):
                a = np.mean([np.asarray(z[i], np.float32) for i in ks], 0); ct[k] = a if a.shape == (H, W) else cv2.resize(a, (W, H))
            v &= ct['surf'] > 0
        v = cv2.erode(v.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0; k = int(3 / mm) | 1
        C = contrast(rd, v, k); Dc = contrast(d9, v, k) if d9 is not None else None
        d9s = float(np.percentile(Dc[v], 99.5)) if Dc is not None and v.any() else np.nan
        fib = {f: fibres(ct[f]) for f in ('lo', 'hi')} if ct else {}
        if ct:
            s = ct['surf']; E = np.abs(cv2.GaussianBlur(s, (0, 0), 0.8) - cv2.GaussianBlur(s, (0, 0), 2.5))
        ring_k = np.ones((int(2 / mm) | 1,) * 2, np.uint8); half, hy = int(6 / mm), int(10 / mm); lags = (int(2.5 / mm), int(7 / mm))
        for r in R_:
            y0, x0, h, w = (int(float(r[c])) for c in ('y0', 'x0', 'h', 'w')); cy, cx = int(float(r['cy'])), int(float(r['cx']))
            m = np.zeros((H, W), bool); m[y0:y0 + h, x0:x0 + w] = C[y0:y0 + h, x0:x0 + w] >= LO; m &= v
            if m.sum() < 5:
                continue
            f = dict(other=float(r['other_c']) / max(float(r['mean_c']), 1e-3), agree=float(Dc[m].mean()) if Dc is not None else np.nan,
                     agree_n=float(Dc[m].mean()) / max(d9s, 1e-3) if Dc is not None else np.nan,
                     ct=float(r['ct_pct']) if float(r['ct_pct']) >= 0 else np.nan, edge=float(r['edge_mm']))
            yy, xx = np.nonzero(m); ev, evec = np.linalg.eigh(np.cov(np.stack([xx, yy]))) if yy.size > 2 else (np.ones(2), np.eye(2))
            ax = np.degrees(np.arctan2(evec[1, 1], evec[0, 1])) % 180; el = float(np.sqrt(max(ev[1], 1e-6) / max(ev[0], 1e-6)))
            for face in ('lo', 'hi'):
                if face in fib:
                    th, coh = fib[face]; q = m & coh
                    f[f'vfib_{face}'] = float(np.mean(adiff(th[q], 90) <= 20)) if q.sum() >= 5 else np.nan
                    f[f'along_{face}'] = float(np.mean(adiff(th[q], ax) <= 20)) if (q.sum() >= 5 and el >= 2) else np.nan
                else:
                    f[f'vfib_{face}'] = f[f'along_{face}'] = np.nan
            ya, yb, xa, xb = max(cy - hy, 0), min(cy + hy, H), max(cx - half, 0), min(cx + half, W)
            win, wv = C[ya:yb, xa:xb], v[ya:yb, xa:xb]
            if wv.sum() > 0.4 * wv.size and (yb - ya) >= 2 * lags[1]:
                p = np.array([win[i][wv[i]].mean() if wv[i].sum() > 10 else 0 for i in range(win.shape[0])]); p = p - p.mean()
                ac = np.correlate(p, p, 'full')[p.size - 1:]; ac = ac / max(ac[0], 1e-6); f['layout'] = float(ac[lags[0]:lags[1]].max())
            else:
                f['layout'] = np.nan
            if ct:
                ring = (cv2.dilate(m.astype(np.uint8), ring_k) > 0) & ~m & v
                f['crackle'] = float(E[m].mean() / max(E[ring].mean(), 1e-6)) if ring.sum() > 20 else np.nan
            else:
                f['crackle'] = np.nan
            fo.write('\t'.join([r[c] for c in cols[:13]] + [f'{f[k]:.4f}' if np.isfinite(f[k]) else 'nan' for k in FEAT]) + '\n')
        fo.flush(); print(name, group, len(R_), 'marks', flush=True)
    print('VENN-FEATURES-DONE', flush=True)


def mask(spec, shape):
    def load(p):
        if p.endswith('.png'):
            return cv2.imread(p, 0).astype(np.float32)
        return np.squeeze(np.asarray(zarr.open(p, mode='r')['0'])).astype(np.float32)
    L, V = load(spec['labels']), load(spec['sup'])
    L = cv2.resize(L, shape[::-1], interpolation=cv2.INTER_AREA); V = cv2.resize(V, shape[::-1], interpolation=cv2.INTER_NEAREST) > 0
    L = L / max(L.max(), 1e-6) > 0.5
    dy, dx = spec.get('roll', [0, 0]); return np.roll(L, (dy, dx), (0, 1)), np.roll(V, (dy, dx), (0, 1))


def calib(bm, feat, labels, out):
    os.makedirs(out, exist_ok=True); rows = list(csv.DictReader(open(feat), delimiter='\t')); LJ = json.load(open(labels))
    specs = json.load(open(f'{bm}/specs.json'))
    for r in rows:
        r['cls'] = 'blank' if r['group'] == 'blank' else None
    for name, spec in LJ.items():                                       # letter marks on known text
        rs = [r for r in rows if r['name'] == name]
        if not rs:
            continue
        D, pre = specs[name].split(':')[:2]; L, V = mask(spec, tifffile.imread(f'{D}/{pre}__readerv2__L66s{SL}_reverse.tif').shape); pos = off = 0
        um = float(specs[name].split(':')[4]); g = int(0.2 / (um / 1000)) * 2 + 1
        Lw = cv2.dilate(L.astype(np.uint8), np.ones((g, g), np.uint8)) > 0
        for r in rs:
            cy, cx = int(float(r['cy'])), int(float(r['cx']))
            if not V[cy, cx]:
                continue
            if Lw[cy, cx]:
                r['cls'] = spec['cls']; pos += 1
            else:
                off += 1
        print(name, len(rs), 'marks,', pos, 'on the letters,', off, 'in the labelled area but off the letters', flush=True)
    val = lambda r, k: float(r.get(k) or 'nan')
    G = {c: [r for r in rows if r.get('cls') == c] for c in ('0841', '343', 'blank')}
    rep = [f"rule-out Venn, calibration (Reader v2 marks at d +1). marks: 0841 letters {len(G['0841'])}, 343 letters {len(G['343'])}, "
           f"blank hits {len(G['blank'])}", 'pass line: threshold keeps 90 % of the 0841 letter marks; '
           'PASS if it removes >= 30 % of the blank hits (a circle that cannot be measured on a mark keeps it)', '']
    rep.append(f"{'circle':10s} {'thresh':>8s} {'keep 0841':>9s} {'keep 343':>9s} {'remove blank':>12s}  n(0841/blank measured)  verdict")
    passed = {}
    for k in FEAT:
        d = DIRN[k]; p = np.array([val(r, k) for r in G['0841']]); p = p[np.isfinite(p)]
        if p.size < 8:
            rep.append(f'{k:10s} too few 0841 letter marks measured ({p.size})'); continue
        t = float(np.percentile(p, 10 if d > 0 else 90))
        keep = lambda r: (not np.isfinite(val(r, k))) or (val(r, k) >= t if d > 0 else val(r, k) <= t)
        kr = {c: (np.mean([keep(r) for r in G[c]]) if G[c] else np.nan) for c in G}
        nb = sum(np.isfinite(val(r, k)) for r in G['blank']); ok = (1 - kr['blank']) >= 0.30
        if ok:
            passed[k] = (t, d)
        rep.append(f"{k:10s} {t:8.3f} {kr['0841']:9.0%} {kr['343']:9.0%} {1 - kr['blank']:12.0%}  {p.size}/{nb}  "
                   f"{'PASS' if ok else 'fail'}")
    def keepall(r):
        return all((not np.isfinite(val(r, k))) or (val(r, k) >= t if d > 0 else val(r, k) <= t) for k, (t, d) in passed.items())
    rep += ['', f"combined (every passing circle must hold: {', '.join(passed) or 'none'}):"]
    for c in G:
        if G[c]:
            rep.append(f"  {c}: kept {np.mean([keepall(r) for r in G[c]]):.0%} of {len(G[c])}")
    open(f'{out}/report.txt', 'w').write('\n'.join(rep) + '\n'); print('\n'.join(rep))
    json.dump({k: dict(threshold=t, direction=d) for k, (t, d) in passed.items()}, open(f'{out}/passed.json', 'w'), indent=1)
    print('VENN-CALIB-DONE', flush=True)


if sys.argv[1] == 'features':
    features(sys.argv[2], sys.argv[3])
elif sys.argv[1] == 'calib':
    calib(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])
