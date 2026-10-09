#!/usr/bin/env python3
"""Derive the spiral fitter's `outer_shell/` tifxyz from a *masked* CT volume.

The fitter (spiral-fitting/fit_spiral.py ShellPolarMap) only uses the shell's valid
(z, y, x) points: it bins them by z and by angle around the umbilicus and takes the mean
radius per bin. So any surface that traces the papyrus' outer boundary will do. For a
masked volume (air outside the scroll is exactly 0) the boundary is the edge of the
largest non-zero connected component in each slice.

Usage: make_outer_shell.py <volume.zarr> <umbilicus.json> <out_dir> [--level 2] [--dz 8]
       [--z-begin 0] [--z-end N] [--theta-bins 720] [--radius-percentile 100]

Output: <out_dir>/{x,y,z}.tif (float32, rows = z samples, cols = theta bins, -1 = empty bin)
        + meta.json. Coordinates are full-resolution (level 0) voxels.
"""
import sys, json, time, os
import numpy as np, zarr, scipy.ndimage as ndi
from PIL import Image

def opt(name, n=1, default=None):
    if name in sys.argv:
        i = sys.argv.index(name); v = sys.argv[i + 1:i + 1 + n]; del sys.argv[i:i + 1 + n]
        return v[0] if n == 1 else v
    return default

level = int(opt("--level", default=2)); dz = int(opt("--dz", default=8))
zb = int(opt("--z-begin", default=0)); ze = opt("--z-end"); nth = int(opt("--theta-bins", default=720))
rpct = float(opt("--radius-percentile", default=100))
vol_path, umb_path, out = sys.argv[1:4]
s = 2 ** level
vol = zarr.open(vol_path, mode="r")[str(level)]
nz_full = vol.shape[0] * s
ze = int(ze) if ze else nz_full
cps = sorted(json.load(open(umb_path))["control_points"], key=lambda c: c["z"])
uz = np.array([c["z"] for c in cps]); ux = np.array([c["x"] for c in cps]); uy = np.array([c["y"] for c in cps])

zs = np.arange(zb, ze, dz)
X = np.full((len(zs), nth), -1, np.float32); Y = X.copy(); Z = X.copy()
edges = np.linspace(0, 2 * np.pi, nth + 1)
t0 = time.time(); stats = []
for i, z in enumerate(zs):
    img = vol[min(z // s, vol.shape[0] - 1)]
    m = img > 0
    if not m.any():
        stats.append((int(z), 0, 0.0, 0.0, 0.0, False, 0)); continue
    lab, n = ndi.label(m)
    if n > 1:
        sizes = ndi.sum(m, lab, range(1, n + 1)); keep = int(np.argmax(sizes)) + 1; m = lab == keep
    cx = np.interp(z, uz, ux) / s; cy = np.interp(z, uz, uy) / s
    yy, xx = np.nonzero(m)
    rel_y = yy - cy; rel_x = xx - cx
    theta = np.mod(np.arctan2(rel_y, rel_x), 2 * np.pi)   # same convention as ShellPolarMap: atan2(dy, dx)
    r = np.hypot(rel_y, rel_x)
    b = np.minimum((theta / (2 * np.pi) * nth).astype(int), nth - 1)
    if rpct >= 100:
        rmax = np.full(nth, -1.0); np.maximum.at(rmax, b, r)
    else:
        rmax = np.full(nth, -1.0)
        order = np.argsort(b); b_s = b[order]; r_s = r[order]
        starts = np.searchsorted(b_s, np.arange(nth)); ends = np.searchsorted(b_s, np.arange(nth), side="right")
        for k in range(nth):
            if ends[k] > starts[k]: rmax[k] = np.percentile(r_s[starts[k]:ends[k]], rpct)
    ok = rmax > 0
    th_c = 0.5 * (edges[:-1] + edges[1:])
    X[i, ok] = (cx + rmax[ok] * np.cos(th_c[ok])) * s
    Y[i, ok] = (cy + rmax[ok] * np.sin(th_c[ok])) * s
    Z[i, ok] = z
    inside = bool(m[int(round(cy)), int(round(cx))]) if 0 <= int(round(cy)) < m.shape[0] and 0 <= int(round(cx)) < m.shape[1] else False
    stats.append((int(z), int(ok.sum()), float(rmax[ok].min() * s * 9.362 / 1000), float(np.median(rmax[ok]) * s * 9.362 / 1000), float(rmax[ok].max() * s * 9.362 / 1000), bool(inside), int(n)))
    if i % 200 == 0:
        print(f"z={z} bins={ok.sum()}/{nth} r_mm min/med/max={stats[-1][2]:.1f}/{stats[-1][3]:.1f}/{stats[-1][4]:.1f} umbilicus_inside={inside} components={n} [{time.time()-t0:.0f}s]", flush=True)

os.makedirs(out, exist_ok=True)
Image.fromarray(X).save(f"{out}/x.tif"); Image.fromarray(Y).save(f"{out}/y.tif"); Image.fromarray(Z).save(f"{out}/z.tif")
valid = Z >= 0
meta = {"uuid": os.path.basename(out.rstrip("/")) or "outer_shell", "scale": [float(dz), float(2 * np.pi * np.median([st[3] for st in stats if st[1] > 0]) * 1000 / 9.362 / nth)],
        "type": "seg", "format": "tifxyz", "source": "make_outer_shell.py: largest non-zero component boundary of masked CT",
        "volume": vol_path, "level": level, "dz": dz, "theta_bins": nth, "radius_percentile": rpct, "z_begin": zb, "z_end": ze,
        "bbox": [float(X[valid].min()), float(Y[valid].min()), float(Z[valid].min()), float(X[valid].max()), float(Y[valid].max()), float(Z[valid].max())]}
json.dump(meta, open(f"{out}/meta.json", "w"), indent=1)
json.dump([dict(zip(("z", "bins", "rmin_mm", "rmed_mm", "rmax_mm", "umbilicus_inside", "components"), st)) for st in stats], open(f"{out}/shell_stats.json", "w"))
empty_rows = int((~valid.any(axis=1)).sum()); not_inside = sum(1 for st in stats if len(st) > 5 and not st[5])
print(f"wrote {out}: rows={len(zs)} theta_bins={nth} valid={int(valid.sum())} empty_rows={empty_rows} umbilicus_outside_rows={not_inside} [{time.time()-t0:.0f}s]")
