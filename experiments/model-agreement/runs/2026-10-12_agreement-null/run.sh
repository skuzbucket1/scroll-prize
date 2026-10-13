#!/bin/bash
# Six-model agreement test, the 9.362 µm comparison (Ted approved 2026-10-12: GPUs 0 and 2 for the new model and the
# agreement test): on 343's letters >= 5 of 6 models were one-sided on 78 % of the letters, on its bare papyrus 10 %,
# on the w079 window 25 %. Here: clean papyrus on PHerc0813 (z 12,000-13,000) and PHerc0191 (z 11,200-12,200), three
# windings each, one 14 x 8 mm window per winding (the window with the fewest dark CT voids), cropped with a 256 px
# margin like the w079 deep look; six models at d 0..+2 on GPU 0 once the w079 deep look is done; then
# model_agreement.py. Markers in run.log: CROPS-DONE, AGREE-NULL-EXIT.
S=~/scroll-prizes; R=$S/runs/2026-10-12_agreement-null; PY=$S/villa/vesuvius/.venv/bin/python
GPU=GPU-2d9651e9-5a94-e0cb-6a99-9300d8056524
until grep -q DEEPLOOK-EXIT $S/runs/2026-10-12_deeplook-0813-w079/run2.log 2>/dev/null; do sleep 120; done
$PY - <<'EOF'
import numpy as np, zarr, os
R = os.path.expanduser('~/scroll-prizes/runs/2026-10-12_agreement-null')
picks = [('PHerc0813', 'exp30k-z12000', w) for w in ('w096', 'w102', 'w106')] + [('PHerc0191', 'exp30k-z11200', w) for w in ('w040', 'w060', 'w100')]
h, w_, m = 854, 1495, 256
with open(f'{R}/crops.tsv', 'w') as fo:
    fo.write('name\tscroll\tfit\twinding\ty0\tx0\tvoid_share\n')
    for sc, fit, w in picks:
        src = zarr.open(f'/mnt/nvme/scroll-prizes/data/{sc}/renders/{fit}/{w}.zarr', mode='r')['0']
        ct = np.asarray(src[33]); H, W = ct.shape; v = ct > 0; nz = ct[v]; dark = (ct < 0.5 * np.median(nz)) & v
        best = None
        for y in range(m, H - h - m, 64):
            for x in range(m, W - w_ - m, 128):
                if v[y - m:y + h + m, x - m:x + w_ + m].mean() < 0.97:
                    continue
                s = dark[y:y + h, x:x + w_].mean()
                if best is None or s < best[0]:
                    best = (s, y, x)
        if best is None:
            print('no clean window in', sc, w); continue
        s, y, x = best; name = f'{sc}_{w}_null'
        a = np.asarray(src[:, y - m:y + h + m, x - m:x + w_ + m])
        g = zarr.open_group(f'{R}/{name}.zarr', mode='w', zarr_format=2)
        g.create_array('0', shape=a.shape, chunks=(66, 256, 256), dtype='u1', fill_value=0)[:] = a
        fo.write(f'{name}\t{sc}\t{fit}\t{w}\t{y}\t{x}\t{s:.4f}\n'); print(name, 'window y', y, 'x', x, 'void share', round(s, 4), flush=True)
EOF
echo "[$(date -Is)] CROPS-DONE"
export CUDA_VISIBLE_DEVICES=$GPU TORCHDYNAMO_DISABLE=1 CKPT_DIR=$S/checkpoints/ckpt343 PY HECATE_PY=$S/checkpoints/ckpt343/hecate.py \
  PREP_PY=$S/bin/ink343/hecate_prep.py N_LAYERS=66 NATIVE_UM=9.362 VILLA_BATCH=16 HEC_BATCH=8 HEC_DEVICE=cuda \
  TMPDIR=/mnt/nvme/scroll-prizes/tmp P_VILLA=1 P_HEC=1 MODELS="dnative hybrid_3d2d-seed42 hybrid_3d2d-seed43 hecate readerv2 d9v4c"
cd $S/villa/vesuvius
for z in $R/*_null.zarr; do
  n=$(basename $z .zarr); mkdir -p $R/maps_$n
  bash $S/bin/ink343/run_depth_sweep.sh $z $R/maps_$n 0 2 > $R/sweep_$n.log 2>&1
  for d in 0 1 2; do
    nice -n 5 $PY $S/bin/model_agreement.py $z $R/maps_$n $n $d $R/agree_${n}_d$d.tsv --window 256 256 854 1495 --label $n >> $R/agreement.log 2>&1
  done
done
echo "[$(date -Is)] AGREE-NULL-EXIT"
