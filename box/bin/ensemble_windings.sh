#!/usr/bin/env bash
# Four-model ensemble (ink_9um 42/43, dense_native, Hecate; Nieuwlaar's scripts) at d = 0 and +1 on triaged windings,
# reusing seed-42 maps already in ink-triage/maps, then ensemble images per winding.
# Usage: ensemble_windings.sh <CUDA GPU UUID> w070 w069 ...
set -uo pipefail
case "$*" in *GPU-33b8aac6*) echo REFUSED; exit 97;; esac
GPU=$1; shift
S=~/scroll-prizes; D=/mnt/nvme/scroll-prizes/data/PHerc0191; M=$D/ink-triage/maps
for w in "$@"; do
  Z=$D/render66/exp30k_snapped_${w}_66.zarr; [ -d $Z/0 ] || { echo "no render for $w"; continue; }
  echo "[$(date -Is)] $w sweep d 0..1"
  bash $S/bin/depth_sweep.sh $Z $M $GPU 0 1 > $D/ink-triage/ensemble_${w}.log 2>&1
  mkdir -p $D/ink-triage/ensemble/$w
  cd $S/villa/vesuvius && .venv/bin/python $S/bin/ink343/ensemble_maps.py --surface $Z --name exp30k_snapped_${w}_66 --maps $M \
     --out $D/ink-triage/ensemble/$w --stat-depths 0 1 --write-depths 0 1 > $D/ink-triage/ensemble/$w/ensemble.log 2>&1
  echo "[$(date -Is)] $w ensemble rc=$? $(ls $D/ink-triage/ensemble/$w | grep -c png) images"
done
echo "ENSWIND-EXIT: 0"
