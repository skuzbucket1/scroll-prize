#!/usr/bin/env python3
"""pad_render.py - copy of a 66-layer render, shifted by zero rows on top and zero columns on the left.

    python pad_render.py <render.zarr> <padded.zarr> [--pad-rows 40] [--pad-cols 200]

Why: villa's ink models work on 64-px tiles and Hecate on 32-px tiles at 9.6 um, so an ink map depends a little on
where a letter falls in the tile grid. In the joined mesh, w048 sits at the tile phase of its own render, but w047 is
shifted by (-40, -1800) px. Padding by (40, 200) moves w047 back by a multiple of 320 px (= 5 x 64 px for villa and
9 x 32 Hecate px), so the ink maps of this padded copy reproduce the w047 maps of the original render.
merge_tile_phase.py then takes the w047 pixels from these maps and everything else from the maps of the plain render.

Output: a zarr v2 group with only level '0' (66 x (H + pad_rows) x (W + pad_cols), uint8, chunks 66 x 128 x 128),
the same layout as the renders the ink maps of this submission were computed on.
"""
import argparse
import os
import shutil

import numpy as np


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('render')
    ap.add_argument('out')
    ap.add_argument('--pad-rows', type=int, default=40)
    ap.add_argument('--pad-cols', type=int, default=200)
    a = ap.parse_args()
    import zarr
    import numcodecs
    src = zarr.open_group(a.render, mode='r')['0']
    n, h, w = src.shape
    assert src.dtype == np.uint8, src.dtype
    H, W = h + a.pad_rows, w + a.pad_cols
    tmp = a.out + '.partial'
    if os.path.exists(tmp):
        shutil.rmtree(tmp)
    g = zarr.open_group(tmp, mode='w', zarr_format=2)
    arr = g.create_array('0', shape=(n, H, W), chunks=(n, 128, 128), dtype='uint8', fill_value=0,
                         compressors=numcodecs.Blosc(cname='lz4', clevel=3, shuffle=1),
                         chunk_key_encoding={'name': 'v2', 'separator': '/'})
    for r0 in range(0, H, 128):
        r1 = min(H, r0 + 128)
        blk = np.zeros((n, r1 - r0, W), np.uint8)
        s0, s1 = max(r0 - a.pad_rows, 0), max(r1 - a.pad_rows, 0)
        if s1 > s0:
            blk[:, (s0 + a.pad_rows) - r0:(s1 + a.pad_rows) - r0, a.pad_cols:] = np.asarray(src[:, s0:s1, :])
        arr[:, r0:r1, :] = blk
    g.attrs.update(dict(padded_render=dict(source=os.path.basename(os.path.normpath(a.render)), pad_rows=a.pad_rows,
                                           pad_cols=a.pad_cols, source_hw=[h, w], hw=[H, W])))
    if os.path.exists(a.out):
        shutil.rmtree(a.out)
    os.rename(tmp, a.out)
    print(f'{a.out}: {n} x {H} x {W}')


if __name__ == '__main__':
    main()
