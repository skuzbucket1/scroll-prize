#!/bin/bash
# Idea 2 step 1b (2026-10-13): texture of real 9.36 µm ink vs bare papyrus on PHerc0841 w00 and ag2814 (human labels),
# layers 33-7..33+9, plus a cross-segment logistic check. CPU, nice 19 (box CPU is shared). Marker TEXTURE-EXIT.
S=/home/tbienapfl/scroll-prizes; H=/mnt/nvme/scroll-prizes/data/controls9um/heldout; C=/mnt/nvme2/scroll-prizes/controls
nice -n 19 $S/villa/vesuvius/.venv/bin/python -I $S/bin/texture_signature.py $S/runs/2026-10-13_texture-signature/texture.txt \
  $C/c0841_w00_66.zarr $H/0841-w00/labels.zarr $H/0841-w00/supervision.zarr -2 -10 \
  $C/c0841_ag2814_66.zarr $H/0841-ag2814/labels.zarr $H/0841-ag2814/supervision.zarr -2 -14
echo "[$(date -Is)] TEXTURE-EXIT: $?"
