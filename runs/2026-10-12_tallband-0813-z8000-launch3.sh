#!/bin/bash
# PHerc0813 band z 8000-10500, inking restarted (Ted 2026-10-12 ~10:40 pm CT: "gpu priority: yes - both"): Reader v2 +
# d9v4C at d 0/+1 on GPU 1 only (GPUs 0 and 2 go to the new 8.64 µm model and the agreement test), with the per-run torch
# compile off (TORCHDYNAMO_DISABLE=1; launch2.sh's units took 17-20 min, most of it compiling on the busy CPU) and 8
# patches per batch. Units already inked are kept (band_models.sh skips them); then the stroke-score 0.2 scoring pass as
# in launch2.sh. Markers: INK-DONE, BAND2-EXIT (launch3.log).
R=/mnt/nvme/scroll-prizes/runs/2026-10-12_tallband-0813-z8000; B=~/scroll-prizes/bin; S=~/scroll-prizes
P=/mnt/nvme/scroll-prizes/data/PHerc0813; FIT=exp30k-z8000; Z=$P/renders/$FIT
W=$(cat $R/windings.txt)
TORCHDYNAMO_DISABLE=1 VILLA_BATCH=8 bash $B/band_models.sh PHerc0813 $FIT GPU-54088dd3-29fc-b2d3-0096-c5b75aea4345 $R readerv2,d9v4c 0,1 $W > $R/gpu1_launch3.log 2>&1
echo "[$(date -Is)] INK-DONE: $(cat $R/gpu*.log | grep -c " ok ") units ok, $(cat $R/gpu*.log | grep -c FAILED) failed"
mkdir -p $R/post/PHerc0813; PY=$S/villa/vesuvius/.venv/bin/python; export TMPDIR=/mnt/nvme/scroll-prizes/scratch
for w in $W; do O=$R/post/PHerc0813/$w; [ -f $O/${w}__post.json ] && continue
  (cd $B && nice -n 5 $PY -I post_models.py $P/ink/$FIT/maps $w 9.362 readerv2,d9v4c 0,1 $O $Z/$w.zarr > $O.log 2>&1); done
cd $B && $PY -I rank_post.py $R/post/PHerc0813 > $R/post/PHerc0813/ranking_v02.tsv 2> $R/rank.log
echo "[$(date -Is)] BAND2-EXIT: $(tail -1 $R/rank.log)"
