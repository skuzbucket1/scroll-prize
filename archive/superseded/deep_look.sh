#!/usr/bin/env bash
# Research plan Phase A3: four-model ink maps (ink_9um 42/43, dense_native, Hecate; Nieuwlaar's run_ink.sh) for chosen
# windings of one fit, depth tier by tier (0, +1, then -1, +2, then -2, +3). Units = (winding, model, depth), shared by
# several GPUs through claim folders. Usage: deep_look.sh <fit-id> <CUDA GPU UUID> <hecate-first|villa-first> <hec_batch> w073 ...
set -uo pipefail
case "$*" in *GPU-33b8aac6*) echo "REFUSED: GTX 1660 SUPER"; exit 97;; esac
FIT=$1; GPU=$2; ORDER=$3; HB=$4; shift 4; WS="$*"
S=~/scroll-prizes; P=/mnt/nvme/scroll-prizes/data/PHerc0191; Z=$P/renders/$FIT; M=$P/ink/$FIT/maps; C=$P/ink/$FIT/claims-a3
L=/mnt/nvme/scroll-prizes/runs/2026-10-10_deeplook-$FIT/units; mkdir -p $M $C $L
export CUDA_VISIBLE_DEVICES=$GPU CKPT_DIR=$S/checkpoints/ckpt343 PY=$S/villa/vesuvius/.venv/bin/python HECATE_PY=$S/checkpoints/ckpt343/hecate.py \
       PREP_PY=$S/bin/ink343/hecate_prep.py N_LAYERS=66 NATIVE_UM=9.362 VILLA_BATCH=4 HEC_BATCH=$HB HEC_DEVICE=cuda TMPDIR=/mnt/nvme/scroll-prizes/scratch
if [ "$ORDER" = hecate-first ]; then MS="hecate hybrid_3d2d-seed42 hybrid_3d2d-seed43 dnative"; else MS="hybrid_3d2d-seed42 hybrid_3d2d-seed43 dnative hecate"; fi
have() { local w=$1 m=$2 d=$3; if [ $m = hecate ]; then local f=$M/${w}__hecate__L66zc$(awk -v d=$d 'BEGIN{printf "%.2f", 32.5 + d}'); [ -s $f.png ] && [ -s ${f}_reverse.png ];
         else local f=$M/${w}__${m}__L66s$((25 + d)); [ -s $f.tif ] && [ -s ${f}_reverse.tif ]; fi; }
cd $S/villa/vesuvius
for d in 0 1 -1 2 -2 3; do for w in $WS; do for m in $MS; do
  have $w $m $d && continue
  [ -d $Z/$w.zarr/0 ] || { echo "no render $w"; continue; }
  mkdir $C/${w}_${m}_d${d} 2>/dev/null || continue; echo $GPU > $C/${w}_${m}_d${d}/gpu
  t0=$(date +%s); bash $S/bin/ink343/run_ink.sh $Z/$w.zarr $m $d $M > $L/${w}_${m}_d${d}.log 2>&1; rc=$?
  have $w $m $d && st=ok || { st=FAILED; rmdir $C/${w}_${m}_d${d} 2>/dev/null; rm -f $C/${w}_${m}_d${d}/gpu; rmdir $C/${w}_${m}_d${d} 2>/dev/null; }
  echo "[$(date -Is)] $w $m d$d rc=$rc $st $(( $(date +%s) - t0 ))s"
done; done; done
echo "DEEPLOOK-EXIT: 0"
