#!/usr/bin/env bash
# Ink maps for any model set and depths on the rendered windings of one fit (Nieuwlaar's run_ink.sh; models e.g. readerv2,d9v4c).
# Units = (winding, model, depth), shared by several GPUs through claim folders in <run dir>/claims-<scroll>-<fit>/.
# Usage: band_models.sh <scroll> <fit-id> <CUDA GPU UUID> <run dir> <models,comma> <depths,comma> w061 w062 ...
# Marker: MODELS-EXIT (one per call).
set -uo pipefail
SC=$1; FIT=$2; GPU=$3; RUN=$4; MS=${5//,/ }; DS=${6//,/ }; shift 6; WS="$*"
case "$GPU" in 1|GPU-33b8aac6*) echo "REFUSED: GPU 1 (GTX 1660 SUPER) is not usable for this work"; exit 97;; esac
S=~/scroll-prizes; P=/mnt/nvme/scroll-prizes/data/$SC; Z=$P/renders/$FIT; M=$P/ink/$FIT/maps; C=$RUN/claims-$SC-$FIT; L=$RUN/units
mkdir -p $M $C $L
export CUDA_VISIBLE_DEVICES=$GPU CKPT_DIR=$S/checkpoints/ckpt343 PY=$S/villa/vesuvius/.venv/bin/python N_LAYERS=66 NATIVE_UM=9.362 \
       VILLA_BATCH=4 TMPDIR=/mnt/nvme/scroll-prizes/scratch
have() { local f=$M/$1__$2__L66s$((25 + $3)); [ -s $f.tif ] && [ -s ${f}_reverse.tif ]; }
cd $S/villa/vesuvius
for d in $DS; do for w in $WS; do for m in $MS; do
  have $w $m $d && continue
  [ -d $Z/$w.zarr/0 ] || continue
  mkdir $C/${w}_${m}_d${d} 2>/dev/null || continue; echo $GPU > $C/${w}_${m}_d${d}/gpu
  t0=$(date +%s); bash $S/bin/ink343/run_ink.sh $Z/$w.zarr $m $d $M > $L/${SC}_${w}_${m}_d${d}.log 2>&1; rc=$?
  have $w $m $d && st=ok || { st=FAILED; rm -rf $C/${w}_${m}_d${d}; }
  echo "[$(date -Is)] $SC $w $m d$d rc=$rc $st $(( $(date +%s) - t0 ))s"
done; done; done
echo "MODELS-EXIT: 0 $SC"
