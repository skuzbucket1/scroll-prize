#!/bin/bash
# Project the 3D damage fields onto every PHerc0813 z12000 winding of the triage set and report (idea 3, 2026-10-13).
# Waits for DAMAGE3D-EXIT. CPU, nice 19. Marker PROJECT-EXIT in project.log.
S=/home/tbienapfl/scroll-prizes; R=/mnt/nvme/scroll-prizes/runs/2026-10-13_damage3d; PY="nice -n 19 $S/villa/vesuvius/.venv/bin/python -I"
P=/mnt/nvme/scroll-prizes/data/PHerc0813; T=$S/runs/2026-10-13_damage-map/tiles_v2
until grep -q DAMAGE3D-EXIT $R/run.log 2>/dev/null; do sleep 30; done
W=$(ls $T/n_0813_w*.npz | sed 's/.*n_0813_//; s/.npz//' | tr '\n' ' ')
$PY $S/bin/damage3d_project.py $R/fields.zarr $P/inputs/spiral-dataset/umbilicus.json $P/geometry/exp30k-z12000 $T 9.362 $R/proj $W --png
$PY $S/bin/damage3d_project.py report $R/proj --flags $R/flags_0813.tsv
echo "[$(date -Is)] PROJECT-EXIT"
