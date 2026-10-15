#!/usr/bin/env bash
# Depth sweep (d = -15..+15) of the four 9 um ink models on a 66-layer render, using Nieuwlaar's scripts (bin/ink343).
# Usage: depth_sweep.sh <surface_66.zarr> <out_dir> <CUDA GPU UUID> [DMIN=-15] [DMAX=15]
set -uo pipefail
case "$*" in *GPU-33b8aac6*) echo "REFUSED: GTX 1660 SUPER" >&2; exit 97;; esac
Z=$1; OUT=$2; export CUDA_VISIBLE_DEVICES=$3; DMIN=${4:--15}; DMAX=${5:-15}
S=~/scroll-prizes
export CKPT_DIR=$S/checkpoints/ckpt343 PY=$S/villa/vesuvius/.venv/bin/python HECATE_PY=$S/checkpoints/ckpt343/hecate.py PREP_PY=$S/bin/ink343/hecate_prep.py
export N_LAYERS=66 NATIVE_UM=${NATIVE_UM:?set NATIVE_UM to the scan voxel size in um} VILLA_BATCH=4 HEC_BATCH=4 HEC_DEVICE=cuda TMPDIR=${TMPDIR_INK:-/mnt/nvme/scroll-prizes/work/tmp} P_VILLA=1 P_HEC=1
mkdir -p "$TMPDIR" "$OUT"
cd $S/villa/vesuvius   # so `python -m vesuvius...` resolves the editable package
t0=$(date +%s)
bash $S/bin/ink343/run_depth_sweep.sh "$Z" "$OUT" "$DMIN" "$DMAX"; nrc=$?
# Nieuwlaar's script counts failures over the out dir's whole timings.tsv, which every render written there shares, so one
# failed winding made every later sweep report 1. Judge this render by its own maps instead (audit B6, 2026-10-15).
# (Its per-job logs, logs/<model>_d<d>.log, are also shared: with several workers on one out dir they hold the latest job.)
NAME=$(basename "$Z" .zarr); miss=0
for d in $(seq $DMIN $DMAX); do for m in ${MODELS:-dnative hybrid_3d2d-seed42 hybrid_3d2d-seed43 hecate}; do
  if [ $m = hecate ]; then f=$OUT/${NAME}__hecate__L66zc$(awk -v d=$d 'BEGIN{printf "%.2f", 32.5 + d}'); e=png
  else f=$OUT/${NAME}__${m}__L66s$(( 25 + d )); e=tif; fi
  for g in $f.$e ${f}_reverse.$e; do [ -s $g ] || { miss=$((miss + 1)); echo "missing $(basename $g)"; }; done
done; done
[ $miss -eq 0 ] && rc=0 || rc=1
echo "[$(date -Is)] sweep rc=$rc ($miss maps missing; run_depth_sweep rc $nrc) in $(( $(date +%s)-t0 ))s"; echo "SWEEP-EXIT: $rc"; exit $rc
