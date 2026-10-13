"""Damage in 3D, projected onto the windings (2026-10-13, idea 3, second half). For every node of a winding's flattened
mesh (tifxyz, one node per 20 render pixels), walk the line along the mesh's OWN normal through the node (+-1.5 mm, one
sample per level-2 voxel; the normal is the cross product of the grid tangents, oriented away from the umbilicus) through
damage3d.py's fields and measure what lies BEHIND and IN FRONT of the sheet, not just on it:
  crack_col   share of the samples outside the node's own sheet (|t| > 0.11 mm) that are cross-sheet crack: dark, planar
              (P > 0.4) and with the gap's plane normal e1 at more than 60 degrees from the mesh normal (|e1 . n| < 0.5)
  dark_col    share that are dark (D; includes the normal air between windings)
  crack_run   the longest unbroken run of crack-or-dark samples along the line, in mm (a gap through several windings)
  disorder    mean (1 - planarity) over the material samples of the line: crushed, unlayered papyrus around the node
  P_own, A_own, dark_own   planarity, alignment of e1 with the mesh normal, and darkness within the node's own sheet
              (|t| <= 0.11 mm): A_own near 1 means the CT's layering agrees with the mesh
The first run used the radial direction from the umbilicus instead of the mesh normal; in this crushed scroll the two
differ a lot, so that run is superseded.
Then per 1.5 mm tile (8 x 8 nodes = 160 render px, the damage_map.py grid) the mean over the tile's nodes, joined with the
damage_map tiles (area_R, area_B: what the ink models see), so that the same questions can be asked: do the hot tiles and
the flagged false alarms sit where damage runs through the scroll in depth?
Pictures (--png): the winding's crack_col map in reading orientation with the hot tiles outlined, and for the strongest
hot tile a radial cross-section of the CT (3 x 3 mm, radial x z) with the cross-sheet cracks in red.
Usage: damage3d_project.py <fields.zarr> <umbilicus.json> <geometry dir> <tiles dir> <um> <out dir> <winding> [...]
       [--png] ; then: damage3d_project.py report <out dir> [--flags flags.tsv]"""
import json, os, sys
import cv2, numpy as np, tifffile, zarr

OWN_MM, REACH_MM, TILE_PX, NODE_PX = 0.11, 1.5, 160, 20


def load_fields(fp):
    g = zarr.open_group(fp, mode='r'); at = dict(g.attrs); S = 2 ** at['level']
    F = {k: np.asarray(g[k]) for k in ('P', 'D', 'CT', 'EZ', 'EY', 'EX')}
    return F, at, S


def project(args):
    png = '--png' in args
    if png:
        args.remove('--png')
    fp, umb, geo, tdir, um, out = args[0], args[1], args[2], args[3], float(args[4]), args[5]; wins = args[6:]
    os.makedirs(out, exist_ok=True); F, at, S = load_fields(fp); z0 = at['z0']; nz, NY, NX = F['P'].shape
    cp = sorted(json.load(open(umb))['control_points'], key=lambda c: c['z'])
    uz, ux, uy = (np.array([c[k] for c in cp]) for k in ('z', 'x', 'y'))
    vox_mm = um / 1000.; step = S                                            # one level-2 voxel per sample, in level-0 voxels
    T = np.arange(-REACH_MM / vox_mm, REACH_MM / vox_mm + 1, step); own = np.abs(T) * vox_mm <= OWN_MM
    for w in wins:
        tz = f'{geo}/flattened/{w}/tifxyz/flatten.tifxyz'
        X, Y, Z = (tifffile.imread(f'{tz}/{k}.tif').astype(np.float64) for k in ('x', 'y', 'z'))
        ok = (X > 0) & (Y > 0) & (Z > 0); ni, nj = X.shape
        rx, ry = X - np.interp(Z, uz, ux), Y - np.interp(Z, uz, uy); rn = np.hypot(rx, ry) + 1e-6; rx, ry = rx / rn, ry / rn
        # mesh normal: cross product of the grid tangents, oriented away from the umbilicus; nodes next to a hole are dropped
        Xi, Xj = np.gradient(X); Yi, Yj = np.gradient(Y); Zi, Zj = np.gradient(Z)
        nx, ny, nzc = Yi * Zj - Zi * Yj, Zi * Xj - Xi * Zj, Xi * Yj - Yi * Xj
        nn = np.sqrt(nx ** 2 + ny ** 2 + nzc ** 2) + 1e-9; nx, ny, nzc = nx / nn, ny / nn, nzc / nn
        flip = (nx * rx + ny * ry) < 0; nx, ny, nzc = np.where(flip, -nx, nx), np.where(flip, -ny, ny), np.where(flip, -nzc, nzc)
        ok &= cv2.erode(ok.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
        # sample positions (nodes, samples) -> level-2 indices
        px = (X[..., None] + T * nx[..., None]) / S; py = (Y[..., None] + T * ny[..., None]) / S; pz = (Z[..., None] + T * nzc[..., None]) / S - z0
        ix, iy, iz = (np.clip(np.round(p).astype(int), 0, n - 1) for p, n in ((px, NX), (py, NY), (pz, nz)))
        inside = (px >= 0) & (px < NX) & (py >= 0) & (py < NY) & (pz >= 0) & (pz < nz) & ok[..., None]
        D = (F['D'][iz, iy, ix] > 0) & inside; P = F['P'][iz, iy, ix] / 255.; CT = F['CT'][iz, iy, ix]
        e = [F[k][iz, iy, ix] / 127.5 - 1 for k in ('EZ', 'EY', 'EX')]
        align = np.abs(e[0] * nzc[..., None] + e[1] * ny[..., None] + e[2] * nx[..., None])
        C = D & (P > 0.4) & (align < 0.5)
        mat = inside & (CT > 0) & ~D
        col = inside & ~own; ncol = np.maximum(col.sum(-1), 1)
        crack_col = (C & col).sum(-1) / ncol; dark_col = (D & col).sum(-1) / ncol
        disorder = np.where(mat.sum(-1) > 0, ((1 - P) * mat).sum(-1) / np.maximum(mat.sum(-1), 1), np.nan)
        gap = (C | D) & col; run = np.zeros(gap.shape[:2]); cur = np.zeros(gap.shape[:2])
        for k in range(gap.shape[-1]):                                     # longest run of gap samples along the line
            cur = np.where(gap[..., k], cur + 1, 0); run = np.maximum(run, cur)
        crack_run = run * S * vox_mm
        nown = np.maximum((inside & own).sum(-1), 1)
        P_own = (P * (inside & own)).sum(-1) / nown; dark_own = (D & own).sum(-1) / nown
        A_own = (align * (inside & own & ~D)).sum(-1) / np.maximum((inside & own & ~D).sum(-1), 1)
        node = dict(crack_col=crack_col, dark_col=dark_col, crack_run=crack_run, disorder=disorder, P_own=P_own, A_own=A_own, dark_own=dark_own)
        # tiles: 8 x 8 nodes, aligned with damage_map's 160 px grid (node (i, j) sits at render pixel (20 i, 20 j))
        tn = TILE_PX // NODE_PX; rows = []
        tiles = np.load(f'{tdir}/n_0813_{w}.npz'); tk = {(int(y), int(x)): n for n, (y, x) in enumerate(zip(tiles['y'], tiles['x']))}
        for ti in range(ni // tn):
            for tj in range(nj // tn):
                sl = (slice(ti * tn, ti * tn + tn), slice(tj * tn, tj * tn + tn)); v = ok[sl]
                key = (ti * TILE_PX, tj * TILE_PX)
                if v.mean() < 0.5 or key not in tk:
                    continue
                r = dict(y=key[0], x=key[1], nodes=int(v.sum()))
                for k, a in node.items():
                    r[k] = float(np.nanmean(a[sl][v]))
                n = tk[key]
                for k in ('area_R', 'area_B', 'P_R', 'P_B', 'void', 'crack', 'edge_mm', 'wander'):
                    r[k] = float(tiles[k][n])
                rows.append(r)
        np.savez_compressed(f'{out}/{w}.npz', **{k: np.array([r[k] for r in rows], np.float32) for k in rows[0]},
                            meta=json.dumps(dict(winding=w, um=um, fields=fp, reach_mm=REACH_MM, own_mm=OWN_MM)))
        md = lambda k: np.nanmedian([r[k] for r in rows])
        print(f'{w}: {len(rows)} tiles; median crack_col {md("crack_col"):.3f}, dark_col {md("dark_col"):.3f}, crack_run {md("crack_run"):.2f} mm, '
              f'disorder {md("disorder"):.2f}, P_own {md("P_own"):.2f}, A_own {md("A_own"):.2f}', flush=True)
        if png:
            picture(out, w, node, ok, rows, F, at, S, X, Y, Z, (nx, ny, nzc), (Xi, Yi, Zi), um)


def picture(out, w, node, ok, rows, F, at, S, X, Y, Z, normal, rowdir, um):
    """crack_col over the winding (reading orientation; hot tiles cyan) and a cross-section along the mesh normal at the
    strongest hot tile."""
    a = np.array([r['area_R'] for r in rows]); b = np.array([r['area_B'] for r in rows]); thr = max(float(np.percentile(a, 95)), 1e-6)
    hot = [r for r, av, bv in zip(rows, a, b) if av >= thr and av > bv]
    cc = np.nan_to_num(node['crack_col']); cc[~ok] = 0
    img = cv2.resize((np.clip(cc / 0.3, 0, 1) * 255).astype(np.uint8), (cc.shape[1] * 4, cc.shape[0] * 4), interpolation=cv2.INTER_NEAREST)
    img = cv2.applyColorMap(img, cv2.COLORMAP_HOT); img[cv2.resize((~ok).astype(np.uint8), (img.shape[1], img.shape[0]), interpolation=cv2.INTER_NEAREST) > 0] = (30, 30, 30)
    f = 4 / NODE_PX                                                       # render px -> picture px
    for r in hot:
        cv2.rectangle(img, (int(r['x'] * f), int(r['y'] * f)), (int((r['x'] + TILE_PX) * f), int((r['y'] + TILE_PX) * f)), (255, 255, 0), 1)
    img = cv2.rotate(img, cv2.ROTATE_180)
    img = cv2.copyMakeBorder(img, 26, 0, 0, 0, cv2.BORDER_CONSTANT, value=(22, 22, 22))
    cv2.putText(img, f'{w}: cross-sheet crack share along the mesh normal (+-1.5 mm, own sheet excluded), 0..0.3; hot tiles cyan',
                (6, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
    cv2.imwrite(f'{out}/{w}_crack_col.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 88])
    if not hot:
        return
    # cross-section (mesh normal x the grid's row direction) through the centre of the strongest hot tile
    r = max(hot, key=lambda q: q['area_R']); i, j = (r['y'] + TILE_PX // 2) // NODE_PX, (r['x'] + TILE_PX // 2) // NODE_PX
    i, j = min(i, X.shape[0] - 1), min(j, X.shape[1] - 1)
    if not ok[i, j]:
        return
    nx, ny, nzc = (c[i, j] for c in normal); ux, uy, uzz = (c[i, j] for c in rowdir); un = np.sqrt(ux ** 2 + uy ** 2 + uzz ** 2) + 1e-9
    ux, uy, uzz = ux / un, uy / un, uzz / un
    half = int(1.5 / (um / 1000.) / S); t = np.arange(-half, half + 1) * S; v = np.arange(-half, half + 1) * S
    px = (X[i, j] + t[None, :] * nx + v[:, None] * ux) / S; py = (Y[i, j] + t[None, :] * ny + v[:, None] * uy) / S
    pz = (Z[i, j] + t[None, :] * nzc + v[:, None] * uzz) / S - at['z0']
    nz_, NY, NX = F['CT'].shape
    ix = np.clip(np.round(px).astype(int), 0, NX - 1); iy = np.clip(np.round(py).astype(int), 0, NY - 1); iz = np.clip(np.round(pz).astype(int), 0, nz_ - 1)
    ct = F['CT'][iz, iy, ix]; D = F['D'][iz, iy, ix] > 0; P = F['P'][iz, iy, ix] / 255.
    e = [F[k][iz, iy, ix] / 127.5 - 1 for k in ('EZ', 'EY', 'EX')]; cr = D & (P > 0.4) & (np.abs(e[0] * nzc + e[1] * ny + e[2] * nx) < 0.5)
    g = cv2.cvtColor(ct, cv2.COLOR_GRAY2BGR); g[cr] = (0.3 * g[cr] + 0.7 * np.array([40, 40, 230])).astype(np.uint8)
    g[:, half] = (0.5 * g[:, half] + 0.5 * np.array([255, 255, 0])).astype(np.uint8)   # the sheet's own position
    g = cv2.resize(g, (g.shape[1] * 6, g.shape[0] * 6), interpolation=cv2.INTER_NEAREST)
    g = cv2.copyMakeBorder(g, 26, 0, 0, 0, cv2.BORDER_CONSTANT, value=(22, 22, 22))
    cv2.putText(g, f'{w} hot tile y{r["y"]} x{r["x"]}: CT along the mesh normal (left = inwards) x along the winding, 3 x 3 mm; cyan = this sheet, red = cross-sheet crack',
                (6, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)
    cv2.imwrite(f'{out}/{w}_section.jpg', g, [cv2.IMWRITE_JPEG_QUALITY, 90])


def auc(pos, neg):
    from scipy.stats import rankdata
    pos, neg = np.asarray(pos, float), np.asarray(neg, float); pos, neg = pos[np.isfinite(pos)], neg[np.isfinite(neg)]
    if not len(pos) or not len(neg):
        return float('nan')
    r = rankdata(np.concatenate([pos, neg])); return float((r[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))


def report(args):
    out = args[0]; flags = None
    if '--flags' in args:
        flags = args[args.index('--flags') + 1]
    files = sorted(f for f in os.listdir(out) if f.endswith('.npz')); Z = {}
    for f in files:
        z = np.load(f'{out}/{f}'); Z[f[:-4]] = {k: z[k] for k in z.files if k != 'meta'}
    ALL = {k: np.concatenate([Z[w][k] for w in Z]) for k in next(iter(Z.values()))}
    M3 = ['crack_col', 'dark_col', 'crack_run', 'disorder', 'P_own', 'A_own', 'dark_own']; M2 = ['void', 'crack', 'edge_mm', 'wander']
    hot_thr = float(np.percentile(ALL['area_R'], 95)); hot = (ALL['area_R'] >= hot_thr) & (ALL['area_R'] > ALL['area_B'])
    lines = [f'{len(Z)} windings, {len(hot)} tiles; hot = reading-side stroke area >= {hot_thr:.3f} (top 5 %) and above the blind side: {hot.sum()} tiles',
             '', '== medians: all tiles vs hot tiles', 'measure'.ljust(12) + 'all'.rjust(9) + 'hot'.rjust(9)]
    for k in M3 + M2:
        lines.append(k.ljust(12) + f'{np.nanmedian(ALL[k]):9.3f}{np.nanmedian(ALL[k][hot]):9.3f}')
    lines += ['', '== Q1 (3D): do hot tiles sit where damage runs through the scroll? AUC hot vs other tiles (0.5 = no link; for P_own, below 0.5 = hot tiles are less planar)']
    lines.append('  ' + ', '.join(f'{k} {auc(ALL[k][hot], ALL[k][~hot]):.2f}' for k in M3) + '   | 2D for comparison: ' + ', '.join(f'{k} {auc(ALL[k][hot], ALL[k][~hot]):.2f}' for k in M2))
    if flags:
        POST = os.path.expanduser('~/scroll-prizes/runs/2026-10-11_tier23-newmodels/post/PHerc0813')
        lines += ['', '== the flagged false alarms: mean percentile of their strongest 4 mm tiles within their own winding (50 = ordinary)',
                  'flag'.ljust(16) + ''.join(k.rjust(11) for k in M3)]
        for ln in open(flags):
            w, d = ln.split()[:2]
            if w not in Z:
                continue
            post = json.load(open(f'{POST}/{w}/{w}__post.json'))['depths'][d]; z = Z[w]
            cy, cx = z['y'] + TILE_PX / 2, z['x'] + TILE_PX / 2; inside = np.zeros(len(cy), bool)
            for q in post['top_tiles']:
                inside |= (cy >= q['raw_y']) & (cy < q['raw_y'] + q['size_px']) & (cx >= q['raw_x']) & (cx < q['raw_x'] + q['size_px'])
            pct = []
            for k in M3:
                v = z[k]; fin = np.isfinite(v)
                pct.append(np.mean([(v[fin] < x).mean() * 100 for x in v[inside & fin]]) if (inside & fin).any() else float('nan'))
            lines.append(f'{w} d+{d}'.ljust(16) + ''.join(f'{p:11.0f}' for p in pct))
    txt = '\n'.join(lines); open(f'{out}/report.txt', 'w').write(txt + '\n'); print(txt)


if __name__ == '__main__':
    a = sys.argv[1:]
    report(a[1:]) if a[0] == 'report' else project(a)
