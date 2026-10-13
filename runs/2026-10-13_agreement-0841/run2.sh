#!/bin/bash
# Second 9.36 µm known-text test for the agreement rule (2026-10-13): PHerc0139 w047 (reference = the 2.4 µm ink
# prediction; d9v4C trained on it, so five models). Waits for AGREE-0841-EXIT, then Reader v2 + Hecate at d +1 on GPU 0
# (dnative and ink_9um x2 maps exist), letter tiles from the reference, agreement, summary. Marker AGREE-0139-EXIT.
S=/home/tbienapfl/scroll-prizes; R=$S/runs/2026-10-13_agreement-0841; PY=$S/villa/vesuvius/.venv/bin/python
H=/mnt/nvme/scroll-prizes/data/controls9um; C=/mnt/nvme2/scroll-prizes/controls; n=c0139_w047_66; M=$R/maps_$n
until grep -q AGREE-0841-EXIT $R/run.log 2>/dev/null; do sleep 60; done
cd $R; mkdir -p $M
for f in $H/c0139_w047/maps/${n}__*__L66s26*.tif; do ln -sf $f $M/; done
(cd $S/villa/vesuvius && CUDA_VISIBLE_DEVICES=GPU-2d9651e9-5a94-e0cb-6a99-9300d8056524 TORCHDYNAMO_DISABLE=1 \
   CKPT_DIR=$S/checkpoints/ckpt343 PY=$PY HECATE_PY=$S/checkpoints/ckpt343/hecate.py PREP_PY=$S/bin/ink343/hecate_prep.py \
   N_LAYERS=66 NATIVE_UM=9.362 VILLA_BATCH=16 HEC_BATCH=8 HEC_DEVICE=cuda TMPDIR=/mnt/nvme/scroll-prizes/tmp MODELS="readerv2 hecate" \
   bash $S/bin/ink343/run_depth_sweep.sh $C/$n.zarr $M 1 1 > $R/sweep_$n.log 2>&1)
$PY -I $R/label_boxes.py $H/heldout/0139-w047/reference.tif - $C/$n.zarr 9.362 $R/boxes_$n.json
nice -n 5 $PY -I $S/bin/model_agreement.py $C/$n.zarr $M $n 1 $R/agree_${n}_d1.tsv --boxes $R/boxes_$n.json --label $n \
  --models dnative,hybrid_3d2d-seed42,hybrid_3d2d-seed43,hecate,readerv2 >> $R/agreement.log 2>&1
$PY -I $R/summary.py > $R/summary.txt 2>&1
echo "[$(date -Is)] AGREE-0139-EXIT"
