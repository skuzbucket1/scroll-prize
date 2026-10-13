#!/bin/bash
# PHerc0813 band z 8000-10500 after the gates (fit 0.484 / 0.132; snap 0.82 with sheet, w040-w113 at 0.84-0.95; tall-band
# tiling approved by Ted 2026-10-11): flatten + render w040-w115 (triage_band.sh: GPU 2 now; GPUs 0 and 1 join when the
# z10500 band's inking is done), then Reader v2 + d9v4C at d 0/+1 on 3 GPUs, then the stroke-score 0.2 scoring pass.
# Markers: TRIAGE-DONE, INK-DONE, BAND2-EXIT (launch2.log).
R=/mnt/nvme/scroll-prizes/runs/2026-10-12_tallband-0813-z8000; B=~/scroll-prizes/bin; S=~/scroll-prizes
P=/mnt/nvme/scroll-prizes/data/PHerc0813; FIT=exp30k-z8000; Z=$P/renders/$FIT
G=(GPU-2d9651e9-5a94-e0cb-6a99-9300d8056524 GPU-54088dd3-29fc-b2d3-0096-c5b75aea4345 GPU-7937f33e-73c8-2a4f-d7c6-9c4c3c20c74f)
SCROLL=PHerc0813 bash $B/triage_band.sh $FIT ${G[2]} 40 115 > $R/triage_gpu2.log 2>&1 &
until grep -q INK-DONE $S/runs/2026-10-11_tallband-0813-z10500/launch3.log 2>/dev/null; do sleep 120; done
for i in 0 1; do SCROLL=PHerc0813 bash $B/triage_band.sh $FIT ${G[$i]} 40 115 > $R/triage_gpu$i.log 2>&1 & sleep 20; done; wait
echo "[$(date -Is)] TRIAGE-DONE: $(ls -d $Z/w*.zarr 2>/dev/null | wc -l) renders"
W=$(ls -d $Z/w*.zarr 2>/dev/null | xargs -n1 basename | sed "s/.zarr//" | sort | tr "\n" " "); echo "$W" > $R/windings.txt
for i in 0 1 2; do bash $B/band_models.sh PHerc0813 $FIT ${G[$i]} $R readerv2,d9v4c 0,1 $W > $R/gpu$i.log 2>&1 & sleep 30; done; wait
echo "[$(date -Is)] INK-DONE: $(cat $R/gpu*.log | grep -c " ok ") units ok, $(cat $R/gpu*.log | grep -c FAILED) failed"
mkdir -p $R/post/PHerc0813; PY=$S/villa/vesuvius/.venv/bin/python; export TMPDIR=/mnt/nvme/scroll-prizes/scratch
for w in $W; do O=$R/post/PHerc0813/$w; [ -f $O/${w}__post.json ] && continue
  (cd $B && nice -n 5 $PY -I post_models.py $P/ink/$FIT/maps $w 9.362 readerv2,d9v4c 0,1 $O $Z/$w.zarr > $O.log 2>&1); done
cd $B && $PY -I rank_post.py $R/post/PHerc0813 > $R/post/PHerc0813/ranking_v02.tsv 2> $R/rank.log
echo "[$(date -Is)] BAND2-EXIT: $(tail -1 $R/rank.log)"
