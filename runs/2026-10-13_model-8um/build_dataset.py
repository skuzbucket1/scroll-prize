"""Training set for an 8.64 µm ink model, first version (2026-10-13, Ted: "start the 8.64 model"): Erwin Nieuwlaar's
PHerc. 343 First Letters segment (his public concat mesh, our 66-layer render), in villa's flat ink-detection layout.

- surface-volume.zarr: render layers 65..1, REVERSED (65 planes; plane 32 = layer 33 = depth 0, the plane where villa's
  label zarrs put the flat label; flat training reads labels with the image's own depth window, centred there: 17
  planes with +-2 jitter, which reaches his letters' depth +1). Reversed because in our renders the written side is the
  one the models see in reverse layer order (the _reverse maps, which the labels come from); fed in stored order, the
  model would be taught that ink sits on the blind side. A 21-plane cut put the labels outside the window (first
  attempt: loss stuck at -0.25). Chunks of 8 planes, so a 17-plane window does not read all 65.
- inklabels: strokes inside his 18 letter boxes = the five-model reading-side ensemble at d +1 (ct_ink_signature.py's
  masks.npz) in the top 20 % of box pixels, specks under 60 px removed. These are pseudo-labels from the current
  models, checked by eye against his published image; the boxes come from his repository (inputs/*_letter_boxes.json).
- supervision_mask: the boxes, grown by 40 px. Nothing outside: the segment holds parts of four lines of text and only
  two are boxed, so unboxed papyrus may carry letters and must not be taught as "no ink".
- validation_mask: whole letters with box centre x > 3000 (raw render pixels; letters 1-6), training on those with
  centre x < 2600 (8-13, 15-18); 7 and 14 (centre x 2600..3000) are left out of both, so no 128 px patch sees training
  and validation letters at once.
Usage: build_dataset.py <out labels dir>   (writes <out>/pherc0343-nieuwlaar/)"""
import json, os, sys
import cv2, numpy as np, zarr

out = os.path.join(sys.argv[1], 'pherc0343-nieuwlaar'); os.makedirs(out, exist_ok=True)
S = os.path.expanduser('~/scroll-prizes')
R = zarr.open('/mnt/nvme/scroll-prizes/data/PHerc0343/control/control343_66.zarr', mode='r')['0']
vol = np.asarray(R[1:66])[::-1].copy(); print('surface volume (reversed)', vol.shape)
g = zarr.open_group(os.path.join(out, 'surface-volume.zarr'), mode='w', zarr_format=2)
g.create_array('0', shape=vol.shape, chunks=(8, 128, 128), dtype='u1', fill_value=0)[:] = vol
H, W = vol.shape[1:]; valid = (vol[23:44] > 0).all(0)
E = np.load(f'{S}/runs/2026-10-12_ct-ink-signature/masks.npz')['E'].astype(np.float32)
boxes = json.load(open(f'{S}/runs/2026-10-12_inkfirst-343/letter_boxes.json'))['letters']
inbox = np.zeros((H, W), bool); sup = np.zeros((H, W), bool); val = np.zeros((H, W), bool); split = {'train': [], 'val': [], 'gap': []}
for l in boxes:
    x0, y0, x1, y1 = (int(round(v)) for v in l['box']); cx = (x0 + x1) / 2
    part = 'train' if cx < 2600 else 'gap' if cx < 3000 else 'val'; split[part].append(l['id'])
    inbox[max(0, y0):y1, max(0, x0):x1] = True
    if part == 'gap':
        continue
    sup[max(0, y0 - 40):y1 + 40, max(0, x0 - 40):x1 + 40] = True
    if part == 'val':
        val[max(0, y0 - 40):y1 + 40, max(0, x0 - 40):x1 + 40] = True
inbox &= valid; sup &= valid; val &= valid
thr = np.percentile(E[inbox], 80)
ink = (E >= thr) & inbox
n, lab, st, _ = cv2.connectedComponentsWithStats(ink.astype(np.uint8), connectivity=8)
ink = np.isin(lab, np.nonzero(st[:, cv2.CC_STAT_AREA] >= 60)[0][1:]) & ink
for name, m in (('inklabels', ink), ('supervision_mask', sup), ('validation_mask', val)):
    cv2.imwrite(os.path.join(out, f'pherc0343-nieuwlaar_{name}.png'), (m * 255).astype(np.uint8))
print('letters: train', split['train'], 'val', split['val'], 'left out', split['gap'])
print(f'ink px {int(ink.sum())} ({ink[sup].mean():.1%} of supervised); supervised {int(sup.sum())}, validation {int(val.sum())}')
prev = cv2.resize(np.dstack([ink * 255, sup * 120, val * 200]).astype(np.uint8), (W // 4, H // 4), interpolation=cv2.INTER_AREA)
cv2.imwrite(os.path.join(sys.argv[1], 'pherc0343-nieuwlaar_labels_preview.png'), cv2.rotate(prev, cv2.ROTATE_180))
