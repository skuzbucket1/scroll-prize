#!/usr/bin/env python3
"""Write a block-mean-downsampled, percentile-stretched 8-bit TIFF preview of one z-slice of a zarr array (or group level).
Usage: zarr_slice_preview.py path.zarr out.tif [level=0] [z=middle] [factor=4]"""
import sys, numpy as np, zarr, tifffile
p, dst = sys.argv[1], sys.argv[2]
level = sys.argv[3] if len(sys.argv) > 3 else '0'
root = zarr.open(p, mode='r')
arr = root if hasattr(root, 'shape') else root[level]
z = int(sys.argv[4]) if len(sys.argv) > 4 else arr.shape[0] // 2
f = int(sys.argv[5]) if len(sys.argv) > 5 else 4
sl = np.asarray(arr[z]); nz = (sl > 0).mean()
a = sl.astype(np.float32)
h, w = (a.shape[0] // f) * f, (a.shape[1] // f) * f
a = a[:h, :w].reshape(h // f, f, w // f, f).mean(axis=(1, 3))
lo, hi = (np.percentile(a[a > 0], [1, 99]) if (a > 0).any() else (0.0, 1.0))
a = np.clip((a - lo) / max(hi - lo, 1e-6), 0, 1)
tifffile.imwrite(dst, (a * 255).round().astype(np.uint8))
print(f'{p} level {level} z={z}: shape {arr.shape} {arr.dtype} chunks {arr.chunks} nonzero {nz:.1%} -> preview {a.shape} (stretch {lo:.0f}-{hi:.0f})')
