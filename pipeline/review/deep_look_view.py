"""Figures for a deep look (six models x depths, bin/depth_sweep.sh on a cropped 66-layer render), with the display rules
of Nieuwlaar's ensemble_maps.py: villa maps v -> clip((v - 64) / 128, 0, 1), Hecate v / 255 resized from its 9.6 um grid;
reading side = the _reverse maps, blind side shown with the reading side's statistics; one stretch per model over all
depths (never per depth); ensemble = mean of the models' z-scores (pooled reading-side mean and SD); valid = CT > 0 in
all 66 layers. Real ink shows on the reading side near the surface (d 0..+2) and fades with depth; damage shows on both
sides or keeps its shape over many depths.
Writes to <out>: depths.jpg (ensemble at a range of depths: reading | blind | CT layer 33+d), models.jpg (each model at
the depth where the ensemble's reading - blind is highest), profile.png (reading - blind against depth, per model and
ensemble) and profile.tsv. Window: the region judged (crop pixels; default: the crop minus `margin`), reading
orientation (rotated 180 degrees), 5 mm bar.
Usage: deep_look_view.py <crop.zarr> <maps dir> <out dir> [--label ...] [--um 9.362] [--margin 256] [--window y0 x0 h w] (all options: --help)
       [--show -4,-2,-1,0,1,2,3,4,6] [--shrink 2]"""
import argparse, glob, os, re
import cv2, numpy as np, tifffile, zarr

ap = argparse.ArgumentParser()
ap.add_argument('crop'); ap.add_argument('maps'); ap.add_argument('out'); ap.add_argument('--label', default='')
ap.add_argument('--um', type=float, default=9.362); ap.add_argument('--margin', type=int, default=256)
ap.add_argument('--window', type=int, nargs=4); ap.add_argument('--show', default='-4,-2,-1,0,1,2,3,4,6'); ap.add_argument('--shrink', type=int, default=2)
a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
name = os.path.basename(a.crop.rstrip('/')).replace('.zarr', '')
CT = zarr.open(a.crop, mode='r')['0']; H, W = CT.shape[1:]
valid = np.ones((H, W), bool)
for k in range(CT.shape[0]):
    valid &= np.asarray(CT[k]) > 0
y0, x0, h, w = a.window if a.window else (a.margin, a.margin, min(H - a.margin, H) - a.margin, W - 2 * a.margin)
h = min(h, H - y0); w = min(w, W - x0); win = (slice(y0, y0 + h), slice(x0, x0 + w)); vw = valid[win]

# index the maps: (model, depth, side) -> path
idx = {}
for f in glob.glob(os.path.join(a.maps, f'{name}__*')):
    base = os.path.basename(f); parts = base.rsplit('.', 1)[0].split('__')
    if len(parts) != 3:
        continue
    m, tail = parts[1], parts[2]; side = 'reading' if tail.endswith('_reverse') else 'blind'; tail = tail.replace('_reverse', '')
    mm_ = re.match(r'L66s(\d+)$', tail) or None; mz = re.match(r'L66zc([0-9.]+)$', tail)
    if mm_ and base.endswith('.tif'):
        d = int(mm_.group(1)) - 25
    elif mz and base.endswith('.png'):
        d = int(round(float(mz.group(1)) - 32.5))
    else:
        continue
    idx[(m, d, side)] = f
models = sorted({k[0] for k in idx}); depths = sorted({k[1] for k in idx if (k[0], k[1], 'reading') in idx and (k[0], k[1], 'blind') in idx})
print(f'{name}: {len(idx)} maps, models {models}, depths {depths[0] if depths else None}..{depths[-1] if depths else None}')


def load(m, d, side):
    f = idx.get((m, d, side))
    if f is None:
        return None
    v = cv2.imread(f, cv2.IMREAD_UNCHANGED) if f.endswith('.png') else tifffile.imread(f)
    if v.ndim == 3:
        v = v[..., 0]
    if f.endswith('.png'):
        p = cv2.resize(v.astype(np.float32) / 255.0, (W, H), interpolation=cv2.INTER_LINEAR)
    else:
        p = np.clip((v.astype(np.float32) - 64) / 128, 0, 1)
    return p


# pass 1: pooled reading-side statistics per model (mean, SD, p1, p99.5) over all depths, valid pixels of the window
st = {}
for m in models:
    vals = [load(m, d, 'reading')[win][vw] for d in depths if (m, d, 'reading') in idx]
    if not vals:
        continue
    x = np.concatenate(vals); st[m] = (float(x.mean()), float(x.std()) or 1.0, *np.percentile(x, [1, 99.5]))
# pass 2: per depth, the ensemble (mean z of the models present on both sides) and the profile numbers
E, rows = {}, []
for d in depths:
    zs = {'reading': [], 'blind': []}
    for m in st:
        r, b = load(m, d, 'reading'), load(m, d, 'blind')
        if r is None or b is None:
            continue
        mu, sd = st[m][:2]
        zr, zb = (r[win] - mu) / sd, (b[win] - mu) / sd
        zs['reading'].append(zr); zs['blind'].append(zb)
        rows.append((d, m, float(zr[vw].mean()), float(zb[vw].mean()), float((r[win][vw] >= 0.5).mean()), float((b[win][vw] >= 0.5).mean())))
    if zs['reading']:
        E[d] = {s: np.mean(zs[s], 0) for s in zs}; n = len(zs['reading'])
        rows.append((d, f'ensemble ({n})', float(E[d]['reading'][vw].mean()), float(E[d]['blind'][vw].mean()), np.nan, np.nan))
with open(os.path.join(a.out, 'profile.tsv'), 'w') as fo:
    fo.write('depth\tmodel\treading_z\tblind_z\treading_minus_blind\treading_share50\tblind_share50\n')
    for d, m, zr, zb, sr, sb in rows:
        fo.write(f'{d:+d}\t{m}\t{zr:.3f}\t{zb:.3f}\t{zr - zb:+.3f}\t{sr:.4f}\t{sb:.4f}\n')
ens = [(d, zr - zb, int(m.split('(')[1].rstrip(')'))) for d, m, zr, zb, _, _ in rows if m.startswith('ensemble')]
full = max((t[2] for t in ens), default=0)                       # best depth among depths with every model
best = max((t for t in ens if t[2] == full), key=lambda t: t[1])[0] if ens else 0
print('ensemble reading - blind by depth: ' + ', '.join(f'{d:+d}: {v:+.2f} ({n})' for d, v, n in ens) + f'; best d {best:+d} (of the depths with all {full} models)')

# figures
allr = np.concatenate([E[d]['reading'][vw][::7] for d in E]) if E else np.zeros(1)
lo, hi = np.percentile(allr, [1, 99.5]); cts = np.concatenate([np.asarray(CT[33 + d])[win][vw][::7] for d in E if 0 <= 33 + d < CT.shape[0]])
clo, chi = np.percentile(cts[cts > 0], [1, 99.5])
sh = a.shrink; bar = int(5000 / a.um / sh)


def tile(img, lab, vmin, vmax):
    t = np.clip((img - vmin) / max(vmax - vmin, 1e-6) * 255, 0, 255).astype(np.uint8); t[~vw] = 0
    t = cv2.resize(t[::-1, ::-1], (w // sh, h // sh), interpolation=cv2.INTER_AREA); t = cv2.cvtColor(t, cv2.COLOR_GRAY2BGR)
    cv2.putText(t, lab, (8, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)
    cv2.line(t, (10, t.shape[0] - 10), (10 + bar, t.shape[0] - 10), (255, 255, 255), 2)
    return cv2.copyMakeBorder(t, 2, 2, 2, 2, cv2.BORDER_CONSTANT, value=(30, 30, 30))


show = [d for d in (int(s) for s in a.show.split(',')) if d in E]
if show:
    grid = [np.concatenate([tile(E[d]['reading'], f'{a.label}  d {d:+d}  ensemble, reading side', lo, hi),
                            tile(E[d]['blind'], f'd {d:+d}  ensemble, blind side', lo, hi),
                            tile(np.asarray(CT[33 + d])[win].astype(np.float32), f'd {d:+d}  CT layer {33 + d}', clo, chi)], 1) for d in show]
    cv2.imwrite(os.path.join(a.out, 'depths.jpg'), np.concatenate(grid, 0), [cv2.IMWRITE_JPEG_QUALITY, 90])
if best in E:
    mrows = []
    for m in st:
        r, b = load(m, best, 'reading'), load(m, best, 'blind')
        if r is None or b is None:
            continue
        _, _, p1, p99 = st[m]
        mrows.append(np.concatenate([tile(r[win], f'{m}  d {best:+d}  reading side', p1, p99), tile(b[win], f'{m}  d {best:+d}  blind side', p1, p99)], 1))
    if mrows:
        cv2.imwrite(os.path.join(a.out, 'models.jpg'), np.concatenate(mrows, 0), [cv2.IMWRITE_JPEG_QUALITY, 90])
try:
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for m in sorted({r[1] for r in rows}):
        pts = sorted((d, zr - zb) for d, mm2, zr, zb, _, _ in rows if mm2 == m)
        ax.plot([p[0] for p in pts], [p[1] for p in pts], lw=3 if m.startswith('ensemble') else 1.2, label=m, color='k' if m.startswith('ensemble') else None)
    ax.axhline(0, color='#999999', lw=0.8); ax.set_xlabel('depth d (layer - 33; + away from the scroll axis)'); ax.set_ylabel('reading - blind (z)')
    ax.set_title(f'{a.label}: reading minus blind side in the window, by depth', fontsize=10); ax.legend(fontsize=7, ncol=2, frameon=False)
    fig.tight_layout(); fig.savefig(os.path.join(a.out, 'profile.png'), dpi=110); plt.close(fig)
except Exception as e:
    print('no profile plot:', e)
print('written to', a.out)
