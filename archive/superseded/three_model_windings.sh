#!/usr/bin/env bash
# Three-model ink pass (ink_9um seeds 42/43 + dense_native, no Hecate) at d = 0, +1 on the windings the AWS fleet run did not
# cover, then ensemble images and the stroke score. Several GPUs can share the list (claims in ink-triage/claims3/).
# Usage: three_model_windings.sh <CUDA GPU UUID> w036 w103 ...
set -uo pipefail
case "$*" in *GPU-33b8aac6*) echo "REFUSED: GTX 1660 SUPER"; exit 97;; esac
GPU=$1; shift
S=~/scroll-prizes; D=/mnt/nvme/scroll-prizes/data/PHerc0191; M=$D/ink-triage/maps; C=$D/ink-triage/claims3; O=/mnt/nvme/scroll-prizes/data/strokes/box3m
export TMPDIR=/mnt/nvme/scroll-prizes/tmp MODELS="hybrid_3d2d-seed42 hybrid_3d2d-seed43 dnative"
mkdir -p $C $O
for w in "$@"; do
  Z=$D/render66/exp30k_snapped_${w}_66.zarr; [ -d $Z/0 ] || { echo "no render for $w"; continue; }
  mkdir $C/$w 2>/dev/null || continue; echo $GPU > $C/$w/gpu
  echo "[$(date -Is)] $w sweep d 0..1 on $GPU"
  bash $S/bin/depth_sweep.sh $Z $M $GPU 0 1 > $D/ink-triage/three_${w}.log 2>&1
  mkdir -p $D/ink-triage/ensemble3/$w
  cd $S/villa/vesuvius
  .venv/bin/python $S/bin/ink343/ensemble_maps.py --surface $Z --name exp30k_snapped_${w}_66 --maps $M \
     --out $D/ink-triage/ensemble3/$w --stat-depths 0 1 --write-depths 0 1 > $D/ink-triage/ensemble3/$w/ensemble.log 2>&1
  for d in 0 1; do
    nice -n 10 .venv/bin/python $S/bin/stroke_score.py --surface $Z --maps $M --name exp30k_snapped_${w}_66 --out $O/$w \
      --um 9.362 --depth $d --models ink9-42,ink9-43,dnative --crops 3 > /dev/null 2>> $O/errors.log
  done
  echo "[$(date -Is)] $w done rc=$? $(ls $O/$w/*.json 2>/dev/null | wc -l) score files"
done
echo "THREEM-EXIT: 0"
