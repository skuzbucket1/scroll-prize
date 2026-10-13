"""Re-sort an ink-first sweep for browsing by eye: the patches that look like the PHerc. 343 letter patches rather than
the hottest ones (which are saturated blobs on damage). Rule, on undamaged papyrus (air <= 0.3): partly lit on the
reading side (`lo` <= frac50 <= `hi`; frac50 = share of the patch centre at ink >= 0.5) and nearly dark on the other
side (frac50 <= `other`); ranked by reading-side mean ink minus other-side mean ink. On PHerc. 343 (Reader v2) the
rule passed 11 % of the letter patches against 7 % elsewhere in the block; 10-12 % of all patches on known-text blocks
against 3-5 % on text-free ones. A browsing order, not a detector.
Writes <out>/resort.tsv (ranked candidates), resort_blocks.tsv (share of patches passing, per block), candidates.tsv
(the top ones in the clusters format, for inkfirst_cluster_view.py) and resort_<k>.jpg (CT | reading side | other side
of the patch centre, 1.1 mm, from the 64 px thumbnails; ranked).
Usage: inkfirst_resort.py <results dir (*/summary.npz)> <out dir> [--model readerv2] [--lo 0.10] [--hi 0.60] [--other 0.05]
       [--top 48] [--reading fwd]"""
import argparse, glob, os
import cv2, numpy as np

ap = argparse.ArgumentParser()
ap.add_argument('res'); ap.add_argument('out'); ap.add_argument('--model', default='readerv2')
ap.add_argument('--lo', type=float, default=0.10); ap.add_argument('--hi', type=float, default=0.60); ap.add_argument('--other', type=float, default=0.05)
ap.add_argument('--top', type=int, default=48); ap.add_argument('--reading', default='fwd')
a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
rd, ot = a.reading, {'fwd': 'rev', 'rev': 'fwd'}[a.reading]
cand, blocks = [], []
for f in sorted(glob.glob(os.path.join(a.res, '**', 'summary.npz'), recursive=True)):
    S = np.load(f); blk = os.path.basename(os.path.dirname(f))
    F, R = S[f'stats_{a.model}_{rd}'], S[f'stats_{a.model}_{ot}']; air = S['air'] if 'air' in S.files else np.zeros(len(F))
    ok = air <= 0.3; p = ok & (F[:, 2] >= a.lo) & (F[:, 2] <= a.hi) & (R[:, 2] <= a.other)
    blocks.append((blk, int(ok.sum()), float(p.sum() / max(ok.sum(), 1))))
    if not p.any():
        continue
    C, CT, IR, IO = S['centre'], S['ct64'], S[f'ink64_{a.model}_{rd}'], S[f'ink64_{a.model}_{ot}']      # load each array once
    for j in np.nonzero(p)[0]:
        cand.append((float(F[j, 0] - R[j, 0]), blk, int(j), *C[j], float(F[j, 2]), float(R[j, 2]), float(F[j, 0]), float(R[j, 0]), float(air[j]),
                     CT[j], IR[j], IO[j]))
cand.sort(key=lambda t: -t[0])
with open(os.path.join(a.out, 'resort.tsv'), 'w') as fo:
    fo.write('rank\tblock\tpatch\tz\ty\tx\tfrac50_reading\tfrac50_other\tmean_reading\tmean_other\tair\n')
    for k, c in enumerate(cand):
        fo.write(f'{k + 1}\t{c[1]}\t{c[2]}\t{c[3]:.0f}\t{c[4]:.0f}\t{c[5]:.0f}\t{c[6]:.3f}\t{c[7]:.3f}\t{c[8]:.3f}\t{c[9]:.3f}\t{c[10]:.2f}\n')
with open(os.path.join(a.out, 'resort_blocks.tsv'), 'w') as fo:
    fo.write('block\tplausible\tshare_passing\n')
    for b in sorted(blocks, key=lambda b: -b[2]):
        fo.write(f'{b[0]}\t{b[1]}\t{b[2]:.4f}\n')
with open(os.path.join(a.out, 'candidates.tsv'), 'w') as fo:      # for inkfirst_cluster_view.py
    fo.write('cluster\tpatches\tmean_frac50\tmax_frac50\tother_side\tone_sided\tz\ty\tx\tblocks\n')
    for k, c in enumerate(cand[:a.top]):
        fo.write(f'r{k + 1:03d}\t1\t{c[6]:.3f}\t{c[6]:.3f}\t{c[7]:.3f}\t1.00\t{c[3]:.0f}\t{c[4]:.0f}\t{c[5]:.0f}\t{c[1]}\n')
tiles = []
for k, c in enumerate(cand[:a.top]):
    ct = cv2.normalize(c[11], None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    t = np.concatenate([cv2.cvtColor(ct, cv2.COLOR_GRAY2BGR), cv2.applyColorMap(c[12], cv2.COLORMAP_INFERNO),
                        cv2.applyColorMap(c[13], cv2.COLORMAP_INFERNO)], 1)
    t = cv2.resize(t, (t.shape[1] * 3, t.shape[0] * 3), interpolation=cv2.INTER_NEAREST)
    cv2.putText(t, f'#{k + 1} {c[1]} p{c[2]}  z{c[3]:.0f} y{c[4]:.0f} x{c[5]:.0f}', (6, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1, cv2.LINE_AA)
    cv2.putText(t, 'CT', (6, t.shape[0] - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1, cv2.LINE_AA)
    cv2.putText(t, f'reading {c[6]:.2f}', (198, t.shape[0] - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1, cv2.LINE_AA)
    cv2.putText(t, f'other {c[7]:.2f}', (390, t.shape[0] - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1, cv2.LINE_AA)
    tiles.append(cv2.copyMakeBorder(t, 3, 3, 3, 3, cv2.BORDER_CONSTANT, value=(22, 22, 22)))
for pg in range(0, len(tiles), 24):
    page = tiles[pg:pg + 24]
    while len(page) % 3:
        page.append(np.zeros_like(tiles[0]))
    cv2.imwrite(os.path.join(a.out, f'resort_{pg // 24 + 1}.jpg'), np.concatenate([np.concatenate(page[i:i + 3], 1) for i in range(0, len(page), 3)], 0),
                [cv2.IMWRITE_JPEG_QUALITY, 90])
sh = np.array([b[2] for b in blocks])
print(f'{len(cand)} patches pass ({len(cand) / max(sum(b[1] for b in blocks), 1):.2%} of plausible); per block median {np.median(sh):.2%}, '
      f'90th {np.percentile(sh, 90):.2%}, max {sh.max():.2%} ({max(blocks, key=lambda b: b[2])[0]})')
