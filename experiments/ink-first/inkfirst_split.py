"""Ink first: split a big patch mosaic into quarters for inference (one mosaic of 300+ Mpx runs out of memory), or stitch
the quarters' ink maps back into one map with the original name, so inkfirst_back.py works unchanged.
Usage: inkfirst_split.py split <dir with mosaic.zarr>            -> <dir>/q0..q3/mosaic.zarr
       inkfirst_split.py stitch <dir> <model>                    -> <dir>/maps/mosaic__<model>__L66s25[_reverse].tif"""
import os, sys
import numpy as np, tifffile, zarr

cmd, d = sys.argv[1], sys.argv[2]
src = zarr.open_group(os.path.join(d, 'mosaic.zarr'), mode='r')['0']
L, H, W = src.shape; S = 256
hr, hc = (H // S + 1) // 2 * S, (W // S + 1) // 2 * S                        # quarter borders on patch boundaries
quads = [(0, hr, 0, hc), (0, hr, hc, W), (hr, H, 0, hc), (hr, H, hc, W)]
if cmd == 'split':
    for q, (y0, y1, x0, x1) in enumerate(quads):
        g = zarr.open_group(os.path.join(d, f'q{q}', 'mosaic.zarr'), mode='w', zarr_format=2)
        a = g.create_array('0', shape=(L, y1 - y0, x1 - x0), chunks=(L, 256, 256), dtype='u1', fill_value=0)
        for yy in range(y0, y1, 2048):
            a[:, yy - y0:min(yy + 2048, y1) - y0, :] = src[:, yy:min(yy + 2048, y1), x0:x1]
        print(f'q{q}: rows {y0}-{y1} cols {x0}-{x1}', flush=True)
else:
    model = sys.argv[3]; os.makedirs(os.path.join(d, 'maps'), exist_ok=True)
    for suf in ('', '_reverse'):
        out = np.zeros((H, W), np.uint8)
        for q, (y0, y1, x0, x1) in enumerate(quads):
            out[y0:y1, x0:x1] = tifffile.imread(os.path.join(d, f'q{q}', 'maps', f'mosaic__{model}__L66s25{suf}.tif'))
        tifffile.imwrite(os.path.join(d, 'maps', f'mosaic__{model}__L66s25{suf}.tif'), out)
        print('stitched', suf or 'forward', out.shape)
