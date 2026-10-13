#!/bin/bash
# Ink-first positive control on PHerc. 343 (Ted approved 2026-10-12 7:10 pm CT, home box, free): one 1280^3 block around
# Erwin Nieuwlaar's First Letters (block from letters_to_3d.py: 10 of his 18 letters), run exactly like the PHerc0175A
# sweep (aws/remote/inkfirst_blocks.sh: stride 96, size 256, m7 surface prediction, 8.64 um) with Reader v2 (the
# sweep's model) and d9v4C (with Reader v2, the set that flags the 343 letters on the full render). None of the models
# trained on this volume. Markers in results/progress.log: BLOCKS-EXIT, then CONTROL343-EXIT after the maps, the cluster
# views and the letter test.
S=~/scroll-prizes; R=$S/runs/2026-10-12_inkfirst-343; PY=$S/villa/vesuvius/.venv/bin/python
U=https://vesuvius-challenge-open-data.s3.amazonaws.com/PHerc0343
export ROOT=$S PY VILLA=$S/villa BIN=$S/bin CKPT_DIR=$S/checkpoints/ckpt343 WORK=/mnt/nvme2/scroll-prizes/scratch/inkfirst-343 \
  KEEP_BLOCKS=1 RESULTS=$R/results TMPDIR=/mnt/nvme2/scroll-prizes/scratch \
  CUDA_VISIBLE_DEVICES=GPU-7937f33e-73c8-2a4f-d7c6-9c4c3c20c74f VILLA_BATCH=4
bash $S/bin/inkfirst_blocks.sh $R/blocks.tsv $U/volumes/20250521140437-8.640um-1.2m-116keV-masked.zarr \
  $U/representations/predictions/surfaces/20250521140437-surface-20260413222639-surface-m7-L0-th0.2.zarr 8.64 readerv2,d9v4c 96 256 1
for m in readerv2 d9v4c; do
  nice -n 5 $PY $S/bin/inkfirst_scroll_map.py $R/results $R/map_$m --model $m --label PHerc0343 > $R/map_$m.log 2>&1
  for o in fwd rev; do
    nice -n 5 $PY $S/bin/inkfirst_cluster_view.py $R/results $R/map_$m/clusters_$o.tsv $R/view_$m --order $o --top 6 --model $m \
      --label PHerc0343 >> $R/view_$m.log 2>&1
  done
done
[ -f $S/bin/inkfirst_letters_test.py ] && nice -n 5 $PY $S/bin/inkfirst_letters_test.py $R/results/b343/summary.npz $R/letters3d.npz \
  $R/letter_boxes.json $R/letters > $R/letters.log 2>&1
echo "[$(date -u +%FT%TZ)] CONTROL343-EXIT" >> $R/results/progress.log
