#!/usr/bin/env python3
"""merge_tile_phase.py - merge the ink maps of the plain and the padded render of the joined mesh.

    python merge_tile_phase.py --plain <maps_dir> --plain-name <name> --padded <maps_dir> --padded-name <name> \
        --node-source <..._node_source.npz> --out <dir> --out-name concat_w047-w048_R5B2_z9500-11000 \
        [--pad-rows 40] [--pad-cols 200]

For every map (model, depth, direction): pixels of w047 nodes (original and transition strip; node source 1 or 4)
come from the padded run, cropped back to the plain frame; all other pixels (w048, bridge) from the plain run.
One node = 20 x 20 render px. Hecate maps are on the 9.6 um grid (0.9 x); the w047 mask is resized to them with
nearest neighbour. Map names follow run_ink.sh: <name>__<model>__L66s<s>[_reverse].tif and
<name>__hecate__L66zc<zc>[_reverse].png; output names use --out-name, as ensemble_maps.py expects.
"""
import argparse
import glob
import json
import os

import numpy as np


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--plain', required=True); ap.add_argument('--plain-name', required=True)
    ap.add_argument('--padded', required=True); ap.add_argument('--padded-name', required=True)
    ap.add_argument('--node-source', required=True)
    ap.add_argument('--out', required=True); ap.add_argument('--out-name', required=True)
    ap.add_argument('--pad-rows', type=int, default=40); ap.add_argument('--pad-cols', type=int, default=200)
    a = ap.parse_args()
    import tifffile
    import cv2
    os.makedirs(a.out, exist_ok=True)
    source = np.load(a.node_source)['source']
    source_px = np.repeat(np.repeat(source, 20, 0), 20, 1)     # node (i, j) -> px [20i, 20i+20) x [20j, 20j+20)
    is47 = (source_px == 1) | (source_px == 4)
    log = dict(w047_px=int(is47.sum()), maps=[])
    for fa in sorted(glob.glob(os.path.join(a.plain, f'{a.plain_name}__*'))):
        b = os.path.basename(fa)
        if not (b.endswith('.tif') or b.endswith('.png')):
            continue
        rest = b[len(a.plain_name) + 2:]
        fp = os.path.join(a.padded, f'{a.padded_name}__{rest}')
        if not os.path.exists(fp):
            log['maps'].append(dict(name=rest, error='padded map missing')); continue
        if b.endswith('.tif'):
            ma, mp = tifffile.imread(fa), tifffile.imread(fp)
            mp = mp[a.pad_rows:a.pad_rows + ma.shape[0], a.pad_cols:a.pad_cols + ma.shape[1]]
            m47 = is47[:ma.shape[0], :ma.shape[1]]
            tifffile.imwrite(os.path.join(a.out, f'{a.out_name}__{rest}'), np.where(m47, mp, ma).astype(ma.dtype))
        else:                                                   # Hecate .png on the 9.6 um grid
            ma, mp = cv2.imread(fa, cv2.IMREAD_UNCHANGED), cv2.imread(fp, cv2.IMREAD_UNCHANGED)
            dr, dc = mp.shape[0] - ma.shape[0], mp.shape[1] - ma.shape[1]
            assert (dr, dc) == (round(a.pad_rows * 0.9), round(a.pad_cols * 0.9)), (b, ma.shape, mp.shape)
            mp = mp[dr:, dc:]
            m47 = cv2.resize(is47.astype(np.uint8), (ma.shape[1], ma.shape[0]), interpolation=cv2.INTER_NEAREST).astype(bool)
            cv2.imwrite(os.path.join(a.out, f'{a.out_name}__{rest}'), np.where(m47, mp, ma).astype(ma.dtype))
            js = fa[:-4] + '.json'
            if os.path.exists(js):
                open(os.path.join(a.out, f'{a.out_name}__{rest[:-4]}.json'), 'w').write(open(js).read())
        log['maps'].append(dict(name=rest, w047_fraction=round(float(m47.mean()), 4)))
    json.dump(log, open(os.path.join(a.out, 'merge.json'), 'w'), indent=1)
    print(f"{len(log['maps'])} maps merged -> {a.out}")


if __name__ == '__main__':
    main()
