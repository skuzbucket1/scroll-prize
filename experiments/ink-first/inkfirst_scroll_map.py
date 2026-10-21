"""Whole-scroll view of an ink-first sweep: every patch of every block (summary.npz from inkfirst_block_summary.py) placed at
its 3D position. Writes
  map_<order>.png    from above (patches within `slab` of the scroll's middle height) and from the side (patches near the
                     centre plane), coloured by frac50 (share of the patch centre at ink >= 0.5); patches that look like
                     damage (air > 0.3: much of the patch is a gap or crack) are drawn grey
  gallery_<order>_<k>.jpg   the hottest plausible patches of the whole scroll, ranked (CT surface layer | ink), with the
                     patch's score on this side and on the other side
  clusters_<order>.tsv      groups of hot plausible patches within `radius` of each other (candidates for deep looks), with
                     `one_sided` = share of the cluster's patches hotter on this side than on the other by >= 0.2
  blocks.tsv         per block: plausible patches, hot share on each side, mean ink this side minus the other (fwd - rev)
                     and its z (patches overlap, so z overstates; on known text the hot share was ~1.7x higher on the
                     reading side (fwd), on text-free blocks even)
Usage: inkfirst_scroll_map.py <results dir (w*/b*/summary.npz)> <out dir> [--coarse <coarse CT zarr dir from inkfirst_plan.py>] (all options: --help)
       [--model readerv2] [--level 5] [--hot 0.5] [--radius 3.0] [--um 8.64] [--top 60] [--label PHerc0175A]
       (no --coarse: no map figure, the rest as usual)"""
import argparse, glob, os
import cv2, numpy as np, zarr

ap = argparse.ArgumentParser()
ap.add_argument('res'); ap.add_argument('out'); ap.add_argument('--coarse'); ap.add_argument('--model', default='readerv2')
ap.add_argument('--level', type=int, default=5); ap.add_argument('--hot', type=float, default=0.5); ap.add_argument('--radius', type=float, default=3.0)
ap.add_argument('--um', type=float, default=8.64); ap.add_argument('--top', type=int, default=60); ap.add_argument('--label', default='PHerc0175A')
a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
files = sorted(glob.glob(os.path.join(a.res, '**', 'summary.npz'), recursive=True))
print(len(files), 'blocks')
rows = {'fwd': [], 'rev': []}; tops = {'fwd': [], 'rev': []}; blocks = []
other = {'fwd': 'rev', 'rev': 'fwd'}
for f in files:
    blk = os.path.basename(os.path.dirname(f)); S = np.load(f)
    c = S['centre']
    air = S['air'] if 'air' in S.files else np.zeros(len(c), np.float32)          # older summaries: no plausibility scores
    lc = S['layer_corr'] if 'layer_corr' in S.files else np.ones(len(c), np.float32); plaus = air <= 0.3
    if all(f'stats_{a.model}_{o}' in S.files for o in ('fwd', 'rev')):
        F, Rv = S[f'stats_{a.model}_fwd'][plaus], S[f'stats_{a.model}_rev'][plaus]
        d = F[:, 0] - Rv[:, 0]; z_ = d.mean() / (d.std() / np.sqrt(len(d))) if len(d) > 1 and d.std() > 0 else 0.0
        blocks.append((blk, len(F), float((F[:, 2] >= a.hot).mean()) if len(F) else 0.0, float((Rv[:, 2] >= a.hot).mean()) if len(F) else 0.0,
                       float(d.mean()) if len(d) else 0.0, float(z_)))
    for o in ('fwd', 'rev'):
        k = f'stats_{a.model}_{o}'
        if k not in S.files:
            continue
        st = S[k]; ko = f'stats_{a.model}_{other[o]}'; so = S[ko] if ko in S.files else np.full_like(st, np.nan)
        t64 = S[f'ink64_{a.model}_{o}'] if f'ink64_{a.model}_{o}' in S.files else None
        o64 = S[f'ink64_{a.model}_{other[o]}'] if f'ink64_{a.model}_{other[o]}' in S.files else None
        for j in range(len(c)):
            rows[o].append((blk, j, *c[j], st[j, 2], st[j, 1], air[j], lc[j], bool(plaus[j]), so[j, 2]))
        if f'topplaus_{a.model}_{o}' in S.files:
            tp, tct, tink = S[f'topplaus_{a.model}_{o}'], S[f'topplausct_{a.model}_{o}'], S[f'topplausink_{a.model}_{o}']
        elif f'top_{a.model}_{o}' in S.files:
            tp, tct, tink = S[f'top_{a.model}_{o}'], S['topct'], S[f'topink_{a.model}_{o}']
        else:                                                                # reference summaries: no full-size patches
            tp, tct, tink = [], [], []
        for q, j in enumerate(tp):
            tops[o].append((float(st[j, 2]), blk, int(j), tct[q], tink[q], *c[j], float(so[j, 2]),
                            t64[j] if t64 is not None else None, o64[j] if o64 is not None else None))
f = 2 ** a.level; C = None
if a.coarse and os.path.isdir(a.coarse):
    C = np.asarray(zarr.open(a.coarse, mode='r')[str(a.level)]).astype(np.float32)
    mz = C.shape[0] // 2; my = C.shape[1] // 2
    top_img = cv2.normalize(C[mz], None, 0, 160, cv2.NORM_MINMAX).astype(np.uint8)
    side_img = cv2.normalize(C[:, my, :], None, 0, 160, cv2.NORM_MINMAX).astype(np.uint8)
mm = a.um / 1000.0
for o in ('fwd', 'rev'):
    R = rows[o]
    if not R:
        continue
    z = np.array([r[2] for r in R]); y = np.array([r[3] for r in R]); x = np.array([r[4] for r in R])
    hot = np.array([r[5] for r in R]); pl = np.array([r[9] for r in R]); hot_o = np.array([r[10] for r in R])
    print(f'{o}: {len(R)} patches, {pl.mean():.0%} plausible; frac50 median {np.median(hot):.3f}, 99th pct {np.percentile(hot, 99):.3f}; '
          f'hot (>= {a.hot}) and plausible: {int(((hot >= a.hot) & pl).sum())}')
    try:
        if C is None:
            raise RuntimeError('no --coarse volume')
        import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
        fig, ax = plt.subplots(1, 2, figsize=(16, 9), facecolor='#161616', gridspec_kw=dict(width_ratios=[C.shape[2] / C.shape[1], C.shape[2] / C.shape[0] * 1.0]))
        slab = 0.12 * C.shape[0] * f
        for k, (img, sel, X, Y, ttl) in enumerate([(top_img, np.abs(z - mz * f) < slab, x, y, f'from above (patches within {slab * mm:.0f} mm of {mz * f * mm:.0f} mm height)'),
                                                    (side_img, np.abs(y - my * f) < 0.06 * C.shape[1] * f, x, z, 'from the side (patches near the centre plane)')]):
            ax[k].imshow(img, cmap='gray', extent=(0, img.shape[1] * f, img.shape[0] * f, 0)); ax[k].set_facecolor('#161616')
            g = sel & ~pl; ax[k].scatter(X[g], Y[g], s=2, c='#6e6e6e', linewidths=0)
            h = sel & pl; o_ = np.argsort(hot[h]); sc = ax[k].scatter(X[h][o_], Y[h][o_], s=4, c=hot[h][o_], cmap='inferno', vmin=0, vmax=max(0.8, a.hot), linewidths=0)
            ax[k].set_title(ttl, color='#dddddd', fontsize=10, loc='left'); ax[k].set_xticks([]); ax[k].set_yticks([])
            if k == 1:
                ax[k].invert_yaxis()
        cb = fig.colorbar(sc, ax=ax, orientation='horizontal', fraction=0.03, pad=0.04); cb.set_label(f'ink first ({a.model}, {o}): share of the patch centre with ink >= 0.5; grey = looks like damage', color='#dddddd')
        cb.ax.tick_params(colors='#aaaaaa')
        fig.suptitle(f'{a.label}, ink first over the whole scroll', color='#eeeeee', x=0.02, ha='left')
        fig.savefig(os.path.join(a.out, f'map_{o}.png'), dpi=100, facecolor=fig.get_facecolor(), bbox_inches='tight'); plt.close(fig)
    except Exception as e:
        print('no map figure:', e)
    # clusters of hot plausible patches (single linkage within `radius` mm)
    idx = np.nonzero((hot >= a.hot) & pl)[0]; P = np.stack([z[idx], y[idx], x[idx]], 1) * mm
    lab = -np.ones(len(idx), int); nc = 0
    if len(idx):
        from scipy.spatial import cKDTree
        tree = cKDTree(P)
        for s0 in range(len(idx)):
            if lab[s0] >= 0:
                continue
            stack = [s0]; lab[s0] = nc
            while stack:
                q = stack.pop()
                for nb in tree.query_ball_point(P[q], a.radius):
                    if lab[nb] < 0:
                        lab[nb] = nc; stack.append(nb)
            nc += 1
    with open(os.path.join(a.out, f'clusters_{o}.tsv'), 'w') as fo:
        fo.write('cluster\tpatches\tmean_frac50\tmax_frac50\tother_side\tone_sided\tz\ty\tx\tblocks\n')
        cl = []
        for c_ in range(nc):
            m = idx[lab == c_]
            cl.append((len(m), float(hot[m].mean()), float(hot[m].max()), float(np.nanmean(hot_o[m])), float(np.mean(hot[m] - hot_o[m] >= 0.2)),
                       *np.mean(np.stack([z[m], y[m], x[m]], 1), 0), ','.join(sorted({R[j][0] for j in m}))))
        for k, c_ in enumerate(sorted(cl, key=lambda t: (-t[0], -t[1]))):
            fo.write(f'c{k:03d}\t{c_[0]}\t{c_[1]:.3f}\t{c_[2]:.3f}\t{c_[3]:.3f}\t{c_[4]:.2f}\t{c_[5]:.0f}\t{c_[6]:.0f}\t{c_[7]:.0f}\t{c_[8]}\n')
    print(f'{o}: {nc} clusters of hot plausible patches (within {a.radius} mm); biggest: {sorted([int((lab == c_).sum()) for c_ in range(nc)], reverse=True)[:8]}')
    # ranked gallery of the hottest plausible patches of the whole scroll
    T = sorted(tops[o], key=lambda t: -t[0])[:a.top]
    tiles = []
    if not T:
        continue
    for (fr, blk, j, ct, ink, zz, yy, xx, fo_, t64, o64) in T:
        ctn = cv2.normalize(ct, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
        tile = np.concatenate([cv2.cvtColor(ctn, cv2.COLOR_GRAY2BGR), cv2.applyColorMap(ink, cv2.COLORMAP_INFERNO)], 1)
        cv2.putText(tile, f'{blk} #{j}  z{zz:.0f} y{yy:.0f} x{xx:.0f}', (6, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(tile, f'{o} {fr:.2f} / {other[o]} {fo_:.2f}', (ct.shape[1] + 6, tile.shape[0] - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1, cv2.LINE_AA)
        tiles.append(tile)
    gap = lambda t: cv2.copyMakeBorder(t, 2, 2, 2, 2, cv2.BORDER_CONSTANT, value=(22, 22, 22))
    for p in range(0, len(tiles), 12):
        page = [gap(t) for t in tiles[p:p + 12]]
        while len(page) % 3:
            page.append(np.zeros_like(page[0]))
        g = np.concatenate([np.concatenate(page[i:i + 3], 1) for i in range(0, len(page), 3)], 0)
        cv2.imwrite(os.path.join(a.out, f'gallery_{o}_{p // 12 + 1}.jpg'), g, [cv2.IMWRITE_JPEG_QUALITY, 88])
if blocks:
    with open(os.path.join(a.out, 'blocks.tsv'), 'w') as fo:
        fo.write('block\tplausible\thot_fwd\thot_rev\tfwd_minus_rev\tz\n')
        for b in sorted(blocks, key=lambda b: -b[5]):
            fo.write(f'{b[0]}\t{b[1]}\t{b[2]:.4f}\t{b[3]:.4f}\t{b[4]:+.4f}\t{b[5]:+.2f}\n')
    zz_ = np.array([b[5] for b in blocks]); hf = np.array([b[2] for b in blocks]); hr = np.array([b[3] for b in blocks])
    print(f'blocks: {len(blocks)}; fwd - rev z median {np.median(zz_):+.1f} (10th {np.percentile(zz_, 10):+.1f}, 90th {np.percentile(zz_, 90):+.1f}); '
          f'hot share fwd {hf.mean():.2%}, rev {hr.mean():.2%} (known text: fwd ~1.7x rev)')
