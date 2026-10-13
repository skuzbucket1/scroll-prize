#!/bin/bash
# 3D damage fields for the PHerc0813 z12000 band (idea 3, 2026-10-13): damage3d.py on GPU 2 at CT level 2. Marker DAMAGE3D-EXIT.
cd /home/tbienapfl/scroll-prizes/villa/vesuvius
CUDA_VISIBLE_DEVICES=GPU-7937f33e-73c8-2a4f-d7c6-9c4c3c20c74f nice -n 5 .venv/bin/python -I /home/tbienapfl/scroll-prizes/bin/damage3d.py   /mnt/nvme/scroll-prizes/data/PHerc0813/source/volume/20250821151723-9.362um-1.2m-113keV-masked.zarr   /mnt/nvme/scroll-prizes/data/PHerc0813/inputs/spiral-dataset/umbilicus.json 11998 13001 /mnt/nvme/scroll-prizes/runs/2026-10-13_damage3d
rc=$?; echo "[$(date -Is)] DAMAGE3D-EXIT: $rc"
