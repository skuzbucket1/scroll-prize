#!/bin/bash
# Idea 1 (Ted 2026-10-13: "yes to 1", on the box): take the papyrus weave out of the CT and see whether the known letters
# show (PHerc. 343: Nieuwlaar's letters, 8.64 µm; PHerc0841 ag2814 and w00: human labels, 9.366 µm). CPU, nice 19.
# Marker DEWEAVE-EXIT in run.log.
S=/home/tbienapfl/scroll-prizes; R=$S/runs/2026-10-13_deweave; PY="nice -n 19 $S/villa/vesuvius/.venv/bin/python -I"
D=/mnt/nvme/scroll-prizes/data; H=$D/controls9um/heldout; C=/mnt/nvme2/scroll-prizes/controls
cd $R
$PY $S/bin/deweave.py $D/PHerc0343/control/control343_66.zarr control343_66 8.64 $R --masks343 $S/runs/2026-10-12_ct-ink-signature/masks.npz \
  --maps $D/PHerc0343/ink/control/maps
$PY $S/bin/deweave.py $C/c0841_ag2814_66.zarr c0841_ag2814_66 9.366 $R --labels $H/0841-ag2814/labels.zarr --sup $H/0841-ag2814/supervision.zarr \
  --maps $D/controls9um/c0841_ag2814/maps
$PY $S/bin/deweave.py $C/c0841_w00_66.zarr c0841_w00_66 9.366 $R --labels $H/0841-w00/labels.zarr --sup $H/0841-w00/supervision.zarr --maps $H/maps
echo "[$(date -Is)] DEWEAVE-EXIT"
