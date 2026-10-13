#!/bin/bash
# Six-model agreement on known 9.36 µm text (2026-10-13, Ted: "yes to step 1"): PHerc0841 ag2814 and w00, the two
# controls with human ink labels. Five of the six models' d +1 maps already exist (the stroke-score control runs); Hecate
# is added at d +1 on GPU 0 (GPU 1 = z8000 band, GPU 2 = the 8.64 µm model's evaluation). Hecate may have trained on
# PHerc0841 (control notes), so summary.py also gives the rule without it. Marker AGREE-0841-EXIT in run.log.
S=/home/tbienapfl/scroll-prizes; R=$S/runs/2026-10-13_agreement-0841; PY=$S/villa/vesuvius/.venv/bin/python
H=/mnt/nvme/scroll-prizes/data/controls9um/heldout; C=/mnt/nvme2/scroll-prizes/controls
cd $R
for n in ag2814 w00; do
  name=c0841_${n}_66; M=$R/maps_$name; mkdir -p $M
  if [ $n = ag2814 ]; then src=/mnt/nvme/scroll-prizes/data/controls9um/c0841_ag2814/maps; else src=$H/maps; fi
  for f in $src/${name}__*__L66s26*.tif; do ln -sf $f $M/; done
  (cd $S/villa/vesuvius && CUDA_VISIBLE_DEVICES=GPU-2d9651e9-5a94-e0cb-6a99-9300d8056524 TORCHDYNAMO_DISABLE=1 \
     CKPT_DIR=$S/checkpoints/ckpt343 PY=$PY HECATE_PY=$S/checkpoints/ckpt343/hecate.py PREP_PY=$S/bin/ink343/hecate_prep.py \
     N_LAYERS=66 NATIVE_UM=9.366 HEC_BATCH=8 HEC_DEVICE=cuda TMPDIR=/mnt/nvme/scroll-prizes/tmp MODELS=hecate \
     bash $S/bin/ink343/run_depth_sweep.sh $C/$name.zarr $M 1 1 > $R/sweep_$name.log 2>&1)
  $PY -I $R/label_boxes.py $H/0841-$n/labels.zarr $H/0841-$n/supervision.zarr $C/$name.zarr 9.366 $R/boxes_$name.json
  nice -n 5 $PY -I $S/bin/model_agreement.py $C/$name.zarr $M $name 1 $R/agree_${name}_d1.tsv --boxes $R/boxes_$name.json \
    --label $name >> $R/agreement.log 2>&1
done
$PY -I $R/summary.py > $R/summary.txt 2>&1
echo "[$(date -Is)] AGREE-0841-EXIT"
