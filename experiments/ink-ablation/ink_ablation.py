"""What do the ink models respond to on real 9.36 µm letters? (2026-10-13, idea 2 step 1; the de-weave test showed it is
not brightness: PHerc0841's human-labelled ink is no brighter than bare papyrus at any depth, yet the models read it at
AUC 0.82-0.86.) On a 66-layer control render with human labels, run one model (villa infer, both directions, the 17
layers s..s+16 as the search does) on variants of the render and score the reading-side map against the labels inside the
supervision mask (AUC, labels shifted by the offset found earlier):
  baseline        the render as it is
  flat L0-L1      the stored layers L0..L1 of the 17 replaced by their own mean over the papyrus (which depths carry
                  the signal; the written face sits near stored layer 33-34 at d +1)
  highpass 0.5mm  every layer minus its local mean (Gaussian 0.5 mm) plus the global mean: pattern kept, slow
                  brightness removed
  shuffle 8px     pixels shuffled inside 8 x 8 px blocks (0.075 mm): fine weave texture destroyed, stroke-scale
                  brightness kept
  shuffle 32px    shuffled inside 32 x 32 px blocks (0.3 mm, a stroke width): stroke shapes destroyed too
A variant whose AUC stays near the baseline did not remove what the model uses; one that drops to 0.5 did.
Usage: ink_ablation.py <render.zarr> <labels.zarr> <sup.zarr> <um> <dy> <dx> <ckpt.pth> <scratch dir> <out.json> [--s 26] [--batch 8]"""
import json, os, shutil, subprocess, sys
import cv2, numpy as np, tifffile, zarr

args = sys.argv[1:]
def opt(k, d):
    if k in args:
        i = args.index(k); v = args[i + 1]; del args[i:i + 2]; return v
    return d
s0, batch = int(opt('--s', '26')), opt('--batch', '8')
rp, lp, sp, um, dy, dx, ckpt, scratch, outp = args[0], args[1], args[2], float(args[3]), int(args[4]), int(args[5]), args[6], args[7], args[8]
S = os.path.expanduser('~/scroll-prizes'); PY = f'{S}/villa/vesuvius/.venv/bin/python'
os.makedirs(scratch, exist_ok=True)
R = zarr.open(rp, mode='r')['0']; NL, H, W = R.shape
base = np.asarray(R[:]); valid = (base[s0:s0 + 17] > 0).all(0)
L = cv2.resize(np.asarray(zarr.open(lp, mode='r')['0']).astype(np.float32), (W, H), interpolation=cv2.INTER_AREA)
L = np.roll(L / max(float(L.max()), 1e-6) > 0.5, (dy, dx), (0, 1))
sup = np.roll(cv2.resize(np.asarray(zarr.open(sp, mode='r')['0']).astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST) > 0, (dy, dx), (0, 1))
pos, neg = L & sup & valid, ~L & sup & valid
neg &= cv2.erode(neg.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
rng = np.random.default_rng(0); ip = rng.choice(np.flatnonzero(pos), min(int(pos.sum()), 150000), replace=False)
im = rng.choice(np.flatnonzero(neg), min(int(neg.sum()), 300000), replace=False)


def auc(x):
    p, n = x.ravel()[ip], x.ravel()[im]; r = np.concatenate([p, n]).argsort().argsort().astype(np.float64)
    return float((r[:len(p)].sum() - len(p) * (len(p) - 1) / 2) / (len(p) * len(n)))


def shuffle_blocks(a, b):
    """Shuffle the pixels of each b x b block of every layer (same permutation for all layers of a block? No: per layer,
    so that no cross-layer structure survives either), inside the valid area only."""
    out = a.copy(); Hh, Ww = (H // b) * b, (W // b) * b
    for k in range(a.shape[0]):
        v = a[k, :Hh, :Ww].reshape(Hh // b, b, Ww // b, b).transpose(0, 2, 1, 3).reshape(-1, b * b)
        idx = np.argsort(rng.random(v.shape), axis=1); v = np.take_along_axis(v, idx, axis=1)
        out[k, :Hh, :Ww] = v.reshape(Hh // b, Ww // b, b, b).transpose(0, 2, 1, 3).reshape(Hh, Ww)
    out[:, ~valid] = a[:, ~valid]
    return out


def variants():
    win = base[s0:s0 + 17]
    yield 'baseline', None
    for a, b in ((0, 3), (4, 6), (7, 9), (10, 12), (13, 16)):
        v = win.copy()
        for k in range(a, b + 1):
            m = v[k][valid].mean(); v[k][valid] = np.uint8(round(float(m)))
        yield f'flat L{s0 + a}-{s0 + b}', v
    v = win.astype(np.float32); sig = 500 / um
    for k in range(17):
        lm = cv2.GaussianBlur(v[k], (0, 0), sig); v[k] = v[k] - lm + v[k][valid].mean()
    v = np.clip(np.round(v), 1, 255).astype(np.uint8); v[:, ~valid] = win[:, ~valid]
    yield 'highpass 0.5mm', v
    yield 'shuffle 8px', shuffle_blocks(win, 8)
    yield 'shuffle 32px', shuffle_blocks(win, 32)


res = []
for name, v in variants():
    tag = name.replace(' ', '_').replace('.', 'p')
    z = os.path.join(scratch, f'{tag}.zarr'); o = os.path.join(scratch, f'{tag}.tif')
    if v is None:
        zp = rp if not os.path.isdir(os.path.join(rp, '1')) else None
        if zp is None:                                                      # level-0 view of a multi-level render
            os.makedirs(z, exist_ok=True); open(os.path.join(z, '.zgroup'), 'w').write('{"zarr_format": 2}')
            if not os.path.exists(os.path.join(z, '0')):
                os.symlink(os.path.join(rp, '0'), os.path.join(z, '0'))
            zp = z
    else:
        arr = base.copy(); arr[s0:s0 + 17] = v
        g = zarr.open_group(z, mode='w', zarr_format=2); g.create_array('0', shape=arr.shape, chunks=(66, 256, 256), dtype='u1', fill_value=0)[:] = arr
        zp = z
    subprocess.run([PY, '-m', 'vesuvius.ink_detection.inference.infer', zp, ckpt, o, '--overlap', '0.5', '--blend-mode', 'hann', '--batch-size', batch,
                    '--direction', 'both', '--layer-start', str(s0), '--layer-end', str(s0 + 17), '--amp-dtype', 'fp16'],
                   cwd=f'{S}/villa/vesuvius', check=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    rd = tifffile.imread(o.replace('.tif', '_reverse.tif')).astype(np.float32); bl = tifffile.imread(o).astype(np.float32)
    r = dict(variant=name, auc_reading=round(auc(rd), 4), auc_blind=round(auc(bl), 4),
             mean_reading_ink=round(float(np.clip((rd.ravel()[ip] - 64) / 128, 0, 1).mean()), 4),
             mean_reading_bare=round(float(np.clip((rd.ravel()[im] - 64) / 128, 0, 1).mean()), 4))
    res.append(r); print(json.dumps(r), flush=True)
    if v is not None:
        shutil.rmtree(z, ignore_errors=True)
json.dump(res, open(outp, 'w'), indent=1); print('written', outp)
