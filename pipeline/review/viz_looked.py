"""'Where we've looked': one scroll from above (a CT slice across the scroll at height z) and from the side (a CT slice
along the scroll axis through the centre of that slice). Every fitted winding is drawn where its mesh crosses the slice,
coloured by what happened to it: fitted only, searched (rendered, inked, scored), flagged by stroke-score 0.2 and checked
by eye, or inked and still being scored. The side view also marks bands that are still being fitted.
Usage: viz_looked.py --vol <CT zarr> --z <z> --um <um> --title T --out <png>
         --fitted <snapped dir>                        all windings of a fit (thin grey)
         --band <flattened dir> <searched|scoring> <w... | all>
         --flag <fit> <winding> <label>                flagged by stroke-score 0.2, checked by eye (fit: part of the band path)
         --fitting <z0> <z1>                           a band still being fitted (side view)"""
import argparse, glob, os, re
import numpy as np, tifffile, zarr
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

ap = argparse.ArgumentParser()
ap.add_argument('--vol', required=True); ap.add_argument('--z', type=int, required=True); ap.add_argument('--um', type=float, default=9.362)
ap.add_argument('--title', default=''); ap.add_argument('--out', required=True); ap.add_argument('--fitted')
ap.add_argument('--band', nargs='+', action='append', default=[]); ap.add_argument('--flag', nargs=3, action='append', default=[])
ap.add_argument('--fitting', nargs=2, type=int, action='append', default=[]); ap.add_argument('--top-level', type=int, default=2)
ap.add_argument('--side-level', type=int, default=3)
a = ap.parse_args()
GREY, BLUE, ORANGE, SKY = '#8c8c8c', '#0072B2', '#E69F00', '#56B4E9'        # Okabe-Ito


def windings(d):
    """{name: (x, y, z) grids, rows along the scroll axis} for every tifxyz under a snapped or flattened fit directory."""
    out = {}
    for f in sorted(glob.glob(os.path.join(d, 'w*', 'z.tif')) + glob.glob(os.path.join(d, 'w*', 'tifxyz', '*', 'z.tif'))):
        m = re.search(r'/(w\d{3})(_exp[^/]*)?/', f)
        if not m or 'spliced' in f:
            continue
        t = os.path.dirname(f); X, Y, Z = (tifffile.imread(os.path.join(t, c + '.tif')).astype(np.float32) for c in 'xyz')
        if np.nanstd(np.where(Z > 0, Z, np.nan), 1).mean() < np.nanstd(np.where(Z > 0, Z, np.nan), 0).mean():
            X, Y, Z = X.T, Y.T, Z.T                                                   # make rows run along the scroll axis
        out[m.group(1)] = (X, Y, Z)
    return out


def crossings(G, axis, value, along):
    """Points where the mesh crosses the plane <axis> = value, by linear interpolation between neighbouring grid points
    in direction `along` (0: between rows, 1: between columns). Returns an (n, 3) array of x, y, z."""
    X, Y, Z = G; A = {'x': X, 'y': Y, 'z': Z}[axis]; ok = (Z > 0) & (X > 0) & (Y > 0)
    sl0, sl1 = ((slice(None, -1), slice(None)), (slice(1, None), slice(None))) if along == 0 else ((slice(None), slice(None, -1)), (slice(None), slice(1, None)))
    a0, a1 = A[sl0] - value, A[sl1] - value; hit = ok[sl0] & ok[sl1] & (a0 * a1 <= 0) & (a0 != a1)
    t = (a0 / np.where(hit, a0 - a1, 1))[hit]
    return np.stack([C[sl0][hit] + t * (C[sl1][hit] - C[sl0][hit]) for C in (X, Y, Z)], 1), np.nonzero(hit)


def side_points(G, y):
    """Crossings with the side-view plane, without stray points outside the mesh's own height range."""
    P, _ = crossings(G, 'y', y, 1); Z = G[2][G[2] > 0]
    if len(P) and Z.size:
        lo, hi = np.percentile(Z, [0.5, 99.5]); P = P[(P[:, 2] >= lo - 50) & (P[:, 2] <= hi + 50)]
    return P


def top_lines(G, z):
    """The winding at height z as ordered polylines (one point per column, split at gaps)."""
    P, (r, c) = crossings(G, 'z', z, 0)
    if not len(P):
        return []
    o = np.argsort(c); P, c = P[o], c[o]
    cuts = np.nonzero(np.diff(c) > 2)[0] + 1
    return [s for s in np.split(P, cuts) if len(s) > 1]


g = zarr.open(a.vol, mode='r'); ft, fs = 2 ** a.top_level, 2 ** a.side_level
top = np.asarray(g[str(a.top_level)][a.z // ft]).astype(np.float32)
m = top > 0; ys, xs = np.nonzero(m); cy, cx = ys.mean() * ft, xs.mean() * ft
pad = 40; ty0, ty1, tx0, tx1 = max(ys.min() - pad, 0), ys.max() + pad, max(xs.min() - pad, 0), xs.max() + pad
side = np.asarray(g[str(a.side_level)][:, int(cy) // fs, :]).astype(np.float32)
zr = np.nonzero((side > 0).mean(1) > 0.02)[0]; sz0, sz1 = zr.min(), zr.max()
sx = np.nonzero((side > 0).mean(0) > 0.02)[0]; sx0, sx1 = max(sx.min() - pad // 2, 0), sx.max() + pad // 2


def grey(im):
    v = im[im > 0]; lo, hi = np.percentile(v, [1, 99.5]) if v.size else (0, 255)
    return np.clip((im - lo) / max(hi - lo, 1), 0, 1) * 0.6

mm = a.um / 1000.0
fig = plt.figure(figsize=(16, 9), facecolor='#161616')
gs = fig.add_gridspec(1, 2, width_ratios=[(tx1 - tx0) / (ty1 - ty0), (sx1 - sx0) * fs / ((sz1 - sz0) * fs) * 1.0], wspace=0.08)
axT, axS = fig.add_subplot(gs[0]), fig.add_subplot(gs[1])
for ax in (axT, axS):
    ax.set_facecolor('#161616'); ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)
axT.imshow(grey(top[ty0:ty1, tx0:tx1]), cmap='gray', vmin=0, vmax=1, extent=(tx0 * ft, tx1 * ft, ty1 * ft, ty0 * ft), interpolation='lanczos')
S = grey(side[sz0:sz1 + 1, sx0:sx1])
axS.imshow(S, cmap='gray', vmin=0, vmax=1, extent=(sx0 * fs, sx1 * fs, sz1 * fs, sz0 * fs), interpolation='lanczos', aspect='equal')
axS.invert_yaxis()                                                                                          # height up

counts, spans, nflag, nside = {}, [], 0, 0
if a.fitted:
    for w, G in windings(a.fitted).items():
        for L in top_lines(G, a.z):
            axT.plot(L[:, 0], L[:, 1], color=GREY, lw=0.35, alpha=0.55)
        P = side_points(G, cy); axS.scatter(P[:, 0], P[:, 2], s=0.15, color=GREY, alpha=0.6, linewidths=0)
for b in sorted(a.band, key=lambda b: b[1] == 'searched'):                                                   # searched on top
    d, status, sel = b[0], b[1], b[2:]; flags = {w: t for f, w, t in a.flag if f in d}
    W = windings(d); W = W if sel == ['all'] else {w: G for w, G in W.items() if w in sel}
    counts[status] = counts.get(status, 0) + len(W)
    zz = np.concatenate([G[2][G[2] > 0] for G in W.values()]); spans.append((status, np.percentile(zz, 0.2), np.percentile(zz, 99.8)))
    col = SKY if status == 'scoring' else BLUE
    for w, G in W.items():
        P = side_points(G, cy)
        axS.scatter(P[:, 0], P[:, 2], s=0.5, color=ORANGE if (w in flags and status == 'searched') else col, linewidths=0)
        if status != 'searched':
            continue
        for L in top_lines(G, a.z):
            axT.plot(L[:, 0], L[:, 1], color=ORANGE if w in flags else BLUE, lw=2.0 if w in flags else 0.7, alpha=1 if w in flags else 0.9)
        if w in flags:
            TL = top_lines(G, a.z)
            if TL:                                                                                            # label in the top view
                L = max(TL, key=len); p = L[np.argmin(L[:, 1])]                                               # its top-most point
                axT.annotate(f'{w}: {flags[w]}', p[:2], xytext=(tx0 * ft + 0.62 * (tx1 - tx0) * ft, ty0 * ft + (0.04 + 0.045 * nflag) * (ty1 - ty0) * ft),
                             color='#eeeeee', fontsize=10, va='center', arrowprops=dict(arrowstyle='-', color=ORANGE, lw=1.2)); nflag += 1
            elif len(P):                                                                                      # not at the top-view height: label it in the side view
                p = P[np.argmax(P[:, 0])]
                axS.annotate(f'{w}: {flags[w]}', (p[0], p[2]), xytext=(sx0 * fs + 0.02 * (sx1 - sx0) * fs, p[2] + (0.03 + 0.035 * nside) * (sz1 - sz0) * fs),
                             color='#eeeeee', fontsize=9, va='center', arrowprops=dict(arrowstyle='-', color=ORANGE, lw=1.0)); nside += 1
for z0, z1 in a.fitting:
    axS.fill_between([sx0 * fs, sx1 * fs], z0, z1, color='#bbbbbb', alpha=0.12, hatch='//', ec='#888888', lw=0)
    axS.text(sx1 * fs + (0.05 + 0.04 * len(a.band)) * (sx1 - sx0) * fs, (z0 + z1) / 2, f'being fitted\n{z0 * mm:.0f}–{z1 * mm:.0f} mm', color='#dddddd', fontsize=9, va='center')
axS.axhline(a.z, color='#eeeeee', lw=0.8, ls=(0, (4, 4))); axS.text(sx0 * fs, a.z, 'top view  ', color='#eeeeee', fontsize=9, va='center', ha='right')
axT.axhline(cy, color='#eeeeee', lw=0.8, ls=(0, (4, 4))); axT.text(tx1 * ft, cy, '  side view', color='#eeeeee', fontsize=9, va='center')
Wd, ty = (sx1 - sx0) * fs, []
for k, (status, z0, z1) in enumerate(spans):
    x = sx1 * fs + (0.03 + 0.04 * k) * Wd
    axS.plot([x, x], [z0, z1], color=SKY if status == 'scoring' else BLUE, lw=4, solid_capstyle='butt', clip_on=False)
    yt = (z0 + z1) / 2
    while any(abs(yt - u) < 0.045 * (sz1 - sz0) * fs for u in ty):                                           # keep labels apart
        yt -= 0.02 * (sz1 - sz0) * fs
    ty.append(yt)
    axS.text(sx1 * fs + (0.05 + 0.04 * len(spans)) * Wd, yt, f"{'searched' if status == 'searched' else 'being scored'}\n{z0 * mm:.0f}–{z1 * mm:.0f} mm",
             color='#dddddd', fontsize=9, va='center')


def scalebar(ax, x1, y, ft_mm, label):
    L = ft_mm / mm; ax.plot([x1 - L, x1], [y, y], color='#eeeeee', lw=3, solid_capstyle='butt')
    ax.text(x1 - L / 2, y, label, color='#eeeeee', fontsize=9, ha='center', va='bottom')

scalebar(axT, tx1 * ft - 0.04 * (tx1 - tx0) * ft, ty1 * ft - 0.04 * (ty1 - ty0) * ft, 10, '10 mm\n')
scalebar(axS, sx1 * fs - 0.04 * (sx1 - sx0) * fs, sz0 * fs + 0.03 * (sz1 - sz0) * fs, 10, '10 mm\n')
axT.set_title(f'from above, at {a.z * mm:.0f} mm height', color='#dddddd', fontsize=11, loc='left')
axS.set_title('from the side, through the centre', color='#dddddd', fontsize=11, loc='left')
h = [Line2D([], [], color=GREY, lw=1, label='fitted, not searched'),
     Line2D([], [], color=BLUE, lw=2, label=f"searched: rendered, inked, scored ({counts.get('searched', 0)} windings)"),
     Line2D([], [], color=ORANGE, lw=3, label='flagged by stroke-score 0.2, checked by eye: not text')]
if counts.get('scoring'):
    h.append(Line2D([], [], color=SKY, lw=2, label=f"inked, being scored ({counts['scoring']} windings)"))
if a.fitting:
    h.append(Patch(facecolor='#bbbbbb', alpha=0.25, hatch='//', label='being fitted'))
fig.legend(handles=h, loc='lower center', ncol=len(h), frameon=False, labelcolor='#dddddd', fontsize=10)
fig.suptitle(a.title, color='#eeeeee', fontsize=14, x=0.02, ha='left')
fig.savefig(a.out, dpi=110, facecolor=fig.get_facecolor(), bbox_inches='tight')
print(a.out, 'centre', round(cy), round(cx), 'side z', sz0 * fs, sz1 * fs, counts)
