"""Score our ink maps on a known-text control against a reference (2.4 um prediction map or human labels).
For each model, depth and side: AUC and Pearson r against the reference resized onto the map grid, after a global shift
found by maximising r for the strongest map (search +-14 px). Also the mean-z ensemble of the given model groups.
Valid pixels (2026-10-21): the render's CT (conventions.ct_valid, eroded 31 px), no longer where any map is > 0, which leaves out
quiet papyrus and made the other face look more ink-like (on PHerc0841 ag2814 its AUCs fell ~0.05, the reading face's moved < 0.025);
AUC with average ranks for ties (conventions.auc; uint8 maps tie heavily).
Usage: control_eval.py <maps dir> <name> <reference.tif | labels.zarr> --render <66-layer zarr> [--mask mask.zarr] [--thr 128] [--out prefix]"""
import glob, os, re, sys, json, numpy as np, tifffile, cv2, zarr
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(HERE, '..', 'common')]   # GPU machine: bin/conventions.py
import conventions as C
args = sys.argv[1:]
def opt(k, d=None):
    if k in args: i = args.index(k); v = args[i + 1]; del args[i:i + 2]; return v
    return d
maskp, thr, outp, renderp = opt('--mask'), float(opt('--thr', '128')), opt('--out'), opt('--render')
if not renderp: sys.exit('--render <66-layer zarr> is needed: valid pixels come from its CT')
mdir, name, refp = args
def load2d(p):
    if p.endswith('.zarr'): return np.asarray(zarr.open(p, mode='r')['0'])
    return tifffile.imread(p)
maps = {}
for f in sorted(glob.glob(f'{mdir}/{name}__*__L66s*.tif')):
    m = re.match(r'.*__(.+?)__L66s(\d+)(_reverse)?\.tif$', f); model, s, rev = m.group(1), int(m.group(2)), bool(m.group(3))
    maps[(model, s - 25, 'reading' if rev else 'blind')] = f
if not maps: sys.exit(f'no maps for {name} in {mdir}')
H, W = tifffile.imread(next(iter(maps.values()))).shape
ref = cv2.resize(load2d(refp).astype(np.float32), (W, H), interpolation=cv2.INTER_AREA)
msk = cv2.resize(load2d(maskp).astype(np.float32), (W, H), interpolation=cv2.INTER_NEAREST) > 0 if maskp else None
def shift(a, dy, dx):
    out = np.zeros_like(a); ys, yd = (slice(dy, None), slice(0, H - dy)) if dy >= 0 else (slice(0, H + dy), slice(-dy, None))
    xs, xd = (slice(dx, None), slice(0, W - dx)) if dx >= 0 else (slice(0, W + dx), slice(-dx, None))
    out[ys, xs] = a[yd, xd]; return out
def auc(score, pos, valid):
    P, N = pos & valid, ~pos & valid
    if not P.any() or not N.any(): return float('nan')
    return C.auc(score[P], score[N])
def corr(a, b, v): return float(np.corrcoef(a[v], b[v])[0, 1])
arr = {k: tifffile.imread(f).astype(np.float32) for k, f in maps.items()}
valid0 = C.resize_mask(C.ct_valid(zarr.open(renderp, mode='r')['0']), (H, W))
valid0 = cv2.erode(valid0.astype(np.uint8), np.ones((31, 31), np.uint8)) > 0
# shift search on a 4x downsampled grid with the map that correlates best unshifted
best_key = max(arr, key=lambda k: corr(arr[k], ref, valid0 & (ref > 0)))
a4, r4, v4 = (cv2.resize(x.astype(np.float32), (W // 4, H // 4), interpolation=cv2.INTER_AREA) for x in (arr[best_key], ref, valid0.astype(np.float32)))
bs = max(((dy, dx) for dy in range(-4, 5) for dx in range(-4, 5)),
         key=lambda t: np.corrcoef(a4[v4 > 0.99], np.roll(np.roll(r4, t[0], 0), t[1], 1)[v4 > 0.99])[0, 1])
cands = [(4 * bs[0] + dy, 4 * bs[1] + dx) for dy in range(-3, 4) for dx in range(-3, 4)]
dy, dx = max(cands, key=lambda t: corr(arr[best_key], shift(ref, *t), valid0))
ref_s = shift(ref, dy, dx); valid = valid0 & (ref_s >= 0)
if msk is not None: valid &= shift(msk.astype(np.float32), dy, dx) > 0
pos = ref_s >= thr
print(f'{name}: map grid {H}x{W}; reference {refp.split("/")[-1]}; shift (dy,dx)=({dy},{dx}) px found with {best_key}; '
      f'positives {pos[valid].mean():.3f} of {valid.sum()} valid px' + (' (masked)' if msk is not None else ''))
rows = []
for k in sorted(arr):
    rows.append((k, auc(arr[k], pos, valid), corr(arr[k], ref_s, valid)))
# ensembles: mean of per-map z-scores (reading-side mean/std for both sides, as ensemble_maps.py does)
groups = {'ens3 (ink9-42, ink9-43, dnative)': ['hybrid_3d2d-seed42', 'hybrid_3d2d-seed43', 'dnative'],
          'ens3+readerv2': ['hybrid_3d2d-seed42', 'hybrid_3d2d-seed43', 'dnative', 'readerv2'],
          'readerv2+d9v4c': ['readerv2', 'd9v4c'], 'all5': ['hybrid_3d2d-seed42', 'hybrid_3d2d-seed43', 'dnative', 'readerv2', 'd9v4c']}
depths = sorted({k[1] for k in arr})
for g, ms in groups.items():
    for d in depths:
        if not all((m, d, 'reading') in arr and (m, d, 'blind') in arr for m in ms): continue
        for side in ('reading', 'blind'):
            zs = []
            for m in ms:
                rd = arr[(m, d, 'reading')]; mu, sd = rd[valid0].mean(), rd[valid0].std() + 1e-6
                zs.append((arr[(m, d, side)] - mu) / sd)
            e = np.mean(zs, 0); rows.append(((g, d, side), auc(e, pos, valid), corr(e, ref_s, valid)))
print(f'{"model":34s} {"d":>3s} {"side":8s} {"AUC":>6s} {"r":>6s}')
for (m, d, side), a, r in rows: print(f'{m:34s} {d:+3d} {side:8s} {a:6.3f} {r:6.3f}')
if outp:
    json.dump({'name': name, 'shift': [dy, dx], 'rows': [[list(map(str, k)), a, r] for k, a, r in rows]}, open(outp + '.json', 'w'), indent=1)
    np.save(outp + '_ref_shifted.npy', ref_s.astype(np.float16))
