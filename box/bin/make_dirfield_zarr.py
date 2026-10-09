#!/usr/bin/env python3
"""Build a vc_grow_seg_from_seed-compatible direction-field root (x/<L>, y/<L>, z/<L>) from a Lasagna-style
compact normal pair (nx, ny uint8 OME-Zarr pyramids). Both sides use the same encoding, (u8 - 128) / 127,
so x and y are symlinked to the existing pyramids and only z = sqrt(1 - nx^2 - ny^2) is materialised
(at the requested level, same chunks/compressor as nx).
Usage: make_dirfield_zarr.py <nx.ome.zarr> <ny.ome.zarr> <out_root> --level 2 [--slab 64]
"""
import sys, os, json, time
import numpy as np, zarr
from numcodecs import Blosc

def opt(name, default=None):
    if name in sys.argv:
        i = sys.argv.index(name); v = sys.argv[i + 1]; del sys.argv[i:i + 2]; return v
    return default

level = opt("--level", "2"); slab = int(opt("--slab", 64))
nx_root, ny_root, out = [os.path.abspath(p) for p in sys.argv[1:4]]
os.makedirs(out, exist_ok=True)
json.dump({"zarr_format": 2}, open(os.path.join(out, ".zgroup"), "w"))
for comp, src in (("x", nx_root), ("y", ny_root)):
    link = os.path.join(out, comp)
    if os.path.islink(link) or os.path.exists(link):
        os.remove(link) if os.path.islink(link) else None
    if not os.path.exists(link):
        os.symlink(src, link)
zdir = os.path.join(out, "z"); os.makedirs(zdir, exist_ok=True)
json.dump({"zarr_format": 2}, open(os.path.join(zdir, ".zgroup"), "w"))
nx = zarr.open(os.path.join(nx_root, level), mode="r"); ny = zarr.open(os.path.join(ny_root, level), mode="r")
assert nx.shape == ny.shape and nx.dtype == np.uint8
meta = json.load(open(os.path.join(nx_root, level, ".zarray")))
zpath = os.path.join(zdir, level)
if os.path.exists(zpath):
    import shutil; shutil.rmtree(zpath)
z = zarr.open(zpath, mode="w", shape=nx.shape, chunks=tuple(meta["chunks"]), dtype=np.uint8,
              compressor=Blosc(cname=meta["compressor"]["cname"], clevel=meta["compressor"]["clevel"], shuffle=meta["compressor"]["shuffle"]),
              dimension_separator=meta.get("dimension_separator", "."), fill_value=128, zarr_format=2)
t0 = time.time(); Z = nx.shape[0]
for z0 in range(0, Z, slab):
    z1 = min(Z, z0 + slab)
    a = nx[z0:z1].astype(np.float32); b = ny[z0:z1].astype(np.float32)
    valid = (nx[z0:z1] != 0) | (ny[z0:z1] != 0)   # 0/0 = "no prediction" in the Fiber output (fill 0)
    a = (a - 128.0) / 127.0; b = (b - 128.0) / 127.0
    nz = np.sqrt(np.maximum(0.0, 1.0 - a * a - b * b))
    enc = np.clip(np.rint(nz * 127.0 + 128.0), 0, 255).astype(np.uint8)
    enc[~valid] = 0
    z[z0:z1] = enc
    if (z0 // slab) % 10 == 0:
        print(f"z {z0}-{z1}/{Z} valid {valid.mean():.3f} [{time.time()-t0:.0f}s]", flush=True)
# copy .zattrs for completeness
for comp in ("z",):
    try:
        attrs = json.load(open(os.path.join(nx_root, ".zattrs"))); attrs["multiscales"][0]["name"] = "nz"
        json.dump(attrs, open(os.path.join(zdir, ".zattrs"), "w"))
    except Exception as e:
        print("no .zattrs copied:", e)
print(f"wrote {out}: x,y -> symlinks; z/{level} shape {z.shape} [{time.time()-t0:.0f}s]")
