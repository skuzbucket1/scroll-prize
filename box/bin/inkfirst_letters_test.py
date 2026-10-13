"""Does ink first see known letters? Maps every ink-first patch of a block back onto a known-text tifxyz segment and
compares the patches that land on the letters with the rest.
A patch is on the segment when its centre lies within `near` voxels of the mesh surface (dense samples every 4 render
pixels); its place on the render is that of the nearest sample. Classes: on a letter (centre inside a letter box), on
the segment away from the boxes (the boxes mark only the letters used for the claim; more text may be there), and
elsewhere in the block (other sheets). Per model and layer order: patches, mean ink, mean frac50 (share of the centre
at ink >= 0.5), share of hot patches (frac50 >= 0.5), and, on the segment, the correlation between the patch's mean ink
and the mesh pipeline's map of the same model over the same 1.1 mm footprint.
Writes <out>/letters_test.tsv and <out>/letters_<model>.jpg: the mesh pipeline's map of the same model on the segment
(reading side, reading orientation) with the letter boxes and the ink-first patch centres (squares of the 1.1 mm
centre, coloured by frac50), one panel per layer order.
Usage: inkfirst_letters_test.py <summary.npz> <letters3d.npz> <letter_boxes.json> <out dir> [--near 10]
       [--maps <dir of the segment's ink maps>] [--render control343_66] [--layer s26]"""
import argparse, json, os
import cv2, numpy as np, tifffile
from scipy.spatial import cKDTree

ap = argparse.ArgumentParser()
ap.add_argument('summary'); ap.add_argument('letters'); ap.add_argument('boxes'); ap.add_argument('out')
ap.add_argument('--near', type=float, default=10.0)
ap.add_argument('--maps', default='/mnt/nvme/scroll-prizes/data/PHerc0343/control/maps')
ap.add_argument('--render', default='control343_66'); ap.add_argument('--layer', default='s26')
a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
S = np.load(a.summary); Lz = np.load(a.letters)
Z, Y, X, V = Lz['mesh_z'], Lz['mesh_y'], Lz['mesh_x'], Lz['mesh_valid']; sr, sc = Lz['scale']
boxes = np.array([l['box'] for l in json.load(open(a.boxes))['letters']], np.float64)     # x0 y0 x1 y1 (render px)

# dense samples of the mesh, every 1/5 of a node (4 render px)
ok = V[:-1, :-1] & V[1:, :-1] & V[:-1, 1:] & V[1:, 1:]; rr, cc = np.nonzero(ok)
P, RC = [], []
for fi in np.arange(5) / 5:
    for fj in np.arange(5) / 5:
        w = [(1 - fi) * (1 - fj), (1 - fi) * fj, fi * (1 - fj), fi * fj]
        g = lambda G: w[0] * G[rr, cc] + w[1] * G[rr, cc + 1] + w[2] * G[rr + 1, cc] + w[3] * G[rr + 1, cc + 1]
        P.append(np.stack([g(Z), g(Y), g(X)], 1)); RC.append(np.stack([(rr + fi) / sr, (cc + fj) / sc], 1))
P, RC = np.concatenate(P), np.concatenate(RC)
dist, k = cKDTree(P).query(S['centre'].astype(np.float64))
row, col = RC[k, 0], RC[k, 1]
on = dist <= a.near
inbox = lambda r, c, m=0: ((c >= boxes[:, 0] - m) & (c <= boxes[:, 2] + m) & (r >= boxes[:, 1] - m) & (r <= boxes[:, 3] + m)).any()
letter = np.array([on[i] and inbox(row[i], col[i]) for i in range(len(on))])
cls = {'on a letter': letter, 'on the segment, outside the boxes': on & ~letter, 'elsewhere in the block': dist > 3 * a.near}
print(f'{len(on)} patches: {letter.sum()} on a letter, {(on & ~letter).sum()} elsewhere on the segment, {(dist > 3 * a.near).sum()} on other sheets '
      f'(distance to the segment: median {np.median(dist):.0f} vx)')
models = [str(m) for m in S['models']]
lines = ['model\torder\tclass\tpatches\tmean_ink\tmean_frac50\thot_share\tr_with_mesh_map']
figs = {}
for m in models:
    mp = os.path.join(a.maps, f'{a.render}__{m}__L66{a.layer}_reverse.tif')
    M = tifffile.imread(mp) if os.path.exists(mp) else None
    if M is not None:                                                   # mesh pipeline's reading-side map, per patch footprint
        mesh_ink = np.array([M[max(0, int(r) - 64):int(r) + 64, max(0, int(c) - 64):int(c) + 64].mean() / 255 if on[i] else np.nan
                             for i, (r, c) in enumerate(zip(row, col))])
    panels = []
    for o in ('fwd', 'rev'):
        key = f'stats_{m}_{o}'
        if key not in S.files:
            continue
        st = S[key]
        for name, sel in cls.items():
            n = int(sel.sum()); rv = ''
            if n:
                if M is not None and name != 'elsewhere in the block':
                    x, y = st[sel, 0], mesh_ink[sel]; good = np.isfinite(y)
                    rv = f'{np.corrcoef(x[good], y[good])[0, 1]:.2f}' if good.sum() > 3 and x[good].std() > 0 and y[good].std() > 0 else ''
                lines.append(f'{m}\t{o}\t{name}\t{n}\t{st[sel, 0].mean():.3f}\t{st[sel, 2].mean():.3f}\t{(st[sel, 2] >= 0.5).mean():.2f}\t{rv}')
        if M is not None:
            allon = on & np.isfinite(mesh_ink)
            r_all = np.corrcoef(st[allon, 0], mesh_ink[allon])[0, 1] if allon.sum() > 3 else np.nan
            lines.append(f'{m}\t{o}\tall on the segment\t{int(allon.sum())}\t{st[allon, 0].mean():.3f}\t{st[allon, 2].mean():.3f}\t{(st[allon, 2] >= 0.5).mean():.2f}\t{r_all:.2f}')
            # panel: mesh map (display stretch (v - 64) / 128), 1/4 size, boxes, patch squares
            f = 4; bg = np.clip((M[::f, ::f].astype(np.float32) - 64) / 128, 0, 1)
            pnl = cv2.cvtColor((bg * 170).astype(np.uint8), cv2.COLOR_GRAY2BGR)
            for x0, y0, x1, y1 in boxes:
                cv2.rectangle(pnl, (int(x0 / f), int(y0 / f)), (int(x1 / f), int(y1 / f)), (200, 200, 200), 1)
            cmap = cv2.applyColorMap(np.arange(256, dtype=np.uint8)[:, None], cv2.COLORMAP_INFERNO)[:, 0]
            for i in np.nonzero(on)[0][np.argsort(st[on, 2])]:
                col_ = tuple(int(v) for v in cmap[int(round(min(st[i, 2] / 0.8, 1) * 255))])
                cv2.rectangle(pnl, (int((col[i] - 64) / f), int((row[i] - 64) / f)), (int((col[i] + 64) / f), int((row[i] + 64) / f)), col_, -1 if st[i, 2] >= 0.5 else 2)
            pnl = cv2.rotate(pnl, cv2.ROTATE_180)                       # reading orientation
            cm = 10000 / 8.64 / f                                       # 1 cm in pixels (1 render px ~ 1 voxel)
            cv2.line(pnl, (12, pnl.shape[0] - 14), (12 + int(cm), pnl.shape[0] - 14), (255, 255, 255), 2)
            cv2.putText(pnl, '1 cm', (12, pnl.shape[0] - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)
            hdr = np.full((24, pnl.shape[1], 3), 22, np.uint8)
            cv2.putText(hdr, f'ink first ({m}, {o}) on the segment: squares = patch centres (1.1 mm), colour = share at ink >= 0.5 (filled: >= 0.5); '
                        f'grey = mesh pipeline {m} map; boxes = the letters', (8, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (230, 230, 230), 1, cv2.LINE_AA)
            panels.append(np.concatenate([hdr, pnl], 0))
    if panels:
        cv2.imwrite(os.path.join(a.out, f'letters_{m}.jpg'), np.concatenate(panels, 0), [cv2.IMWRITE_JPEG_QUALITY, 90])
open(os.path.join(a.out, 'letters_test.tsv'), 'w').write('\n'.join(lines) + '\n')
print('\n'.join(lines))
