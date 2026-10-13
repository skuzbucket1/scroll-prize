"""Letter tiles for model_agreement.py from human ink labels (2026-10-13). First version took the label's connected
components as boxes, but PHerc0841's labels merge into a few big blobs (5 on ag2814), unlike Nieuwlaar's 18 letter boxes
on PHerc. 343. Now: a grid of letter-sized tiles (`tile` px, 300 = 2.8 mm at 9.366 µm) over the supervision mask; a tile
is a 'letter' box when at least `min_cov` of it is labelled ink (default 0.15); tiles wholly inside the mask with no
label at all go to <out>.bare.json (model_agreement.py --bare: known bare papyrus). Also writes <out>.sup.png (the supervision mask on the render grid). No shift correction
(control_eval.py finds at most 14 px, small next to a 300 px tile).
Reference mode (PHerc0139 w047, no human labels): `label_boxes.py <reference.tif> - <render.zarr> <um> <out.json>` takes the
2.4 µm ink prediction instead, binarised at half its maximum, over the whole render.
Usage: label_boxes.py <labels.zarr|reference.tif> <supervision.zarr|-> <render.zarr> <um> <out.json> [--tile 300] [--min-cov 0.15]"""
import json, sys
import cv2, numpy as np, zarr

args = sys.argv[1:]
def opt(k, d):
    if k in args:
        i = args.index(k); v = args[i + 1]; del args[i:i + 2]; return v
    return d
tile, min_cov = int(opt('--tile', '300')), float(opt('--min-cov', '0.15'))
labp, supp, rp, um, out = args[0], args[1], args[2], float(args[3]), args[4]
H, W = zarr.open(rp, mode='r')['0'].shape[1:]
if labp.endswith('.tif'):
    import tifffile
    L = cv2.resize(tifffile.imread(labp).astype(np.float32), (W, H), interpolation=cv2.INTER_AREA); sup = np.ones((H, W), bool)
else:
    L = cv2.resize(np.asarray(zarr.open(labp, mode='r')['0']).astype(np.float32), (W, H), interpolation=cv2.INTER_AREA)
    sup = cv2.resize(np.asarray(zarr.open(supp, mode='r')['0']).astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST) > 0
L = (L / max(float(L.max()), 1e-6) > 0.5) & sup
letters = []; bare = []
for y in range(0, H - tile + 1, tile):
    for x in range(0, W - tile + 1, tile):
        s = sup[y:y + tile, x:x + tile]
        if s.mean() < 0.8:
            continue
        cov = float(L[y:y + tile, x:x + tile].mean())
        if cov >= min_cov:
            letters.append(dict(id=len(letters) + 1, label=str(len(letters) + 1), row='', box=[x, y, x + tile, y + tile], cov=round(cov, 3)))
        elif cov == 0 and s.all():
            bare.append(dict(id=len(bare) + 1, label=str(len(bare) + 1), row='', box=[x, y, x + tile, y + tile], cov=0.0))
json.dump(dict(note=f'{tile} px grid tiles over the supervision mask with at least {min_cov:.0%} human-labelled ink (label_boxes.py)',
               frame='render pixels', letters=letters), open(out, 'w'), indent=1)
json.dump(dict(note=f'{tile} px grid tiles wholly inside the supervision mask with no labelled ink (label_boxes.py)', frame='render pixels',
               letters=bare), open(out.replace('.json', '.bare.json'), 'w'), indent=1)
cv2.imwrite(out.replace('.json', '.sup.png'), sup.astype(np.uint8) * 255)
print(f'{out}: {len(letters)} letter tiles and {len(bare)} bare tiles of {tile} px (cov >= {min_cov}); supervised {int(sup.sum())} px, labelled {int(L.sum())} px')
