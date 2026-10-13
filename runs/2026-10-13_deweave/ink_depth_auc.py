"""Is 0841's ink brighter in the raw CT at any depth? (2026-10-13, follow-up to deweave.py: d 0..+4 showed AUC 0.49-0.52
while the ink models reach 0.82-0.86.) Per layer 33+d, d = -12..+12: AUC of the CT (Gaussian 0.05 mm) for human-labelled
ink against unlabelled papyrus inside the supervision mask (labels shifted as in deweave.py), plus the local contrast
(SD of the CT in a 0.2 mm window) as a texture cue. Usage: ink_depth_auc.py <render.zarr> <labels.zarr> <sup.zarr> <um> <dy> <dx>"""
import sys
import cv2, numpy as np, zarr
rp, lp, sp, um, dy, dx = sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4]), int(sys.argv[5]), int(sys.argv[6])
R = zarr.open(rp, mode='r')['0']; H, W = R.shape[1:]
ct = np.asarray(R[33 - 12:33 + 13]).astype(np.float32); valid = (ct > 0).all(0)
L = cv2.resize(np.asarray(zarr.open(lp, mode='r')['0']).astype(np.float32), (W, H), interpolation=cv2.INTER_AREA)
L = np.roll(L / max(float(L.max()), 1e-6) > 0.5, (dy, dx), (0, 1))
S = np.roll(cv2.resize(np.asarray(zarr.open(sp, mode='r')['0']).astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST) > 0, (dy, dx), (0, 1))
pos, neg = L & S & valid, ~L & S & valid
neg &= cv2.erode(neg.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
rng = np.random.default_rng(0); ip = rng.choice(np.flatnonzero(pos), min(int(pos.sum()), 150000), replace=False)
im = rng.choice(np.flatnonzero(neg), min(int(neg.sum()), 300000), replace=False)
def auc(x):
    p, n = x.ravel()[ip], x.ravel()[im]; r = np.concatenate([p, n]).argsort().argsort().astype(np.float64)
    return (r[:len(p)].sum() - len(p) * (len(p) - 1) / 2) / (len(p) * len(n))
k = max(3, int(round(200 / um)) | 1)
print('d   AUC(CT)  AUC(local SD)  mean CT ink - bare')
for i, d in enumerate(range(-12, 13)):
    c = ct[i]; g = cv2.GaussianBlur(c, (0, 0), 50 / um)
    m = cv2.blur(c, (k, k)); sd = np.sqrt(np.maximum(cv2.blur(c * c, (k, k)) - m * m, 0))
    print(f'{d:+3d}  {auc(g):.3f}    {auc(sd):.3f}         {c.ravel()[ip].mean() - c.ravel()[im].mean():+6.2f}')
