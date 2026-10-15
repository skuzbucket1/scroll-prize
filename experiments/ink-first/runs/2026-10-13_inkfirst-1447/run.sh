#!/bin/bash
# Second 8.64 µm positive control for ink first (Ted 2026-10-13 ~10:10 am CT: "yes - do that next", home box, free):
# one 1280^3 block of PHerc1447 centred on a place with known text in the public 8.64 um volume (the block in blocks.tsv;
# volume shape z 24297, y 8343, x 8343), run like the PHerc. 343 per-sheet control (stride 96, size 256, m7 surface
# prediction, per-sheet sampler) with Reader v2 and d9v4C. We only test whether our tools see it. Waits for ABLATION-EXIT (GPU 2; the other session's
# top30 run yielded GPU 2 and runs on GPU 0 only).
# Markers in results/progress.log: BLOCKS-EXIT, then INKFIRST1447-EXIT after the maps and cluster views.
S=~/scroll-prizes; R=$S/runs/2026-10-13_inkfirst-1447; PY=$S/villa/vesuvius/.venv/bin/python
U=https://vesuvius-challenge-open-data.s3.amazonaws.com/PHerc1447
until grep -q ABLATION-EXIT $S/runs/2026-10-13_ink-ablation/run.log 2>/dev/null; do sleep 60; done
while ls $S/runs/.gpu2-hold* > /dev/null 2>&1; do sleep 60; done   # other short GPU-2 jobs hold the card (each removes its file when done)
export ROOT=$S PY VILLA=$S/villa BIN=$S/bin CKPT_DIR=$S/checkpoints/ckpt343 WORK=/mnt/nvme2/scroll-prizes/scratch/inkfirst-1447 \
  KEEP_BLOCKS=1 RESULTS=$R/results TMPDIR=/mnt/nvme2/scroll-prizes/scratch SAMPLE_ARGS=--per-sheet \
  CUDA_VISIBLE_DEVICES=GPU-7937f33e-73c8-2a4f-d7c6-9c4c3c20c74f VILLA_BATCH=8 TORCHDYNAMO_DISABLE=1
bash $S/bin/inkfirst_blocks.sh $R/blocks.tsv $U/volumes/20250521151220-8.640um-1.2m-116keV-masked.zarr \
  $U/representations/predictions/surfaces/20250521151220-surface-20260413222639-surface-m7-L0-th0.2.zarr 8.64 readerv2,d9v4c 96 256 1
for m in readerv2 d9v4c; do
  nice -n 5 $PY $S/bin/inkfirst_scroll_map.py $R/results $R/map_$m --model $m --label "PHerc1447 text block" > $R/map_$m.log 2>&1
  for o in fwd rev; do
    nice -n 5 $PY $S/bin/inkfirst_cluster_view.py $R/results $R/map_$m/clusters_$o.tsv $R/view_$m --order $o --top 6 \
      --model $m --label "PHerc1447 text block" >> $R/view_$m.log 2>&1
  done
done
echo "[$(date -u +%FT%TZ)] INKFIRST1447-EXIT" >> $R/results/progress.log
