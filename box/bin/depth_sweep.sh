#!/usr/bin/env bash
# Depth sweep (d = -15..+15) of the four 9 um ink models on a 66-layer render, using Nieuwlaar's scripts (bin/ink343).
# Usage: depth_sweep.sh <surface_66.zarr> <out_dir> <CUDA GPU UUID> [DMIN=-15] [DMAX=15]
set -uo pipefail
case "$*" in *GPU-33b8aac6*) echo "REFUSED: GTX 1660 SUPER" >&2; exit 97;; esac
Z=$1; OUT=$2; export CUDA_VISIBLE_DEVICES=$3; DMIN=${4:--15}; DMAX=${5:-15}
S=~/scroll-prizes
export CKPT_DIR=$S/checkpoints/ckpt343 PY=$S/villa/vesuvius/.venv/bin/python HECATE_PY=$S/checkpoints/ckpt343/hecate.py PREP_PY=$S/bin/ink343/hecate_prep.py
export N_LAYERS=66 NATIVE_UM=9.362 VILLA_BATCH=4 HEC_BATCH=4 HEC_DEVICE=cuda TMPDIR=/mnt/nvme/scroll-prizes/tmp P_VILLA=1 P_HEC=1
mkdir -p "$TMPDIR" "$OUT"
cd $S/villa/vesuvius   # so `python -m vesuvius...` resolves the editable package
t0=$(date +%s)
bash $S/bin/ink343/run_depth_sweep.sh "$Z" "$OUT" "$DMIN" "$DMAX"; rc=$?
echo "[$(date -Is)] sweep rc=$rc in $(( $(date +%s)-t0 ))s"; echo "SWEEP-EXIT: $rc"
