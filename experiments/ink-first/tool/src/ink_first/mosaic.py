"""Patch mosaics: split a big mosaic into quarters for inference (a 300+ Mpx mosaic runs out of memory in the ink models'
inference), stitch the quarters' ink maps back, and read the central part of every patch from an ink map."""
from __future__ import annotations

import os

import numpy as np


def quarters(H: int, W: int, S: int) -> list:
    hr, hc = (H // S + 1) // 2 * S, (W // S + 1) // 2 * S                     # borders on patch boundaries
    return [(0, hr, 0, hc), (0, hr, hc, W), (hr, H, 0, hc), (hr, H, hc, W)]


def split(d: str, S: int | None = None, log=print) -> None:
    """<d>/mosaic.zarr -> <d>/q0..q3/mosaic.zarr."""
    import zarr
    src = zarr.open_group(os.path.join(d, 'mosaic.zarr'), mode='r')['0']
    S = S or int(np.load(os.path.join(d, 'patches.npz'))['size'])
    L, H, W = src.shape
    for q, (y0, y1, x0, x1) in enumerate(quarters(H, W, S)):
        g = zarr.open_group(os.path.join(d, f'q{q}', 'mosaic.zarr'), mode='w', zarr_format=2)
        a = g.create_array('0', shape=(L, y1 - y0, x1 - x0), chunks=(L, 256, 256), dtype='u1', fill_value=0)
        for yy in range(y0, y1, 2048):
            a[:, yy - y0:min(yy + 2048, y1) - y0, :] = src[:, yy:min(yy + 2048, y1), x0:x1]
        log(f'q{q}: rows {y0}-{y1} cols {x0}-{x1}')


def stitch(d: str, model: str, s: int = 25, S: int | None = None, log=print) -> None:
    """<d>/q*/maps/mosaic__<model>__L66s<s>[_reverse].tif -> <d>/maps/ (same names, whole mosaic)."""
    import tifffile
    P = np.load(os.path.join(d, 'patches.npz')); S = S or int(P['size'])
    g = int(np.ceil(np.sqrt(len(P['rowcol'])))); H = W = g * S
    os.makedirs(os.path.join(d, 'maps'), exist_ok=True)
    for suf in ('', '_reverse'):
        out = np.zeros((H, W), np.uint8)
        for q, (y0, y1, x0, x1) in enumerate(quarters(H, W, S)):
            out[y0:y1, x0:x1] = tifffile.imread(os.path.join(d, f'q{q}', 'maps', f'mosaic__{model}__L66s{s}{suf}.tif'))
        tifffile.imwrite(os.path.join(d, 'maps', f'mosaic__{model}__L66s{s}{suf}.tif'), out)
        log(f'stitched {model} {suf or "forward"} {out.shape}')


def centre(M: np.ndarray, rowcol, S: int, C: int) -> np.ndarray:
    """The central C x C pixels of the patch at mosaic (row, col)."""
    o = (S - C) // 2; r, c = rowcol
    return M[r * S + o:r * S + o + C, c * S + o:c * S + o + C]
