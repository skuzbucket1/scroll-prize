import sys, numpy as np, tifffile, cv2
r0, r1, c0, c1 = 640, 1920, 2560, 3840
ref = tifffile.imread('/tmp/ctlkit/0139-w047/reference.tif'); s = ref.shape[0] / 5840.0
refw = cv2.resize(ref[int(r0 * s):int(r1 * s), int(c0 * s):int(c1 * s)].astype(np.float32), (c1 - c0, r1 - r0), interpolation=cv2.INTER_AREA)
meshw = tifffile.imread('/Users/tbienapfl/dev/vscode/scroll-prizes/data/controls9um/c0139_w047/maps/c0139_w047_66__readerv2__L66s26_reverse.tif')[r0:r1, c0:c1].astype(np.float32) / 255.
B = np.load(sys.argv[1]); cov = np.isfinite(B['d9v4c_forward'])
print(f'coverage {cov.mean():.3f}')
shifts = [(dy, dx) for dy in range(-480, 481, 120) for dx in range(-480, 481, 120) if max(abs(dy), abs(dx)) >= 240]
def test(img, name):
    al = np.corrcoef(img[cov], np.roll(np.roll(refw, -8, 0), -6, 1)[cov])[0, 1]
    nul = np.array([np.corrcoef(img[cov], np.roll(np.roll(refw, dy, 0), dx, 1)[cov])[0, 1] for dy, dx in shifts])
    print(f'{name:22s} aligned r {al:+.3f} | null (n={len(nul)}) mean {nul.mean():+.3f} sd {nul.std():.3f} max {nul.max():+.3f} | z {(al - nul.mean()) / nul.std():+.1f}')
test(meshw, 'MESH-BASED rv2 d+1')
for k in sorted(B.files):
    if k != 'shape': test(np.nan_to_num(B[k]), 'INK-FIRST ' + k)
