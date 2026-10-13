"""Does the 8.64 µm fine-tune see letters it never trained on better than the model it started from, without lighting up
more papyrus? (2026-10-13)
1. Held-out letters: on Nieuwlaar's PHerc. 343 segment, reading-side map at d +1 (villa infer, layers 26..42, reverse =
   reading side, as run_ink.sh does) for each checkpoint; AUC of the map against the stroke labels inside the validation
   boxes (letters 1-6) and inside the training boxes (8-13, 15-18, for overfitting), and the mean map on strokes minus
   the mean on the papyrus between them.
2. False alarms: the same checkpoints on the six clean 9.362 µm crops of the agreement test and on PHerc0813 w079's crop
   (d +1): share of the window at map >= 0.5 on the reading side and on the blind side.
3. Picture: the validation letters, reading orientation, original next to fine-tuned, boxes outlined.
The starting model's maps are recomputed the same way, so both sides of every comparison are inked identically.
Usage: eval_8um.py <out dir> name=checkpoint.pth [name=checkpoint.pth ...]"""
import glob, json, os, subprocess, sys
import cv2, numpy as np, tifffile

S = os.path.expanduser('~/scroll-prizes'); PY = f'{S}/villa/vesuvius/.venv/bin/python'
out = sys.argv[1]; os.makedirs(out, exist_ok=True)
cks = dict(a.split('=', 1) for a in sys.argv[2:])
R343 = '/mnt/nvme/scroll-prizes/data/PHerc0343/control/control343_66.zarr'
LAB = '/mnt/nvme/scroll-prizes/data/train8um/labels/pherc0343-nieuwlaar/pherc0343-nieuwlaar'
NULLS = sorted(glob.glob(f'{S}/runs/2026-10-12_agreement-null/PHerc*_null.zarr')) + [f'{S}/runs/2026-10-12_deeplook-0813-w079/w079crop.zarr']


def l0(z):
    """A level-0-only view of a multi-level render (as run_ink.sh does), so villa scans at full resolution."""
    if os.path.isdir(os.path.join(z, '1')):
        v = os.path.join(out, 'l0', os.path.basename(z)); os.makedirs(v, exist_ok=True)
        open(os.path.join(v, '.zgroup'), 'w').write('{"zarr_format": 2}')
        if not os.path.exists(os.path.join(v, '0')):
            os.symlink(os.path.join(z, '0'), os.path.join(v, '0'))
        return v
    return z


def infer(z, name, ck, s=26):
    o = os.path.join(out, 'maps', f'{os.path.basename(z)[:-5]}__{name}__L66s{s}.tif')
    if not (os.path.exists(o) and os.path.exists(o.replace('.tif', '_reverse.tif'))):
        os.makedirs(os.path.dirname(o), exist_ok=True)
        subprocess.run([PY, '-m', 'vesuvius.ink_detection.inference.infer', l0(z), ck, o, '--overlap', '0.5', '--blend-mode', 'hann',
                        '--batch-size', '8', '--direction', 'both', '--layer-start', str(s), '--layer-end', str(s + 17), '--amp-dtype', 'fp16'],
                       cwd=f'{S}/villa/vesuvius', check=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    rd = np.clip((tifffile.imread(o.replace('.tif', '_reverse.tif')).astype(np.float32) - 64) / 128, 0, 1)
    bl = np.clip((tifffile.imread(o).astype(np.float32) - 64) / 128, 0, 1)
    return rd, bl


def auc(pos, neg):
    x = np.concatenate([pos, neg]); r = x.argsort().argsort().astype(np.float64)
    return (r[:len(pos)].sum() - len(pos) * (len(pos) - 1) / 2) / (len(pos) * len(neg))


ink = cv2.imread(f'{LAB}_inklabels.png', 0) > 0; sup = cv2.imread(f'{LAB}_supervision_mask.png', 0) > 0
val = cv2.imread(f'{LAB}_validation_mask.png', 0) > 0; trn = sup & ~val
rows, maps343 = [], {}
for name, ck in cks.items():
    rd, bl = infer(R343, name, ck); maps343[name] = rd
    res = {'model': name}
    for part, m in (('validation letters', val), ('training letters', trn)):
        p, n = rd[m & ink], rd[m & ~ink]; rng = np.random.default_rng(0)
        p = rng.choice(p, min(len(p), 200000), replace=False); n = rng.choice(n, min(len(n), 400000), replace=False)
        res[f'AUC {part}'] = round(float(auc(p, n)), 4); res[f'stroke - papyrus {part}'] = round(float(p.mean() - n.mean()), 4)
    for z in NULLS:
        nm = os.path.basename(z)[:-5]; rdn, bln = infer(z, name, ck)
        v = rdn > 0; win = np.zeros_like(v); win[256:256 + 854, 256:256 + 1495] = True
        if os.path.exists(z.replace('.zarr', '.window')):
            y, x, h, w = map(int, open(z.replace('.zarr', '.window')).read().split()); win[:] = False; win[y:y + h, x:x + w] = True
        m = v & win
        res[f'{nm} reading >= 0.5'] = round(float((rdn[m] >= 0.5).mean()), 4); res[f'{nm} blind >= 0.5'] = round(float((bln[m] >= 0.5).mean()), 4)
    rows.append(res); print(json.dumps(res), flush=True)
json.dump(rows, open(os.path.join(out, 'eval.json'), 'w'), indent=1)
# picture of the validation letters
ys, xs = np.nonzero(val); y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
panels = []
for name, rd in maps343.items():
    c = (np.clip(rd[y0:y1, x0:x1], 0, 1) * 255).astype(np.uint8); c = cv2.cvtColor(c, cv2.COLOR_GRAY2BGR)
    cnt, _ = cv2.findContours(val[y0:y1, x0:x1].astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(c, cnt, -1, (60, 160, 255), 2); c = cv2.rotate(c, cv2.ROTATE_180)
    c = cv2.resize(c, (c.shape[1] // 2, c.shape[0] // 2), interpolation=cv2.INTER_AREA)
    cv2.putText(c, f'{name}: held-out letters 1-6, reading side, d +1', (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
    panels.append(cv2.copyMakeBorder(c, 3, 3, 3, 3, cv2.BORDER_CONSTANT, value=(22, 22, 22)))
cv2.imwrite(os.path.join(out, 'heldout_letters.jpg'), np.concatenate(panels, 0), [cv2.IMWRITE_JPEG_QUALITY, 90])
print('written', out)
