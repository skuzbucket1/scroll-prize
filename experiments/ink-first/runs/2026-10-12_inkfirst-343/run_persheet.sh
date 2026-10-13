#!/bin/bash
# 343 ink-first control, second run (Ted approved 2026-10-12 ~9:05 pm CT: "run the sampler test on 343 overnight", home box,
# free): the same block b343 and models as run.sh, with the per-sheet sampler (ink-first sample --per-sheet: one point
# per separate sheet piece in each 96^3 cell instead of one per cell). The question: do Nieuwlaar's letters now get
# enough patches to show up as a clear one-sided cluster? Results in results_persheet/, compared with results/ by the
# same map, cluster-view and letter-test scripts. Markers in results_persheet/progress.log: BLOCKS-EXIT, PERSHEET-EXIT.
S=~/scroll-prizes; R=$S/runs/2026-10-12_inkfirst-343; PY=$S/villa/vesuvius/.venv/bin/python
U=https://vesuvius-challenge-open-data.s3.amazonaws.com/PHerc0343
export ROOT=$S PY VILLA=$S/villa BIN=$S/bin CKPT_DIR=$S/checkpoints/ckpt343 WORK=/mnt/nvme2/scroll-prizes/scratch/inkfirst-343-persheet \
  KEEP_BLOCKS=1 RESULTS=$R/results_persheet TMPDIR=/mnt/nvme2/scroll-prizes/scratch SAMPLE_ARGS=--per-sheet \
  CUDA_VISIBLE_DEVICES=GPU-7937f33e-73c8-2a4f-d7c6-9c4c3c20c74f VILLA_BATCH=8 TORCHDYNAMO_DISABLE=1
bash $S/bin/inkfirst_blocks.sh $R/blocks.tsv $U/volumes/20250521140437-8.640um-1.2m-116keV-masked.zarr \
  $U/representations/predictions/surfaces/20250521140437-surface-20260413222639-surface-m7-L0-th0.2.zarr 8.64 readerv2,d9v4c 96 256 1
for m in readerv2 d9v4c; do
  nice -n 5 $PY $S/bin/inkfirst_scroll_map.py $R/results_persheet $R/map_persheet_$m --model $m --label "PHerc0343 per-sheet" > $R/map_persheet_$m.log 2>&1
  for o in fwd rev; do
    nice -n 5 $PY $S/bin/inkfirst_cluster_view.py $R/results_persheet $R/map_persheet_$m/clusters_$o.tsv $R/view_persheet_$m --order $o --top 6 \
      --model $m --label "PHerc0343 per-sheet" >> $R/view_persheet_$m.log 2>&1
  done
done
nice -n 5 $PY $S/bin/inkfirst_letters_test.py $R/results_persheet/b343/summary.npz $R/letters3d.npz $R/letter_boxes.json $R/letters_persheet \
  > $R/letters_persheet.log 2>&1
echo "[$(date -u +%FT%TZ)] PERSHEET-EXIT" >> $R/results_persheet/progress.log
