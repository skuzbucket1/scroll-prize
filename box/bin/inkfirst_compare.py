"""Ink-first vs mesh-based vs known text on the w047 window (grid rows 32-96, cols 128-192 = full-res rows 640-1920, cols 2560-3840)."""
import numpy as np, tifffile, cv2, sys
r0, r1, c0, c1 = 640, 1920, 2560, 3840
ref = tifffile.imread('/tmp/ctlkit/0139-w047/reference.tif'); s = ref.shape[0] / 5840.0
refw = cv2.resize(ref[int(r0 * s):int(r1 * s), int(c0 * s):int(c1 * s)].astype(np.float32), (c1 - c0, r1 - r0), interpolation=cv2.INTER_AREA)
M = '/Users/tbienapfl/dev/vscode/scroll-prizes/data/controls9um/c0139_w047/maps'
mesh_rv2 = tifffile.imread(f'{M}/c0139_w047_66__readerv2__L66s26_reverse.tif')
print('mesh-based map shape', mesh_rv2.shape)
meshw = mesh_rv2[r0:r1, c0:c1].astype(np.float32) / 255.
B = np.load(sys.argv[1])
def auc(score, pos, ok):
    sc, p = score[ok], pos[ok]; n1 = p.sum(); n0 = p.size - n1
    rk = np.argsort(np.argsort(sc, kind='stable'), kind='stable') + 1.0
    return (rk[p].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)
def best_shift(img, ref, ok):
    best = (-2, 0, 0)
    for dy in range(-16, 17, 2):
        for dx in range(-16, 17, 2):
            rs = np.roll(np.roll(ref, dy, 0), dx, 1); m = ok & np.isfinite(img)
            c = np.corrcoef(np.nan_to_num(img[m]), rs[m])[0, 1]
            if c > best[0]: best = (c, dy, dx)
    return best
ok = np.ones_like(refw, bool); ok[:20] = ok[-20:] = False; ok[:, :20] = ok[:, -20:] = False
cm, dym, dxm = best_shift(meshw, refw, ok); refm = np.roll(np.roll(refw, dym, 0), dxm, 1)
print(f'mesh-based Reader v2 d+1: r {cm:.3f} (shift {dym},{dxm}), AUC {auc(meshw, refm >= 128, ok):.3f}')
panels = [('KNOWN TEXT reference (78 keV, 2.4 um)', refw / 255.), ('MESH-BASED Reader v2, d+1 (our usual pipeline)', meshw)]
for k in sorted(B.files):
    if k == 'shape': continue
    img = B[k]; cov = np.isfinite(img)
    c, dy, dx = best_shift(img, refw, ok & cov); rs = np.roll(np.roll(refw, dy, 0), dx, 1)
    m = ok & cov
    print(f'INK-FIRST {k}: coverage {cov.mean():.3f}, r {c:.3f} (shift {dy},{dx}), AUC {auc(np.nan_to_num(img), rs >= 128, m):.3f}')
    panels.append((f'INK-FIRST (no mesh) {k}', np.nan_to_num(img)))
WD = 640; rows = []
for t, im in panels:
    v = np.clip(im / max(np.percentile(im, 99.5), 1e-3), 0, 1) if 'KNOWN' not in t else np.clip(im, 0, 1)
    a = cv2.resize((v * 255).astype(np.uint8), (WD, WD), interpolation=cv2.INTER_AREA)
    c = np.zeros((WD + 24, WD), np.uint8); c[24:] = a; cv2.putText(c, t, (4, 17), cv2.FONT_HERSHEY_SIMPLEX, 0.42, 255, 1, cv2.LINE_AA); rows.append(c)
while len(rows) % 3: rows.append(np.zeros_like(rows[0]))
grid = np.concatenate([np.concatenate(rows[i:i + 3], 1) for i in range(0, len(rows), 3)], 0)
cv2.imwrite('/tmp/inkfirst/compare_r8.jpg', grid, [cv2.IMWRITE_JPEG_QUALITY, 88]); print(grid.shape)
