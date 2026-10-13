#!/bin/bash
# Evaluate the 8.64 µm fine-tune v1 when training ends (GPU 2; GPU 0 trains, GPU 1 = z8000 band). Marker EVAL-V1-EXIT.
S=~/scroll-prizes; R=$S/runs/2026-10-13_model-8um
until grep -q TRAIN-V1-EXIT $R/train_v1.log 2>/dev/null; do sleep 60; done
LAST=$(ls $R/out_v1/ckpt_*.pth 2>/dev/null | sort | tail -1)
CUDA_VISIBLE_DEVICES=GPU-7937f33e-73c8-2a4f-d7c6-9c4c3c20c74f TORCHDYNAMO_DISABLE=1 nice -n 5 $S/villa/vesuvius/.venv/bin/python $R/eval_8um.py $R/eval_v1 \
  dense_native=$S/checkpoints/ckpt343/dense_native-016000.pth ft_best=$R/out_v1/best_val_balanced_accuracy.pth ft_last=$LAST
echo "[$(date -Is)] EVAL-V1-EXIT: $?"
