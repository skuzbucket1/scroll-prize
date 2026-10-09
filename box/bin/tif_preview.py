#!/usr/bin/env python3
"""Block-mean downsample a prediction TIFF and write an 8-bit TIFF preview.
Usage: tif_preview.py in.tif out.tif [factor=8] [--rescale9um]
--rescale9um applies the 9 um models' label-smoothing inverse: (p - 0.25) / 0.5, clipped to [0, 1]."""
import sys, numpy as np, tifffile
args = [a for a in sys.argv[1:] if not a.startswith('--')]
src, dst = args[0], args[1]
f = int(args[2]) if len(args) > 2 else 8
a = tifffile.imread(src)
if a.ndim == 3: a = a[0] if a.shape[0] < a.shape[-1] else a[..., 0]
orig_shape, orig_dtype = a.shape, a.dtype
a = a.astype(np.float32)
if a.max() > 1.5: a /= 255.0 if a.max() <= 255 else 65535.0
if '--rescale9um' in sys.argv: a = np.clip((a - 0.25) / 0.5, 0, 1)
h, w = (a.shape[0] // f) * f, (a.shape[1] // f) * f
a = a[:h, :w].reshape(h // f, f, w // f, f).mean(axis=(1, 3))
tifffile.imwrite(dst, (a * 255).round().astype(np.uint8))
print(f'{src}: {orig_shape} {orig_dtype} -> {a.shape}; range {a.min():.3f}-{a.max():.3f} mean {a.mean():.3f}')
