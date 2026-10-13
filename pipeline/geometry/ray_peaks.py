#!/usr/bin/env python3
"""Winding-count / umbilicus audit on a CT slice: cast rays from a center and count sheet (bright) peaks along each ray.
Usage: ray_peaks.py <volume.zarr> <z_full_res> [--level 2] [--center X Y (full-res voxels)] [--umbilicus umbilicus.json] [--rays 12] [--step 1.0]
Without --center/--umbilicus the center is the intensity-weighted centroid of the slice (a proxy for the umbilicus).
Per ray: distance to first sheet, peak counts at three prominence levels, autocorrelation period and implied count, ray extent.
Also: mean intensity in a ~1.5 mm disk around the center (near zero = air core) as the umbilicus check."""
import sys, json, numpy as np, zarr
args = sys.argv[1:]
def opt(name, n=1, default=None):
    if name in args:
        i = args.index(name); v = args[i+1:i+1+n]; del args[i:i+1+n]; return v if n > 1 else v[0]
    return default
level = int(opt("--level", default="2")); nrays = int(opt("--rays", default="12")); step = float(opt("--step", default="1.0"))
center = opt("--center", 2); umb = opt("--umbilicus"); VOX_UM = 9.362
vol, z = args[0], int(args[1])
g = zarr.open(vol, mode="r"); a = g[str(level)]; s = 2 ** level
zl = min(a.shape[0] - 1, z // s); img = np.asarray(a[zl]).astype(np.float32)
if umb:
    cps = sorted(json.load(open(umb))["control_points"], key=lambda c: c["z"]); zs = np.array([c["z"] for c in cps])
    cx = np.interp(z, zs, [c["x"] for c in cps]) / s; cy = np.interp(z, zs, [c["y"] for c in cps]) / s; src = "umbilicus.json"
elif center:
    cx, cy = float(center[0]) / s, float(center[1]) / s; src = "--center"
else:
    m = img > 0; ys, xs = np.nonzero(m); w = img[m]; cx, cy = (xs * w).sum() / w.sum(), (ys * w).sum() / w.sum(); src = "intensity centroid"
r_core = 1500.0 / VOX_UM / s   # 1.5 mm in level-s voxels
yy, xx = np.ogrid[:img.shape[0], :img.shape[1]]; core = img[((xx - cx) ** 2 + (yy - cy) ** 2) < r_core ** 2]
print(f"slice z={z} (level {level} idx {zl}, {img.shape}); center ({cx*s:.0f}, {cy*s:.0f}) full-res via {src}; 1.5 mm core disk: mean {core.mean():.1f}, nonzero frac {(core>0).mean():.2f}")
def smooth(v, k=3): return np.convolve(v, np.ones(k) / k, mode="same")
def peaks(v, prom):
    out = []
    for i in range(1, len(v) - 1):
        if v[i] > v[i-1] and v[i] >= v[i+1]:
            lo = min(v[max(0, i-15):i].min(), v[i+1:i+16].min())
            if v[i] - lo >= prom: out.append(i)
    return out
print(f"{'ray°':>5s} {'first-sheet mm':>14s} {'strict':>6s} {'mid':>5s} {'perm':>5s} {'period vx':>9s} {'ext/period':>10s} {'extent mm':>9s}")
rows = []
for k in range(nrays):
    ang = 2 * np.pi * (k + 0.5) / nrays; d = np.arange(0, 1200, step); xs = cx + d * np.cos(ang); ys = cy + d * np.sin(ang)
    ok = (xs >= 0) & (xs < img.shape[1] - 1) & (ys >= 0) & (ys < img.shape[0] - 1); xs, ys, d = xs[ok], ys[ok], d[ok]
    prof = img[ys.round().astype(int), xs.round().astype(int)]; nz = np.nonzero(prof > 0)[0]
    if len(nz) < 20: print(f"{int(np.degrees(ang)):>5d}  (ray leaves the mask immediately)"); continue
    first, last = nz[0], nz[-1]; p = smooth(prof[first:last + 1]); sd = p.std()
    st, md, pe = len(peaks(p, 1.5 * sd)), len(peaks(p, 0.9 * sd)), len(peaks(p, 0.45 * sd))
    pc = p - p.mean(); ac = np.correlate(pc, pc, "full")[len(pc) - 1:]; ac = ac / ac[0] if ac[0] else ac
    per = next((i for i in range(3, min(len(ac) - 1, 200)) if ac[i] > ac[i-1] and ac[i] >= ac[i+1] and ac[i] > 0.05), 0)
    ext = (last - first) * step; rows.append((st, md, pe))
    print(f"{int(np.degrees(ang)):>5d} {first*step*s*VOX_UM/1000:>14.1f} {st:>6d} {md:>5d} {pe:>5d} {per:>9d} {(ext/per if per else 0):>10.1f} {ext*s*VOX_UM/1000:>9.1f}")
if rows: r = np.array(rows); print(f"median peaks/ray — strict {np.median(r[:,0]):.0f}, mid {np.median(r[:,1]):.0f}, permissive {np.median(r[:,2]):.0f}")
