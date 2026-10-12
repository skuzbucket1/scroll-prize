"""Plan an ink-first sweep of a whole scroll: tile the level-0 volume into blocks, keep the blocks the scroll fills.
Occupancy comes from a coarse pyramid level of the masked CT (voxels > 0 are papyrus or air inside the scroll mask).
Blocks are `block` voxels with `margin` overlap on each side, so their usable centres (ink-first samples points at least
`margin` from a block edge) tile the scroll without gaps.
Usage: inkfirst_plan.py <CT zarr URL> <out dir> [--level 5] [--block 1280] [--margin 48] [--min-occ 0.25]
Writes <out>/blocks.tsv (id z0 z1 y0 y1 x0 x1 occupancy) and <out>/plan.png (top and side views with the blocks)."""
import argparse, json, os, sys
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ink-first-src'))
from ink_first.fetch import fetch_block
import zarr

ap = argparse.ArgumentParser()
ap.add_argument('url'); ap.add_argument('out'); ap.add_argument('--level', type=int, default=5)
ap.add_argument('--block', type=int, default=1280); ap.add_argument('--margin', type=int, default=48)
ap.add_argument('--min-occ', type=float, default=0.25)
a = ap.parse_args()
os.makedirs(a.out, exist_ok=True); store = os.path.join(a.out, 'coarse.zarr'); lv = str(a.level); f = 2 ** a.level
import urllib.request
shape0 = json.loads(urllib.request.urlopen(a.url.rstrip('/') + '/0/.zarray', timeout=60).read())['shape']
shp = json.loads(urllib.request.urlopen(a.url.rstrip('/') + f'/{lv}/.zarray', timeout=60).read())['shape']
fetch_block(a.url, store, lv, (0, shp[0], 0, shp[1], 0, shp[2]), threads=16)
C = np.asarray(zarr.open(store, mode='r')[lv]) > 0
step = a.block - 2 * a.margin; rows = []
for z0 in range(0, shape0[0] - 2 * a.margin, step):
    for y0 in range(0, shape0[1] - 2 * a.margin, step):
        for x0 in range(0, shape0[2] - 2 * a.margin, step):
            z1, y1, x1 = min(z0 + a.block, shape0[0]), min(y0 + a.block, shape0[1]), min(x0 + a.block, shape0[2])
            occ = C[z0 // f:max(z1 // f, z0 // f + 1), y0 // f:max(y1 // f, y0 // f + 1), x0 // f:max(x1 // f, x0 // f + 1)].mean()
            if occ >= a.min_occ:
                rows.append((f'b{len(rows):04d}', z0, z1, y0, y1, x0, x1, round(float(occ), 3)))
with open(os.path.join(a.out, 'blocks.tsv'), 'w') as o:
    o.write('id\tz0\tz1\ty0\ty1\tx0\tx1\toccupancy\n')
    for r in rows:
        o.write('\t'.join(map(str, r)) + '\n')
vox = sum((r[2] - r[1]) * (r[4] - r[3]) * (r[6] - r[5]) for r in rows)
print(f'volume {shape0} (level {lv}: {list(C.shape)}), scroll fills {C.mean():.1%} of the box; {len(rows)} blocks of {a.block}^3 '
      f'(step {step}) with occupancy >= {a.min_occ}; {vox / 1e9:.0f} G voxels to read')
try:
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 2, figsize=(12, 7), facecolor='#161616')
    mz = C.shape[0] // 2
    ax[0].imshow(C[mz], cmap='gray'); ax[0].set_title(f'from above, z {mz * f}', color='#ddd')
    ax[1].imshow(C[:, C.shape[1] // 2, :], cmap='gray', aspect='auto'); ax[1].set_title('from the side, through the centre', color='#ddd')
    for r in rows:
        if r[1] <= mz * f < r[2]:
            ax[0].add_patch(plt.Rectangle((r[5] / f, r[3] / f), (r[6] - r[5]) / f, (r[4] - r[3]) / f, fill=False, ec='#E69F00', lw=0.6))
        if r[3] <= (C.shape[1] // 2) * f < r[4]:
            ax[1].add_patch(plt.Rectangle((r[5] / f, r[1] / f), (r[6] - r[5]) / f, (r[2] - r[1]) / f, fill=False, ec='#56B4E9', lw=0.6))
    for x in ax:
        x.set_xticks([]); x.set_yticks([])
    fig.savefig(os.path.join(a.out, 'plan.png'), dpi=90, facecolor=fig.get_facecolor(), bbox_inches='tight')
except Exception as e:
    print('no plan figure:', e)
