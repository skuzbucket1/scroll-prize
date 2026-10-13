#!/usr/bin/env bash
# Research plan Phase A4: three-model ink maps (ink_9um seeds 42/43 + dense_native, Nieuwlaar's run_ink.sh; no Hecate) at depths 0
# and +1 on the rendered windings of one fit. Units = (winding, model, depth), shared by several GPUs through claim folders.
# band_score3.sh scores them. Usage: band_three_model.sh <scroll> <fit-id> <CUDA GPU UUID> <run dir> w020 w021 ...
# Marker: A4INK-EXIT.
set -uo pipefail
SC=$1; FIT=$2; GPU=$3; RUN=$4; shift 4; WS="$*"
case "$GPU" in 1|GPU-33b8aac6*) echo "REFUSED: GPU 1 (GTX 1660 SUPER) is not usable for this work"; exit 97;; esac
S=~/scroll-prizes; P=/mnt/nvme/scroll-prizes/data/$SC; Z=$P/renders/$FIT; M=$P/ink/$FIT/maps; C=$P/ink/$FIT/claims-a4; L=$RUN/units
mkdir -p $M $C $L
export CUDA_VISIBLE_DEVICES=$GPU CKPT_DIR=$S/checkpoints/ckpt343 PY=$S/villa/vesuvius/.venv/bin/python N_LAYERS=66 NATIVE_UM=9.362 \
       VILLA_BATCH=4 TMPDIR=/mnt/nvme/scroll-prizes/scratch
MS="hybrid_3d2d-seed42 hybrid_3d2d-seed43 dnative"
have() { local f=$M/$1__$2__L66s$((25 + $3)); [ -s $f.tif ] && [ -s ${f}_reverse.tif ]; }
cd $S/villa/vesuvius
for d in 0 1; do for w in $WS; do for m in $MS; do
  have $w $m $d && continue
  [ -d $Z/$w.zarr/0 ] || continue
  mkdir $C/${w}_${m}_d${d} 2>/dev/null || continue; echo $GPU > $C/${w}_${m}_d${d}/gpu
  t0=$(date +%s); bash $S/bin/ink343/run_ink.sh $Z/$w.zarr $m $d $M > $L/${w}_${m}_d${d}.log 2>&1; rc=$?
  have $w $m $d && st=ok || { st=FAILED; rm -rf $C/${w}_${m}_d${d}; }
  echo "[$(date -Is)] $w $m d$d rc=$rc $st $(( $(date +%s) - t0 ))s"
done; done; done
echo "A4INK-EXIT: 0"
