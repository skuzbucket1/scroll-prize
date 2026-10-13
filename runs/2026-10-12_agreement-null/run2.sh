#!/bin/bash
# Six-model agreement test on clean 9.362 µm papyrus, second start (2026-10-13 ~00:10 CT). run.sh found no window: it
# asked for the window plus its 256 px margin to be 97 % inside the strip, which these ragged strips never are, and its
# loop then ran on an unmatched glob. Now: the 14 x 8 mm window itself at least 90 % inside the strip (the margin may run
# off the edge, as in the w079 crop), the fewest dark CT voids among those, and PHerc0813 crops on GPU 0, PHerc0191 crops
# on GPU 2 in parallel. Markers in run2.log: CROPS-DONE, AGREE-NULL-EXIT.
S=~/scroll-prizes; R=$S/runs/2026-10-12_agreement-null; PY=$S/villa/vesuvius/.venv/bin/python
shopt -s nullglob
$PY - <<'EOF'
import numpy as np, zarr, os
R = os.path.expanduser('~/scroll-prizes/runs/2026-10-12_agreement-null')
picks = [('PHerc0813', 'exp30k-z12000', w) for w in ('w096', 'w102', 'w106')] + [('PHerc0191', 'exp30k-z11200', w) for w in ('w040', 'w060', 'w100')]
h, w_, m = 854, 1495, 256
with open(f'{R}/crops.tsv', 'w') as fo:
    fo.write('name\tscroll\tfit\twinding\ty0\tx0\twindow_valid\tvoid_share\n')
    for sc, fit, w in picks:
        src = zarr.open(f'/mnt/nvme/scroll-prizes/data/{sc}/renders/{fit}/{w}.zarr', mode='r')['0']
        ct = np.asarray(src[33]); H, W = ct.shape; v = ct > 0; nz = ct[v]; dark = (ct < 0.5 * np.median(nz)) & v
        best = None
        for y in range(0, H - h + 1, 32):
            for x in range(0, W - w_ + 1, 64):
                vv = v[y:y + h, x:x + w_].mean()
                if vv < 0.9:
                    continue
                s = dark[y:y + h, x:x + w_][v[y:y + h, x:x + w_]].mean()
                if best is None or s < best[0]:
                    best = (s, y, x, vv)
        if best is None:
            print('no clean window in', sc, w, flush=True); continue
        s, y, x, vv = best; name = f'{sc}_{w}_null'
        Y0, X0 = max(0, y - m), max(0, x - m)
        a = np.asarray(src[:, Y0:min(H, y + h + m), X0:min(W, x + w_ + m)])
        g = zarr.open_group(f'{R}/{name}.zarr', mode='w', zarr_format=2)
        g.create_array('0', shape=a.shape, chunks=(66, 256, 256), dtype='u1', fill_value=0)[:] = a
        fo.write(f'{name}\t{sc}\t{fit}\t{w}\t{y}\t{x}\t{vv:.3f}\t{s:.4f}\n')
        open(f'{R}/{name}.window', 'w').write(f'{y - Y0} {x - X0} {h} {w_}\n')       # window inside the crop
        print(name, 'window y', y, 'x', x, 'valid', round(vv, 3), 'void share', round(s, 4), flush=True)
EOF
echo "[$(date -Is)] CROPS-DONE"
export TORCHDYNAMO_DISABLE=1 CKPT_DIR=$S/checkpoints/ckpt343 PY HECATE_PY=$S/checkpoints/ckpt343/hecate.py \
  PREP_PY=$S/bin/ink343/hecate_prep.py N_LAYERS=66 NATIVE_UM=9.362 VILLA_BATCH=16 HEC_BATCH=8 HEC_DEVICE=cuda \
  TMPDIR=/mnt/nvme/scroll-prizes/tmp P_VILLA=1 P_HEC=1 MODELS="dnative hybrid_3d2d-seed42 hybrid_3d2d-seed43 hecate readerv2 d9v4c"
worker(){   # GPU UUID, crops...
  local gpu=$1; shift
  for z in "$@"; do
    local n=$(basename $z .zarr); mkdir -p $R/maps_$n
    (cd $S/villa/vesuvius && CUDA_VISIBLE_DEVICES=$gpu bash $S/bin/ink343/run_depth_sweep.sh $z $R/maps_$n 0 2 > $R/sweep_$n.log 2>&1)
    for d in 0 1 2; do
      nice -n 5 $PY $S/bin/model_agreement.py $z $R/maps_$n $n $d $R/agree_${n}_d$d.tsv --window $(cat $R/$n.window) --label $n >> $R/agreement.log 2>&1
    done
  done
}
rm -rf $R/maps_\*_null $R/sweep_\*_null.log
worker GPU-2d9651e9-5a94-e0cb-6a99-9300d8056524 $R/PHerc0813_*_null.zarr &
worker GPU-7937f33e-73c8-2a4f-d7c6-9c4c3c20c74f $R/PHerc0191_*_null.zarr &
wait
echo "[$(date -Is)] AGREE-NULL-EXIT"
