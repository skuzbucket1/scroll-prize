#!/bin/bash
# Deep look at PHerc0813 w079 window 1, second start (2026-10-13 00:31 UTC): run.sh's sweep spent ~3 of every 5 minutes
# compiling the model (torch inductor, max-autotune) on the busy CPU and inked 4 patches per batch, i.e. ~13 h for the
# 186 runs. Same models, depths and crop; compile off (TORCHDYNAMO_DISABLE=1: eager mode, same fp16 autocast, outputs
# equal up to rounding) and 16 patches per batch. Maps that exist are kept (dnative d0 from run.sh).
# Markers in run2.log: SWEEP-EXIT, DEEPLOOK-EXIT.
S=~/scroll-prizes; R=$S/runs/2026-10-12_deeplook-0813-w079; PY=$S/villa/vesuvius/.venv/bin/python
export CUDA_VISIBLE_DEVICES=GPU-2d9651e9-5a94-e0cb-6a99-9300d8056524 TORCHDYNAMO_DISABLE=1
export CKPT_DIR=$S/checkpoints/ckpt343 PY HECATE_PY=$S/checkpoints/ckpt343/hecate.py PREP_PY=$S/bin/ink343/hecate_prep.py
export N_LAYERS=66 NATIVE_UM=9.362 VILLA_BATCH=16 HEC_BATCH=8 HEC_DEVICE=cuda TMPDIR=/mnt/nvme/scroll-prizes/tmp P_VILLA=1 P_HEC=1
export MODELS="dnative hybrid_3d2d-seed42 hybrid_3d2d-seed43 hecate readerv2 d9v4c"
mkdir -p $TMPDIR $R/maps
cd $S/villa/vesuvius
t0=$(date +%s)
bash $S/bin/ink343/run_depth_sweep.sh $R/w079crop.zarr $R/maps -15 15 > $R/sweep2.log 2>&1; rc=$?
echo "[$(date -Is)] SWEEP-EXIT: $rc in $(( $(date +%s) - t0 )) s"
nice -n 5 $PY $S/bin/deep_look_view.py $R/w079crop.zarr $R/maps $R/view --label "PHerc0813 w079 window 1" --um 9.362 \
  --window 256 256 854 1495 > $R/view.log 2>&1
echo "[$(date -Is)] DEEPLOOK-EXIT"
