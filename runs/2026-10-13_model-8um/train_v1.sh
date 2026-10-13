#!/bin/bash
# 8.64 µm fine-tune v1 (Ted 2026-10-13 "start the 8.64 model"): train_v1.json on GPU 0 (GPU 1 = z8000 band). Marker TRAIN-V1-EXIT.
cd ~/scroll-prizes/villa/vesuvius
CUDA_VISIBLE_DEVICES=GPU-2d9651e9-5a94-e0cb-6a99-9300d8056524 .venv/bin/python -m vesuvius.ink_detection.training.train ~/scroll-prizes/runs/2026-10-13_model-8um/train_v1.json
echo "[$(date -Is)] TRAIN-V1-EXIT: $?"
