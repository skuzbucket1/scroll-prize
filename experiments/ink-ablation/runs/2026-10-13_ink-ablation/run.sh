#!/bin/bash
# Idea 2, step 1 (2026-10-13): what do the models respond to on PHerc0841's real letters? ink_ablation.py with
# dense_native and Reader v2 on w00 (label shift -2,-10) and ag2814 (-2,-14), GPU 2 after the 3D damage v1 chain.
# Marker ABLATION-EXIT in run.log.
S=/home/tbienapfl/scroll-prizes; R=$S/runs/2026-10-13_ink-ablation; H=/mnt/nvme/scroll-prizes/data/controls9um/heldout
C=/mnt/nvme2/scroll-prizes/controls; SCR=/mnt/nvme2/scroll-prizes/scratch/ablation; mkdir -p $R $SCR
until grep -q PROJECT-V1-EXIT /mnt/nvme/scroll-prizes/runs/2026-10-13_damage3d/run_v1.log 2>/dev/null; do sleep 30; done
export CUDA_VISIBLE_DEVICES=GPU-7937f33e-73c8-2a4f-d7c6-9c4c3c20c74f TORCHDYNAMO_DISABLE=1
PY="nice -n 5 $S/villa/vesuvius/.venv/bin/python -I"
for seg in "w00 -2 -10" "ag2814 -2 -14"; do set -- $seg
  for m in dense_native readerv2; do
    case $m in dense_native) CK=$S/checkpoints/ckpt343/dense_native-016000.pth;; readerv2) CK=$S/checkpoints/ckpt343/reader-v2-step040000.pth;; esac
    [ -f "$CK" ] || { echo "no checkpoint for $m"; continue; }
    $PY $S/bin/ink_ablation.py $C/c0841_$1_66.zarr $H/0841-$1/labels.zarr $H/0841-$1/supervision.zarr 9.366 $2 $3 $CK $SCR/$1_$m $R/ablation_$1_$m.json > $R/ablation_$1_$m.log 2>&1
  done
done
rm -rf $SCR
echo "[$(date -Is)] ABLATION-EXIT"
