"""Damage map v0 (2026-10-13; plan B in notes/plan-8um-model-and-damage-map.md, Ted's idea: map the cracks, holes and
folds, then search the cleaner papyrus). Do the ink models' false alarms sit on damage, and does real writing sit on
cleaner papyrus?

Per 1.5 mm tile of a 66-layer render (tiles with at least 60 % valid pixels):
  void     share of the tile in holes: the surface (mean of layers 31..35) darker than half the surface layer's median
           CT, at least 0.1 mm across and 0.05 mm2 (so the weave's thin dark gaps don't count). v1 asked for dark in 7 of
           the sheet's 9 layers 33-4..33+4 and missed the thin voids
  dark     the share of the sheet's voxels below half the median (holes and weave gaps alike)
  crack    share of pixels in thin dark lines at least 0.3 mm long: black-hat (0.1 mm radius, at half resolution) of
           the mean of layers 31..35, above the render's median + 4 robust SDs, holes left out
  edge_mm  distance from the tile centre to the nearest invalid pixel (mesh edge or hole), in mm
  wander   SD over the tile of the sheet's depth (centroid of the CT above half the median over layers 33-8..33+8), in
           layers: folds and layer crossings; offset = the tile's mean depth
  bright   the tile's median surface CT over the render's median: dense, compressed zones
and the ink the way stroke-score sees it (same valid mask, CT void mask, ensemble normalisation and stroke filter):
  area_R / area_B  share of the tile's usable area covered by strokes, reading / blind side; P_R / P_B mean ink probability.
Known text: `--labels labels.zarr --sup supervision.zarr` (human labels, PHerc. 0841): label = share of labelled ink in
tiles at least 80 % supervised, else -1; or `--boxes letter_boxes.json` (Nieuwlaar's PHerc. 343 letter boxes, not stroke
labels): label 1 for tiles at least half inside a box, else -1 (only two of the segment's lines are boxed).
Usage: damage_map.py tiles <render.zarr> <maps dir> <name> <um> <out.npz> [--models readerv2,d9v4c] [--depth 1]
                     [--labels L --sup S | --boxes B] [--png out.jpg]
       damage_map.py report <out prefix> <group>=<npz>[,<npz>...] ...   (groups named null:* are text-free)"""
import json, os, sys
import cv2, numpy as np, zarr
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'stroke-score-src'))
from stroke_score.cli import nieuwlaar_paths
from stroke_score.core import Params, fill_specks, map_footprint, read_map, strokes, usable_area

TILE_MM, MID, TEXT = 1.5, 33, 0.05
# damage measures, oriented so that larger = more damaged
DAMAGE = {'void': lambda Z: Z['void'], 'dark': lambda Z: Z['dark'], 'crack': lambda Z: Z['crack'],
          'near edge': lambda Z: -Z['edge_mm'], 'wander': lambda Z: Z['wander'], '|offset|': lambda Z: np.abs(Z['offset']),
          'bright': lambda Z: Z['bright']}


def opt(args, k, d=None):
    if k in args:
        i = args.index(k); v = args[i + 1]; del args[i:i + 2]; return v
    return d


def tiles(args):
    models = opt(args, '--models', 'readerv2,d9v4c').split(','); d = int(opt(args, '--depth', '1'))
    labp, supp, boxp, png = opt(args, '--labels'), opt(args, '--sup'), opt(args, '--boxes'), opt(args, '--png')
    render, mdir, name, um, out = args[0], args[1], args[2], float(args[3]), args[4]
    p = Params(um=um); st = zarr.open_group(render, mode='r')['0']; H, W = int(st.shape[1]), int(st.shape[2])
    P = {m: nieuwlaar_paths(mdir, name, m, d) for m in models}
    if not all(P.values()):
        sys.exit(f'{name}: missing maps for {[m for m in P if not P[m]]}')
    # one pass over the render: valid (CT > 0 in all 66 layers), the sheet layers 25..41, the 3 CT layers of the void mask
    v66 = np.zeros((H, W), bool); sheet = np.zeros((17, H, W), np.uint8); ct = np.zeros((H, W), np.float32)
    for r0 in range(0, H, 256):
        b = np.asarray(st[:, r0:r0 + 256])
        v66[r0:r0 + 256] = (b > 0).all(0); sheet[:, r0:r0 + 256] = b[MID - 8:MID + 9]
        ct[r0:r0 + 256] = b[MID + d - 1:MID + d + 2].astype(np.float32).mean(0)
    fp = np.ones((H, W), bool)
    for pr, pb in P.values():
        fp &= map_footprint(pr, (H, W)) | map_footprint(pb, (H, W))
    valid = fp & fill_specks(v66); del v66
    med = float(np.median(sheet[8][valid]))
    dark = np.zeros((H, W), np.float32)
    for i in range(4, 13):
        dark += sheet[i] < 0.5 * med
    dark /= 9
    # holes: a dark surface, at least 0.1 mm across (an opening drops the weave's thin dark gaps) and 0.05 mm2
    surf = sheet[6:11].astype(np.float32).mean(0)
    ro = max(1, int(round(50 / um))); so = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * ro + 1, 2 * ro + 1))
    voidpx = cv2.morphologyEx(((surf < 0.5 * med) & valid).astype(np.uint8), cv2.MORPH_OPEN, so)
    n, lab, cst, _ = cv2.connectedComponentsWithStats(voidpx, connectivity=8)
    big = cst[:, cv2.CC_STAT_AREA] * (um / 1000.) ** 2 >= 0.05; big[0] = False; voidpx = big[lab]
    # black-hat at half resolution (16x cheaper; cracks stay 1-3 px wide there)
    r = max(1, int(round(50 / um))); se = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))
    s2 = cv2.resize(cv2.GaussianBlur(surf, (0, 0), 1.0), (W // 2, H // 2), interpolation=cv2.INTER_AREA)
    bh = cv2.resize(cv2.morphologyEx(s2, cv2.MORPH_BLACKHAT, se), (W, H), interpolation=cv2.INTER_LINEAR); del s2
    b = bh[valid & ~voidpx]; bmed = float(np.median(b)); bsd = 1.4826 * float(np.median(np.abs(b - bmed))) + 1e-6
    crack = ((bh > bmed + 4 * bsd) & valid & ~voidpx).astype(np.uint8); del bh, b
    n, lab, cst, _ = cv2.connectedComponentsWithStats(crack, connectivity=8)      # lines at least 0.3 mm long
    long_ = np.maximum(cst[:, cv2.CC_STAT_WIDTH], cst[:, cv2.CC_STAT_HEIGHT]) * um / 1000. >= 0.3; long_[0] = False
    crack = long_[lab]; del lab
    tot = np.zeros((H, W), np.float32); num = np.zeros((H, W), np.float32)
    for i in range(17):
        w = np.clip(sheet[i].astype(np.float32) - 0.5 * med, 0, None); tot += w; num += w * (i - 8)
    depth = num / (tot + 1e-3); del sheet, tot, num, w
    dist = cv2.distanceTransform(valid.astype(np.uint8), cv2.DIST_L2, 5) * um / 1000.
    # ink, as `stroke-score score` sees it
    use, _ = usable_area(valid, p, ct)
    E = {'R': np.zeros((H, W), np.float32), 'B': np.zeros((H, W), np.float32)}
    Pm = {'R': np.zeros((H, W), np.float32), 'B': np.zeros((H, W), np.float32)}
    for m, (pr, pb) in P.items():
        R, B = read_map(pr, (H, W)), read_map(pb, (H, W)); v = R[valid].astype(np.float64); mu, sd = v.mean(), v.std() + 1e-6
        E['R'] += (R - mu) / sd / len(P); E['B'] += (B - mu) / sd / len(P); Pm['R'] += R / len(P); Pm['B'] += B / len(P)
    S = {k: strokes(E[k], valid, p)[0] & use for k in E}
    L = sup = None
    if labp:
        L = cv2.resize(np.asarray(zarr.open(labp, mode='r')['0']).astype(np.float32), (W, H), interpolation=cv2.INTER_AREA)
        L = L / max(float(L.max()), 1e-6) > 0.5
        sup = cv2.resize(np.asarray(zarr.open(supp, mode='r')['0']).astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST) > 0 \
            if supp else np.ones((H, W), bool)
    elif boxp:
        L = np.zeros((H, W), bool)
        for l in json.load(open(boxp))['letters']:
            x0, y0, x1, y1 = (int(round(v)) for v in l['box']); L[max(0, y0):y1, max(0, x0):x1] = True
    t = int(round(TILE_MM * 1000 / um)); rows = []
    for y in range(0, H - t + 1, t):
        for x in range(0, W - t + 1, t):
            sl = (slice(y, y + t), slice(x, x + t)); v = valid[sl]
            if v.mean() < 0.6:
                continue
            u = use[sl]; nu = max(int(u.sum()), 1); dv = depth[sl][v]
            row = dict(y=y, x=x, valid=float(v.mean()), void=float(voidpx[sl][v].mean()), dark=float(dark[sl][v].mean()),
                       crack=float(crack[sl][v].mean()),
                       edge_mm=float(dist[y + t // 2, x + t // 2]), wander=float(dv.std()), offset=float(dv.mean()),
                       bright=float(np.median(surf[sl][v]) / med), use=float(u.mean()),
                       area_R=float(S['R'][sl].sum() / nu), area_B=float(S['B'][sl].sum() / nu),
                       P_R=float(Pm['R'][sl][v].mean()), P_B=float(Pm['B'][sl][v].mean()), label=-1.0)
            if sup is not None:
                s = sup[sl] & v
                if s.sum() >= 0.8 * v.sum():
                    row['label'] = float(L[sl][s].mean())
            elif L is not None and L[sl][v].mean() >= 0.5:
                row['label'] = 1.0
            rows.append(row)
    np.savez_compressed(out, **{k: np.array([q[k] for q in rows], np.float32) for k in rows[0]},
                        meta=json.dumps(dict(render=render, name=name, um=um, depth=d, models=models, tile_px=t, H=H, W=W)))
    md = lambda k: np.median([q[k] for q in rows])
    print(f'{name}: {len(rows)} tiles of {t} px; median void {md("void"):.3f}, crack {md("crack"):.3f}, wander {md("wander"):.2f}, '
          f'offset {md("offset"):+.2f} layers; text tiles {sum(q["label"] >= TEXT for q in rows)}', flush=True)
    if png:
        picture(png, surf, valid, voidpx, crack, rows, t, um, name, L)


def picture(path, surf, valid, voidpx, crack, rows, t, um, name, L=None):
    """Reading orientation (rotated 180 degrees): the surface CT with holes (red) and cracks (yellow); known letters or
    ink labels outlined in green; tiles in the render's top 5 % of reading-side stroke area that beat the blind side
    outlined in cyan."""
    lo, hi = np.percentile(surf[valid], [1, 99.5]); g = (np.clip((surf - lo) / (hi - lo), 0, 1) * 255).astype(np.uint8)
    c = cv2.cvtColor(g, cv2.COLOR_GRAY2BGR); c[~valid] = (30, 30, 30)
    for m, col in ((voidpx & valid, (40, 40, 230)), (crack, (0, 220, 255))):
        c[m] = (0.4 * c[m] + 0.6 * np.array(col)).astype(np.uint8)
    lw = max(2, t // 40)
    if L is not None:
        cnt, _ = cv2.findContours(L.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(c, cnt, -1, (60, 220, 60), lw)
    a = np.array([q['area_R'] for q in rows]); thr = max(float(np.percentile(a, 95)), 1e-6)
    for q in rows:
        if q['area_R'] >= thr and q['area_R'] > q['area_B']:
            cv2.rectangle(c, (q['x'], q['y']), (q['x'] + t - 1, q['y'] + t - 1), (255, 255, 0), lw)
    c = cv2.rotate(c, cv2.ROTATE_180)
    f = 4 if c.shape[1] > 6000 else 2
    c = cv2.resize(c, (c.shape[1] // f, c.shape[0] // f), interpolation=cv2.INTER_AREA)
    c = cv2.copyMakeBorder(c, 34, 0, 0, 0, cv2.BORDER_CONSTANT, value=(22, 22, 22))
    bar = int(round(5000 / um / f)); cv2.line(c, (12, c.shape[0] - 14), (12 + bar, c.shape[0] - 14), (255, 255, 255), 3)
    cv2.putText(c, f'{name}, reading orientation: holes red, cracks yellow, known text green, top 5 % reading-side '
                f'stroke tiles cyan; bar 5 mm', (12, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
    cv2.imwrite(path, c, [cv2.IMWRITE_JPEG_QUALITY, 88])


def auc(pos, neg):
    """P(a pos value > a neg value), ties counted half."""
    from scipy.stats import rankdata
    pos, neg = np.asarray(pos, float), np.asarray(neg, float)
    if len(pos) == 0 or len(neg) == 0:
        return float('nan')
    r = rankdata(np.concatenate([pos, neg]))
    return float((r[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))


def report(args):
    prefix = args[0]; G = {}
    for a in args[1:]:
        g, fs = a.split('=', 1); parts = [np.load(f) for f in fs.split(',')]
        G[g] = {k: np.concatenate([z[k] for z in parts]) for k in parts[0].files if k != 'meta'}
    nulls = [g for g in G if g.startswith('null:')]; known = [g for g in G if g not in nulls]
    NZ = {k: np.concatenate([G[n][k] for n in nulls]) for k in G[nulls[0]]}
    out = []; P = lambda *a: out.append(' '.join(str(x) for x in a))
    # hot = reading-side stroke area in the top 5 % of all null tiles, and above the blind side
    hot_thr = float(np.percentile(NZ['area_R'], 95))
    hot = lambda Z: (Z['area_R'] >= hot_thr) & (Z['area_R'] > Z['area_B'])
    P(f'hot tile: reading-side stroke area >= {hot_thr:.3f} (the top 5 % of {len(NZ["y"])} null tiles) and above the blind side')
    P('\n== damage by group (medians; void, crack = share of the tile; edge in mm; wander, offset in layers; bright = x median)')
    cols = ['void', 'dark', 'crack', 'edge_mm', 'wander', 'offset', 'bright']
    P('group'.ljust(36), 'tiles'.rjust(7), ' '.join(f.rjust(8) for f in cols), 'hot'.rjust(7))
    for g, Z in G.items():
        sets = [(g, np.ones(len(Z['y']), bool))] if g in nulls else \
            [(g + ' text tiles', Z['label'] >= TEXT), (g + ' bare tiles', Z['label'] == 0)]
        for nm, s in sets:
            if s.sum():
                P(nm[:36].ljust(36), str(int(s.sum())).rjust(7), ' '.join(f'{np.median(Z[f][s]):8.3f}' for f in cols),
                  f'{hot(Z)[s].mean():7.1%}')
    P('\n== Q1: on text-free windings, do the hot tiles sit on damage? AUC per damage measure, hot vs other tiles (0.5 = no)')
    for g, Z in [(g, G[g]) for g in nulls] + [('all nulls', NZ)]:
        h = hot(Z); P(g.ljust(20), f'{int(h.sum())} hot of {len(h)}:', ', '.join(f'{k} {auc(f(Z)[h], f(Z)[~h]):.2f}' for k, f in DAMAGE.items()))
    P('\n== Q2: among hot tiles, does damage tell false alarms (null tiles) from writing (text tiles)? AUC, null-hot vs text-hot')
    nh = hot(NZ)
    for g in known:
        Z = G[g]; th = hot(Z) & (Z['label'] >= TEXT)
        P(g.ljust(20), f'{int(th.sum())} hot text tiles vs {int(nh.sum())} hot null tiles:',
          ', '.join(f'{k} {auc(f(NZ)[nh], f(Z)[th]):.2f}' for k, f in DAMAGE.items()))
    P('\n== Q3: a simple clean-papyrus mask: void, crack and wander at most the null tiles\' 75th percentile, edge at least 1 mm')
    lim = {f: float(np.percentile(NZ[f], 75)) for f in ('void', 'crack', 'wander')}
    clean = lambda Z: (Z['void'] <= lim['void']) & (Z['crack'] <= lim['crack']) & (Z['wander'] <= lim['wander']) & (Z['edge_mm'] >= 1.0)
    P('limits:', ', '.join(f'{f} {v:.3f}' for f, v in lim.items()))
    cn = clean(NZ)
    P(f'nulls: {cn.mean():.0%} of tiles clean; hot: {nh.mean():.2%} of all tiles, {nh[cn].mean():.2%} of clean tiles; '
      f'{(nh & cn).sum() / max(nh.sum(), 1):.0%} of the hot tiles are clean')
    for g in known:
        Z = G[g]; tt = Z['label'] >= TEXT; th = hot(Z) & tt; c = clean(Z)
        P(f'{g}: {c[tt].mean():.0%} of text tiles clean; {int(th.sum())} of {int(tt.sum())} text tiles hot, '
          f'{(th & c).sum() / max(th.sum(), 1):.0%} of those clean; hot among clean text tiles {hot(Z)[tt & c].mean():.1%}, '
          f'among all text tiles {hot(Z)[tt].mean():.1%}')
    txt = '\n'.join(out); open(prefix + '.txt', 'w').write(txt + '\n'); print(txt)


if __name__ == '__main__':
    a = sys.argv[1:]
    {'tiles': tiles, 'report': report}[a[0]](a[1:])
