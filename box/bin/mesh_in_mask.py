#!/usr/bin/env python3
"""Per-winding 'in papyrus' audit for a spiral-fit run.

For each exported (non-spliced) winding mesh, sample its vertices on the masked CT at level 2 and
report the fraction that land on non-zero voxels (inside the scroll), the mean radius from the
umbilicus, and the vertex count. Summarises how many windings are mostly in air.
Usage: mesh_in_mask.py <run_dir> <volume.zarr> <umbilicus.json> [--level 2] [--stride 4]
"""
import sys, json, glob, os
import numpy as np, zarr
from PIL import Image

def opt(name, default=None):
    if name in sys.argv:
        i = sys.argv.index(name); v = sys.argv[i + 1]; del sys.argv[i:i + 2]; return v
    return default

level = int(opt("--level", 2)); stride = int(opt("--stride", 4))
run, vol_path, umb_path = sys.argv[1:4]
s = 2 ** level
vol = zarr.open(vol_path, mode="r")[str(level)]
cps = sorted(json.load(open(umb_path))["control_points"], key=lambda c: c["z"])
uz = np.array([c["z"] for c in cps]); ux = np.array([c["x"] for c in cps]); uy = np.array([c["y"] for c in cps])
mesh_dirs = sorted(d for d in glob.glob(os.path.join(run, "meshes", "*", "w[0-9][0-9][0-9]_*")) if "_spliced_" not in d)
rows = []
cache = {}
for d in mesh_dirs:
    w = int(os.path.basename(d)[1:4])
    Z = np.array(Image.open(f"{d}/z.tif"))[::stride, ::stride]
    Y = np.array(Image.open(f"{d}/y.tif"))[::stride, ::stride]
    X = np.array(Image.open(f"{d}/x.tif"))[::stride, ::stride]
    ok = (Z >= 0) & (Y >= 0) & (X >= 0)
    z = Z[ok]; y = Y[ok]; x = X[ok]
    if len(z) == 0:
        rows.append((w, 0, float("nan"), float("nan"))); continue
    zi = np.clip((z / s).astype(int), 0, vol.shape[0] - 1); yi = np.clip((y / s).astype(int), 0, vol.shape[1] - 1); xi = np.clip((x / s).astype(int), 0, vol.shape[2] - 1)
    vals = np.empty(len(z), np.uint8)
    for zz in np.unique(zi):
        if zz not in cache: cache[zz] = vol[int(zz)]
        m = zi == zz; vals[m] = cache[zz][yi[m], xi[m]]
    inside = float((vals > 0).mean())
    r = np.hypot(y - np.interp(z, uz, uy), x - np.interp(z, uz, ux)) * 9.362 / 1000
    rows.append((w, int(len(z)), inside, float(r.mean())))
print(f"run: {run}")
print(f"windings: {len(rows)}  (w{rows[0][0]:03d}..w{rows[-1][0]:03d})")
air = [r for r in rows if r[1] > 0 and r[2] < 0.5]
print(f"windings with <50% of vertices inside the CT mask: {len(air)}  -> {[r[0] for r in air][:12]}{'...' if len(air) > 12 else ''}")
mostly_in = [r for r in rows if r[1] > 0 and r[2] >= 0.9]
print(f"windings with >=90% inside: {len(mostly_in)}")
print(" w   verts  inside  r_mm")
for r in rows[::max(1, len(rows) // 24)] + [rows[-1]]:
    print(f"{r[0]:3d} {r[1]:7d}  {r[2]:5.2f}  {r[3]:5.1f}")
json.dump([dict(zip(("winding", "verts", "inside_fraction", "mean_radius_mm"), r)) for r in rows], open(os.path.join(run, "mesh_in_mask.json"), "w"))
