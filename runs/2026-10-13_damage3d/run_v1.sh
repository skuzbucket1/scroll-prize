#!/bin/bash
# 3D damage v1 (2026-10-13): fields recomputed with the layer normal stored (EZ/EY/EX), then the projection along each
# mesh's own normal instead of the radial direction (v0 assumed radial sheets; in this crushed scroll the median
# alignment was only 0.74). GPU 2 for the fields, CPU for the projection. Markers DAMAGE3D-V1-EXIT, PROJECT-V1-EXIT.
S=/home/tbienapfl/scroll-prizes; R=/mnt/nvme/scroll-prizes/runs/2026-10-13_damage3d; P=/mnt/nvme/scroll-prizes/data/PHerc0813
T=$S/runs/2026-10-13_damage-map/tiles_v2; PY="nice -n 19 $S/villa/vesuvius/.venv/bin/python -I"
mv $R/fields.zarr $R/fields_v0.zarr 2>/dev/null; mv $R/proj $R/proj_v0 2>/dev/null
cd $S/villa/vesuvius
CUDA_VISIBLE_DEVICES=GPU-7937f33e-73c8-2a4f-d7c6-9c4c3c20c74f nice -n 5 .venv/bin/python -I $S/bin/damage3d.py \
  $P/source/volume/20250821151723-9.362um-1.2m-113keV-masked.zarr $P/inputs/spiral-dataset/umbilicus.json 11998 13001 $R
rc=$?; echo "[$(date -Is)] DAMAGE3D-V1-EXIT: $rc"; [ $rc -ne 0 ] && exit $rc
W=$(ls $T/n_0813_w*.npz | sed 's/.*n_0813_//; s/.npz//' | tr '\n' ' ')
$PY $S/bin/damage3d_project.py $R/fields.zarr $P/inputs/spiral-dataset/umbilicus.json $P/geometry/exp30k-z12000 $T 9.362 $R/proj $W --png
$PY $S/bin/damage3d_project.py report $R/proj --flags $R/flags_0813.tsv
echo "[$(date -Is)] PROJECT-V1-EXIT"
