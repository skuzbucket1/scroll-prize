"""Is there an ink signal in the raw CT itself, with no model? On a segment with known letters (PHerc. 343: Nieuwlaar's
letter boxes), compare the CT brightness profile along the normal (layers 33+d, d = -12..+12 of the 66-layer render):
  stroke   inside a letter box, where the models' reading-side ensemble is in the top 20 % of the box pixels
  box bg   inside a letter box, ensemble in the bottom half (the papyrus between the strokes)
  outside  on the segment, more than `gap` pixels from any box (may hold unboxed writing)
Profiles are raw means and "shape" means (each pixel's profile minus its own mean over the depths, so overall brightness
differences between places drop out). Partial-volume check: the same stroke - box bg difference split by where the
surface falls inside a voxel (the fractional coordinate along the normal's main axis, for pixels whose normal is within
~37 degrees of an axis). The model ensemble only picks which pixels are strokes; every number here is CT.
Writes <out>/profile.tsv, profile.png, phase.tsv.
Usage: ct_ink_signature.py <render.zarr> <maps dir> <name> <letter_boxes.json> <mesh.tifxyz> <out dir>
       [--models readerv2,d9v4c,dnative,hybrid_3d2d-seed42,hybrid_3d2d-seed43] [--s 26] [--gap 150]"""
import argparse, json, os
import cv2, numpy as np, tifffile, zarr

ap = argparse.ArgumentParser()
for k in ('render', 'maps', 'name', 'boxes', 'mesh', 'out'):
    ap.add_argument(k)
ap.add_argument('--models', default='readerv2,d9v4c,dnative,hybrid_3d2d-seed42,hybrid_3d2d-seed43'); ap.add_argument('--s', type=int, default=26)
ap.add_argument('--gap', type=int, default=150)
a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
D = np.arange(-12, 13)
R = zarr.open(a.render, mode='r')['0']; H, W = R.shape[1:]
ct = np.stack([np.asarray(R[33 + d]) for d in D]).astype(np.float32)           # (25, H, W)
valid = (ct > 0).all(0)
# reading-side ensemble at the letters' depth (only used to pick stroke pixels)
E = np.zeros((H, W), np.float32); n = 0
for m in a.models.split(','):
    f = os.path.join(a.maps, f'{a.name}__{m}__L66s{a.s}_reverse.tif')
    if not os.path.exists(f):
        continue
    p = np.clip((tifffile.imread(f).astype(np.float32) - 64) / 128, 0, 1); mu, sd = p[valid].mean(), p[valid].std() or 1
    E += (p - mu) / sd; n += 1
E /= max(n, 1)
boxes = np.array([l['box'] for l in json.load(open(a.boxes))['letters']]).round().astype(int)
inbox = np.zeros((H, W), bool); near = np.zeros((H, W), bool)
for x0, y0, x1, y1 in boxes:
    inbox[max(0, y0):y1, max(0, x0):x1] = True
    near[max(0, y0 - a.gap):y1 + a.gap, max(0, x0 - a.gap):x1 + a.gap] = True
inbox &= valid
q80, q50 = np.percentile(E[inbox], [80, 50])
cls = {'stroke': inbox & (E >= q80), 'box bg': inbox & (E < q50), 'outside': valid & ~near}
shape = ct - ct.mean(0, keepdims=True)
rows = []
for k, msk in cls.items():
    rows.append((k, int(msk.sum()), ct[:, msk].mean(1), shape[:, msk].mean(1), shape[:, msk].std(1) / np.sqrt(msk.sum())))
with open(os.path.join(a.out, 'profile.tsv'), 'w') as fo:
    fo.write('class\tpixels\t' + '\t'.join(f'raw_d{d:+d}' for d in D) + '\t' + '\t'.join(f'shape_d{d:+d}' for d in D) + '\n')
    for k, npx, raw, shp, _ in rows:
        fo.write(f'{k}\t{npx}\t' + '\t'.join(f'{v:.2f}' for v in raw) + '\t' + '\t'.join(f'{v:.2f}' for v in shp) + '\n')
diff = rows[0][3] - rows[1][3]
print(f'{n} models for the stroke mask; pixels: ' + ', '.join(f'{k} {npx}' for k, npx, *_ in rows))
print('raw CT, stroke - box bg by depth: ' + ' '.join(f'{d:+d}:{v:+.1f}' for d, v in zip(D, rows[0][2] - rows[1][2])))
print('shape, stroke - box bg by depth:  ' + ' '.join(f'{d:+d}:{v:+.1f}' for d, v in zip(D, diff)))
# partial volume: split by the surface's position inside the voxel (layer 33 sample point) along the normal's main axis
X, Y, Z = (tifffile.imread(os.path.join(a.mesh, f'{c}.tif')).astype(np.float32) for c in 'xyz')
sc = json.load(open(os.path.join(a.mesh, 'meta.json')))['scale'][0]
ok = (X >= 0) & (Y >= 0) & (Z >= 0)
P = np.stack([Z, Y, X], -1); du = np.gradient(P, axis=1); dv = np.gradient(P, axis=0); N = np.cross(dv, du)
N /= np.linalg.norm(N, axis=-1, keepdims=True) + 1e-9
up = lambda A: cv2.resize(A, (W, H), interpolation=cv2.INTER_LINEAR)
Pp = np.stack([up(P[..., i]) for i in range(3)], -1); Np = np.stack([up(N[..., i]) for i in range(3)], -1)
okp = cv2.resize(ok.astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST).astype(bool)
ax = np.abs(Np).argmax(-1); main = np.take_along_axis(np.abs(Np), ax[..., None], -1)[..., 0]
phase = np.take_along_axis(Pp, ax[..., None], -1)[..., 0] % 1.0
use = okp & (main > 0.8)
with open(os.path.join(a.out, 'phase.tsv'), 'w') as fo:
    fo.write('phase_bin\tstroke_px\tboxbg_px\tshape_diff_d0\tshape_diff_d+1\tshape_diff_d+2\n')
    line = []
    for b in range(4):
        sel = use & (phase >= b / 4) & (phase < (b + 1) / 4)
        s1, s0 = cls['stroke'] & sel, cls['box bg'] & sel
        if s1.sum() < 200 or s0.sum() < 200:
            continue
        dd = shape[:, s1].mean(1) - shape[:, s0].mean(1); i0 = list(D).index(0)
        fo.write(f'{b / 4:.2f}-{(b + 1) / 4:.2f}\t{int(s1.sum())}\t{int(s0.sum())}\t{dd[i0]:+.2f}\t{dd[i0 + 1]:+.2f}\t{dd[i0 + 2]:+.2f}\n')
        line.append(f'{b / 4:.2f}-{(b + 1) / 4:.2f}: d0 {dd[i0]:+.1f}, d+1 {dd[i0 + 1]:+.1f}, d+2 {dd[i0 + 2]:+.1f} (n {int(s1.sum())})')
print(f'partial volume (stroke - box bg, shape), {int(use.sum())} px with an axis-aligned normal: ' + '; '.join(line))
try:
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    fig, axs = plt.subplots(1, 2, figsize=(11, 4))
    for k, npx, raw, shp, se in rows:
        axs[0].plot(D, raw, label=f'{k} ({npx} px)'); axs[1].errorbar(D, shp, yerr=2 * se, label=k, capsize=2)
    axs[0].set_title('raw CT along the normal', fontsize=10); axs[1].set_title("each pixel's profile minus its own mean (±2 SE)", fontsize=10)
    for x in axs:
        x.set_xlabel('depth d (layer - 33)'); x.axvline(0, color='#999', lw=0.7); x.legend(fontsize=8, frameon=False)
    axs[0].set_ylabel('CT value')
    fig.suptitle('PHerc. 343, Nieuwlaar\'s letters: is the ink in the raw CT?', fontsize=11); fig.tight_layout()
    fig.savefig(os.path.join(a.out, 'profile.png'), dpi=110); plt.close(fig)
except Exception as e:
    print('no plot:', e)
np.savez_compressed(os.path.join(a.out, 'masks.npz'), stroke=cls['stroke'], boxbg=cls['box bg'], outside=cls['outside'], E=E.astype(np.float16))
