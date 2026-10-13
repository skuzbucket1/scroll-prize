"""Ink-first 'glowing sheets': a CT cross-section (a slice across the scroll at height z) through an ink-first block, with
the ink-first prediction painted where its patches cut the slice. The patches lie along the sheets of the surface
prediction, so the sheets light up where the model sees ink. With --mesh/--labels a second panel shows the same slice
with the human ink labels of a known-text segment drawn where that segment's mesh cuts the slice. --null adds a block
without known text, on the same colour scale. One colour ramp (dark to bright orange) for ink; grey CT underneath.
Values below the text block's median are drawn dim, so the patch coverage stays visible.
Usage: viz_glow.py --text <ct zarr> <patches.npz> <ink map tif> <z> --title T --out <png>
         [--mesh <tifxyz dir> --back <ink-first back npz> --labels <npz with labs, sups aligned to the mesh render> --window r0 r1 c0 c1 (full-res grid)]
         [--null <ct zarr> <patches.npz> <ink map tif> <z> <label>] [--centre 128] [--um 9.362]"""
import argparse
import cv2, numpy as np, tifffile, zarr
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

ap = argparse.ArgumentParser()
ap.add_argument('--text', nargs=4, required=True); ap.add_argument('--null', nargs=5); ap.add_argument('--mesh'); ap.add_argument('--labels'); ap.add_argument('--window', nargs=4, type=int)
ap.add_argument('--back', help='ink first mapped onto the known-text mesh (ink-first back), same window'); ap.add_argument('--back-key', default='readerv2_forward')
ap.add_argument('--title', default=''); ap.add_argument('--out', required=True); ap.add_argument('--centre', type=int, default=128)
ap.add_argument('--um', type=float, default=9.362); ap.add_argument('--text-label', default='known text')
a = ap.parse_args()
INK = LinearSegmentedColormap.from_list('ink', ['#6b4a00', '#E69F00', '#fff1c9']); INK.set_under('#3a2c12')       # below the median: dim (coverage)


def glow(patches, ink_map, z):
    """Mean ink of the patch-centre pixels lying within 0.7 voxel of the plane at height z, on the block's (y, x) grid."""
    P = np.load(patches); S, C = int(P['size']), a.centre; o = (S - C) // 2
    z0, z1, y0, y1, x0, x1 = map(int, P['box']); M = tifffile.imread(ink_map).astype(np.float32) / 255.
    ii, jj = np.mgrid[0:C, 0:C].astype(np.float32) + o - (S - 1) / 2
    acc = np.zeros((y1 - y0, x1 - x0)); cnt = np.zeros_like(acc)
    for k, (r, c) in enumerate(P['rowcol']):
        cen, u, v = P['centre'][k], P['u'][k], P['v'][k]
        pz = cen[0] + u[0] * ii + v[0] * jj; hit = np.abs(pz - z) < 0.7
        if not hit.any():
            continue
        py = np.round(cen[1] + u[1] * ii[hit] + v[1] * jj[hit]).astype(int) - y0
        px = np.round(cen[2] + u[2] * ii[hit] + v[2] * jj[hit]).astype(int) - x0
        val = M[r * S + o:r * S + o + C, c * S + o:c * S + o + C][hit]; ok = (py >= 0) & (py < acc.shape[0]) & (px >= 0) & (px < acc.shape[1])
        np.add.at(acc, (py[ok], px[ok]), val[ok]); np.add.at(cnt, (py[ok], px[ok]), 1)
    G = np.where(cnt > 0, acc / np.maximum(cnt, 1), np.nan)
    k = np.ones((3, 3), np.uint8); Gd = cv2.dilate(np.nan_to_num(G, nan=-1).astype(np.float32), k)          # 3 px lines
    return np.where(Gd >= 0, Gd, np.nan), (y0, y1, x0, x1)


def ct_slice(ct, z, box):
    y0, y1, x0, x1 = box; im = np.asarray(zarr.open(ct, mode='r')['0'][z, y0:y1, x0:x1]).astype(np.float32)
    v = im[im > 0]; lo, hi = np.percentile(v, [1, 99.5]) if v.size else (0, 255)
    return np.clip((im - lo) / max(hi - lo, 1), 0, 1) * 0.55


def label_points(z, box):
    """The labelled segment where its mesh cuts the plane: (y, x, label, supervised) at full mesh resolution."""
    X, Y, Z = (tifffile.imread(f'{a.mesh}/{c}.tif').astype(np.float32) for c in 'xyz')
    L = np.load(a.labels); labs, sups = L['labs'], L['sups']; r0, r1, c0, c1 = a.window
    rr, cc = np.mgrid[r0:r1, c0:c1].astype(np.float32) / 20.0
    up = lambda A: cv2.remap(A, cc, rr, cv2.INTER_LINEAR)
    Xu, Yu, Zu = up(X), up(Y), up(Z); hit = (np.abs(Zu - z) < 0.7) & (Xu > 0) & sups
    F = np.load(a.back)[a.back_key][hit] if a.back else np.full(hit.sum(), np.nan)
    return Yu[hit] - box[0], Xu[hit] - box[2], labs[hit] >= 128, F


blocks = [(a.text[0], a.text[1], a.text[2], int(a.text[3]), a.text_label)]
if a.null:
    blocks.append((a.null[0], a.null[1], a.null[2], int(a.null[3]), a.null[4]))
G = [glow(p, m, z) for _, p, m, z, _ in blocks]
allv = G[0][0][np.isfinite(G[0][0])]; vlo, vhi = np.percentile(allv, [50, 99.5])     # the text block's scale, for every panel
panels = [(ct_slice(ct, z, box), g, box, z, lab) for (ct, _, _, z, lab), (g, box) in zip(blocks, G)]


def show(ax, ct, over, title, crop=None, bar_mm=2):
    ax.set_facecolor('#161616'); ax.set_xticks([]); ax.set_yticks([]); [s.set_visible(False) for s in ax.spines.values()]
    y0, y1, x0, x1 = crop or (0, ct.shape[0], 0, ct.shape[1])
    ax.imshow(ct[y0:y1, x0:x1], cmap='gray', vmin=0, vmax=1, interpolation='lanczos', extent=(x0, x1, y1, y0))
    if over is not None:
        ax.imshow(np.ma.masked_invalid(over[y0:y1, x0:x1]), cmap=INK, vmin=vlo, vmax=vhi, interpolation='nearest', extent=(x0, x1, y1, y0))
    ax.set_title(title, color='#dddddd', fontsize=10.5, loc='left')
    L = bar_mm * 1000 / a.um; m = 0.04 * (x1 - x0)
    ax.plot([x1 - m - L, x1 - m], [y1 - m, y1 - m], color='#eeeeee', lw=3); ax.text(x1 - m - L / 2, y1 - 1.6 * m, f'{bar_mm:g} mm', color='#eeeeee', ha='center', fontsize=9)
    ax.set_xlim(x0, x1); ax.set_ylim(y1, y0)

ct, g, box, z, lab = panels[0]; h = z * a.um / 1000
fig = plt.figure(figsize=(16, 11 if a.null else 6.5), facecolor='#161616')
gs = fig.add_gridspec(2 if a.null else 1, 3, hspace=0.14, wspace=0.05, width_ratios=[1.15, 1, 1])
ax0 = fig.add_subplot(gs[0, 0]); show(ax0, ct, g, f'{lab}: ink first, every sheet')
if a.mesh:
    y, x, ink, F = label_points(z, box)
    cy, cx = np.median(y), np.median(x); r = 0.62 * max(np.ptp(y), np.ptp(x), 250) / 2 + 30
    crop = tuple(int(v) for v in (max(cy - r, 0), min(cy + r, ct.shape[0]), max(cx - r, 0), min(cx + r, ct.shape[1])))
    ax0.add_patch(plt.Rectangle((crop[2], crop[0]), crop[3] - crop[2], crop[1] - crop[0], fill=False, ec='#eeeeee', lw=1, ls='--'))
    ax = fig.add_subplot(gs[0, 1]); show(ax, ct, None, 'zoom: ink first on the labelled sheet', crop, 1)
    f = np.isfinite(F); ax.scatter(x[~f], y[~f], s=3, color='#8a8a8a', linewidths=0, label='no patch nearby')
    ax.scatter(x[f], y[f], s=7, c=F[f], cmap=INK, vmin=vlo, vmax=vhi, linewidths=0)
    ax.legend(loc='upper left', frameon=False, labelcolor='#dddddd', markerscale=3, fontsize=9)
    ax = fig.add_subplot(gs[0, 2]); show(ax, ct, None, 'zoom: human ink labels, same sheet', crop, 1)
    ax.scatter(x[~ink], y[~ink], s=5, color='#9a9a9a', linewidths=0, label='labelled: no ink')
    ax.scatter(x[ink], y[ink], s=7, color='#fff1c9', linewidths=0, label='labelled: ink')
    ax.legend(loc='upper left', frameon=False, labelcolor='#dddddd', markerscale=2.5, fontsize=9)
    print('label points', len(x), 'ink', int(ink.sum()), 'covered', int(f.sum()), 'crop', crop, 'ink-first on ink %.3f / no ink %.3f' % (np.nanmean(F[ink]), np.nanmean(F[~ink])))
if a.null:
    ct, g, box, z, lab = panels[1]; show(fig.add_subplot(gs[1, :]), ct, g, f'{lab}: ink first, every sheet, same colour scale')
cax = fig.add_axes([0.35, 0.05 if a.null else 0.02, 0.3, 0.012])
cb = fig.colorbar(plt.cm.ScalarMappable(cmap=INK, norm=plt.Normalize(vlo, vhi)), cax=cax, orientation='horizontal', extend='min')
cb.set_label('ink-first prediction (Reader v2); dim = below the known-text median', color='#dddddd', fontsize=9)
cb.ax.tick_params(colors='#aaaaaa', labelsize=8); cb.outline.set_visible(False)
fig.suptitle(a.title, color='#eeeeee', fontsize=14, x=0.02, ha='left')
fig.savefig(a.out, dpi=110, facecolor=fig.get_facecolor(), bbox_inches='tight')
print(a.out, 'scale', round(float(vlo), 3), round(float(vhi), 3))
