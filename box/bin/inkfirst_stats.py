"""Ink first, search test: raw per-patch statistics of an ink-first map (no per-patch normalisation), to compare a block with
known text against blocks without: mean ink, contrast (SD), 95th percentile, and the share of pixels above 0.5 and 0.8, over
the centre --centre x --centre of every patch. Writes <out>.npz (one row per patch) and prints the medians.
Usage: inkfirst_stats.py <patches.npz> <map.tif> <out.npz> [--centre 192] [--label NAME]"""
import argparse
import numpy as np, tifffile

ap = argparse.ArgumentParser()
ap.add_argument('patches'); ap.add_argument('map'); ap.add_argument('out')
ap.add_argument('--centre', type=int, default=192); ap.add_argument('--label', default='')
a = ap.parse_args()
P = np.load(a.patches); S = int(P['size']); C = a.centre; o = (S - C) // 2
M = tifffile.imread(a.map).astype(np.float32) / 255.
rows = []
for R_, C_ in P['rowcol']:
    v = M[R_ * S + o:R_ * S + o + C, C_ * S + o:C_ * S + o + C]
    rows.append((v.mean(), v.std(), np.percentile(v, 95), (v > 0.5).mean(), (v > 0.8).mean()))
X = np.array(rows, np.float32)
np.savez_compressed(a.out, stats=X, cols=np.array(['mean', 'sd', 'p95', 'frac50', 'frac80']), normal=P['normal'], centre=P['centre'])
med = np.median(X, 0); p90 = np.percentile(X, 90, 0)
print(f'{a.label:14s} patches {len(X):5d} | median mean {med[0]:.3f} sd {med[1]:.3f} p95 {med[2]:.3f} frac>0.5 {med[3]:.3f} frac>0.8 {med[4]:.4f} '
      f'| 90th pct sd {p90[1]:.3f} frac>0.5 {p90[3]:.3f}')
