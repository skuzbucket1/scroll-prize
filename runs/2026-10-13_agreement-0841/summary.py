"""Six-model agreement on known 9.36 µm text against the earlier sets (2026-10-13). Per set: tiles, the models present,
the share of tiles with at least (n - 1) of the n models one-sided (reading - blind above 0.2 of the model's own
spread), with all n, and the same without Hecate (which may have trained on PHerc0841; its training set is unknown for
PHerc0139). Sets: PHerc0841 ag2814 and w00 letter tiles (300 px grid tiles with at least 15 % human-labelled ink) and
bare papyrus (300 px tiles inside the supervision mask, away from the letter tiles); PHerc0139 w047 letter tiles (tiles
where at least 15 % of the 2.4 µm reference prediction is above half its maximum) and bare tiles, five models (d9v4C
trained on this segment and is left out); PHerc. 343 letters and background (2026-10-12_model-agreement/343_d+1.tsv);
the six clean 9.36 µm crops at d +1 (2026-10-12_agreement-null); the PHerc0813 w079 false alarm at d +1.
Usage: summary.py [dir of tsvs]   (the dir form reads every set from one folder, e.g. relative/ for the --relative rerun)"""
import csv, glob, os, sys
import cv2, numpy as np

S = os.path.expanduser('~/scroll-prizes/runs'); R = f'{S}/2026-10-13_agreement-0841'
if len(sys.argv) > 1:                       # one folder holding every set's tsv under the canonical names (the --relative rerun)
    D = sys.argv[1]; R = D; S343 = D; SNULL = D; S079 = D
else:
    S343 = f'{S}/2026-10-12_model-agreement'; SNULL = f'{S}/2026-10-12_agreement-null'; S079 = f'{S}/2026-10-12_model-agreement'
SIX = ['dnative', 'hybrid_3d2d-seed42', 'hybrid_3d2d-seed43', 'hecate', 'readerv2', 'd9v4c']


def rows(path, cls=None, sup=None):
    """(models present, array of per-model z values) for the tiles of one class."""
    if not os.path.exists(path):
        return [], np.zeros((0, 0))
    rd = list(csv.DictReader(open(path), delimiter='\t')); models = [m for m in SIX if rd and m in rd[0]]
    out = []
    for r in rd:
        if cls and r['class'] != cls:
            continue
        if sup is not None:
            y, x, h, w = (int(r[k]) for k in ('y', 'x', 'h', 'w'))
            if sup[y:y + h, x:x + w].mean() < 0.8:
                continue
        out.append([float(r[m]) for m in models])
    return models, np.array(out).reshape(-1, len(models))


sets = []
for n in ('ag2814', 'w00'):
    t = f'{R}/agree_c0841_{n}_66_d1.tsv'
    sets += [(f'PHerc0841 {n} letters', rows(t, 'letter')), (f'PHerc0841 {n} other papyrus (may hold unlabelled text)', rows(t, 'background'))]
t = f'{R}/agree_c0139_w047_66_d1.tsv'
sets += [('PHerc0139 w047 letters (5 models)', rows(t, 'letter')), ('PHerc0139 w047 other papyrus (5 models)', rows(t, 'background')),
         ('PHerc. 343 letters', rows(f'{S343}/343_d+1.tsv', 'letter')),
         ('PHerc. 343 background', rows(f'{S343}/343_d+1.tsv', 'background'))]
nulls = [rows(f) for f in sorted(glob.glob(f'{SNULL}/agree_*_null_d1.tsv'))]
if nulls:
    sets.append(('clean 9.36 µm crops (6), d +1', (nulls[0][0], np.concatenate([x for _, x in nulls]))))
sets.append(('PHerc0813 w079 false alarm, d +1', rows(f'{S079}/w079_d1.tsv')))
print(f'{"set":<52} {"tiles":>5} {"models":>6}  {">= n-1 of n":>11}  {"all n":>6}  {"no Hecate >= n-2":>16}  {"mean z":>7}')
for name, (models, X) in sets:
    if not len(X):
        print(f'{name:<52} {0:>5}'); continue
    n = len(models); k = (X > 0.2).sum(1)
    noh = [i for i, m in enumerate(models) if m != 'hecate']; kh = (X[:, noh] > 0.2).sum(1)
    print(f'{name:<52} {len(X):>5} {n:>6}  {np.mean(k >= n - 1):>11.0%}  {np.mean(k == n):>6.0%}  {np.mean(kh >= len(noh) - 1):>16.0%}  {X.mean():>+7.2f}')
