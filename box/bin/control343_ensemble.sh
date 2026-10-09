#!/usr/bin/env bash
# Full four-model ensemble at d = +1 on the PHerc. 343 control (winner's method), then ensemble_maps images.
set -uo pipefail
export CUDA_VISIBLE_DEVICES=${1:-GPU-7937f33e-73c8-2a4f-d7c6-9c4c3c20c74f}
S=~/scroll-prizes; C=/mnt/nvme/scroll-prizes/data/PHerc0343/control; Z=$C/control343_66.zarr
export CKPT_DIR=$S/checkpoints/ckpt343 PY=$S/villa/vesuvius/.venv/bin/python HECATE_PY=$S/checkpoints/ckpt343/hecate.py PREP_PY=$S/bin/ink343/hecate_prep.py
export N_LAYERS=66 NATIVE_UM=8.64 VILLA_BATCH=4 HEC_BATCH=4 HEC_DEVICE=cuda TMPDIR=/mnt/nvme/scroll-prizes/tmp
cd $S/villa/vesuvius
for m in hybrid_3d2d-seed43 dnative hecate; do t0=$(date +%s); bash $S/bin/ink343/run_ink.sh "$Z" $m 1 $C/maps > $C/ink_${m}_d1.log 2>&1; echo "$m d+1 rc=$? $(( $(date +%s)-t0 ))s"; done
mkdir -p $C/images
$PY $S/bin/ink343/ensemble_maps.py --surface $Z --name control343_66 --maps $C/maps --out $C/images --stat-depths 1 --write-depths 1 > $C/images/ensemble.log 2>&1; echo "ensemble rc=$?"
ls $C/images
echo "ENSEMBLE343-EXIT: 0"
