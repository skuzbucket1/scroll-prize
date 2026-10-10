#!/usr/bin/env python3
"""Smooth a vc_gen_umbilicus result the way PHerc0191's umbilicus was smoothed (2026-10-08): local-median outlier rejection
(a point more than --maxdev voxels from the median of its +-8 neighbours is an outlier), then a +-4-point moving average of
the inliers. The raw file is left untouched.
Usage: smooth_umbilicus.py <raw.json> <out.json> [--maxdev 400]"""
import json, statistics as st, sys

args = sys.argv[1:]
maxdev = 400.0
if '--maxdev' in args:
    i = args.index('--maxdev'); maxdev = float(args[i + 1]); del args[i:i + 2]
raw, out_path = args
d = json.load(open(raw)); c = sorted(d['control_points'], key=lambda p: p['z'])
zs = [p['z'] for p in c]; xs = [p['x'] for p in c]; ys = [p['y'] for p in c]; n = len(c)


def win(i, k):
    return range(max(0, i - k), min(n, i + k + 1))


inlier = []
for i in range(n):
    w = win(i, 8); mx = st.median([xs[j] for j in w]); my = st.median([ys[j] for j in w])
    inlier.append(((xs[i] - mx) ** 2 + (ys[i] - my) ** 2) ** 0.5 <= maxdev)
out = []
for i in range(n):
    w = [j for j in win(i, 4) if inlier[j]] or [j for j in win(i, 8) if inlier[j]] or list(win(i, 8))
    p = dict(c[i]); p['x'] = sum(xs[j] for j in w) / len(w); p['y'] = sum(ys[j] for j in w) / len(w); p['smoothed'] = True
    out.append(p)
d['control_points'] = out
d.setdefault('metadata', {})['smoothing'] = ('local-median outlier rejection (>%g vx vs +-8 nbrs, %d of %d rejected) + '
                                             '+-4-point moving average of inliers; raw in %s' % (maxdev, n - sum(inlier), n, raw))
json.dump(d, open(out_path, 'w'), indent=1)
sx = [p['x'] for p in out]; sy = [p['y'] for p in out]
step_raw = [((xs[i + 1] - xs[i]) ** 2 + (ys[i + 1] - ys[i]) ** 2) ** 0.5 for i in range(n - 1)]
step = [((sx[i + 1] - sx[i]) ** 2 + (sy[i + 1] - sy[i]) ** 2) ** 0.5 for i in range(n - 1)]
print(f'{n} points, z {zs[0]:.0f}-{zs[-1]:.0f}; rejected {n - sum(inlier)} outliers; median neighbour step '
      f'{st.median(step_raw):.1f} vx raw -> {st.median(step):.1f} smoothed')
for z0 in sorted({zs[0], zs[n // 4], zs[n // 2], zs[3 * n // 4], zs[-1]}):
    i = zs.index(z0); print(f'  z {z0:.0f}: raw ({xs[i]:.0f},{ys[i]:.0f}) -> smoothed ({sx[i]:.0f},{sy[i]:.0f})')
