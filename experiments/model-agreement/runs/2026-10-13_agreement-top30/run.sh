#!/bin/bash
# Step 2 of the targeting plan (Ted 2026-10-13 "do all 3"; gate passed: agreement held on 343, 0841 w00 and 0139 w047):
# six-model agreement on crops around the top 15 ranked windings of PHerc0813 z12000 and PHerc0191 z11200, d 0 and +1.
# GPU 0 starts now; GPU 2 joins after the ablations (ABLATION-EXIT). Crops are claimed with mkdir so the two GPUs share one
# queue. Markers CROPS-DONE, TOP30-EXIT in run.log.
S=/home/tbienapfl/scroll-prizes; R=$S/runs/2026-10-13_agreement-top30; PY=$S/villa/vesuvius/.venv/bin/python
cd $R && mkdir -p claims
[ -f crops.tsv ] || nice -n 19 $PY -I make_crops.py $R --n 15
echo "[$(date -Is)] CROPS-DONE"
export TORCHDYNAMO_DISABLE=1 CKPT_DIR=$S/checkpoints/ckpt343 PY HECATE_PY=$S/checkpoints/ckpt343/hecate.py \
  PREP_PY=$S/bin/ink343/hecate_prep.py N_LAYERS=66 NATIVE_UM=9.362 VILLA_BATCH=16 HEC_BATCH=8 HEC_DEVICE=cuda \
  TMPDIR=/mnt/nvme/scroll-prizes/tmp P_VILLA=1 P_HEC=1 MODELS="dnative hybrid_3d2d-seed42 hybrid_3d2d-seed43 hecate readerv2 d9v4c"
worker(){   # GPU UUID
  local gpu=$1 z n
  for z in $R/PHerc*_top.zarr; do
    n=$(basename $z .zarr); mkdir claims/$n 2>/dev/null || continue
    mkdir -p $R/maps_$n
    (cd $S/villa/vesuvius && CUDA_VISIBLE_DEVICES=$gpu bash $S/bin/ink343/run_depth_sweep.sh $z $R/maps_$n 0 1 > $R/sweep_$n.log 2>&1)
    for d in 0 1; do
      nice -n 5 $PY -I $S/bin/model_agreement.py $z $R/maps_$n $n $d $R/agree_${n}_d$d.tsv --window $(cat $R/$n.window) --label $n >> $R/agreement.log 2>&1
      nice -n 5 $PY -I $S/bin/model_agreement.py $z $R/maps_$n $n $d $R/rel_agree_${n}_d$d.tsv --window $(cat $R/$n.window) --label $n --relative >> $R/agreement_rel.log 2>&1
    done
    echo "[$(date -Is)] $n done on $gpu"
  done
}
worker GPU-2d9651e9-5a94-e0cb-6a99-9300d8056524 &
( until grep -q ABLATION-EXIT $S/runs/2026-10-13_ink-ablation/run.log 2>/dev/null; do sleep 60; done
  worker GPU-7937f33e-73c8-2a4f-d7c6-9c4c3c20c74f ) &
wait
echo "[$(date -Is)] TOP30-EXIT"
