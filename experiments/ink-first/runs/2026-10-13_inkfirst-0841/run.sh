#!/bin/bash
# Ink first on known 9.36 µm text with the per-sheet sampler (Ted 2026-10-13 ~5:15 pm CT: "yes", home GPU 0, free). The
# prototype found PHerc0841's text before the per-sheet sampler existed; the sampler is what made Nieuwlaar's letters on
# PHerc. 343 show (hot reading-side patches ~15x more often on letters than chance). Same test here on PHerc0841's two
# human-labelled segments, w00 and its neighbouring sheet ag2814 (official labels; held out for Reader v2 and d9v4C):
# letter tiles from runs/2026-10-13_agreement-0841 (label_boxes.py: 300 px tiles with >= 15 % labelled ink) -> 3D
# (letters_to_3d.py) -> one 1280^3 block per segment (the second is skipped when it lies inside the first) -> ink first
# (stride 96, size 256, m7 surface prediction, per-sheet sampler, Reader v2 + d9v4C) -> scroll map + cluster views ->
# letters test per segment (patches on letters vs elsewhere, against the mesh pipeline's maps of the same models).
# Markers in results/progress.log: BLOCKS-EXIT, then INKFIRST0841-EXIT.
S=~/scroll-prizes; R=$S/runs/2026-10-13_inkfirst-0841; PY=$S/villa/vesuvius/.venv/bin/python
U=https://vesuvius-challenge-open-data.s3.amazonaws.com/PHerc0841; H=/mnt/nvme/scroll-prizes/data/controls9um
V=$U/volumes/20250821151531-9.366um-1.2m-113keV-masked.zarr
P=$U/representations/predictions/surfaces/20250821151531-surface-20260413222639-surface-m7-L0-th0.2.zarr
A=$S/runs/2026-10-13_agreement-0841; mkdir -p $R/results; cd $R
log(){ echo "[$(date -u +%FT%TZ)] $*" | tee -a $R/results/progress.log; }
for seg in w00 ag2814; do
  [ -f l_$seg/blocks.tsv ] || nice -n 5 $PY -I $S/bin/letters_to_3d.py $H/heldout/0841-$seg/mesh.tifxyz $A/boxes_c0841_${seg}_66.json \
    l_$seg --size 1280 --id b0841$seg --shape 19400 7703 7703 > l_$seg.log 2>&1
  log "$seg: $(tail -1 l_$seg.log)"
done
# blocks: w00's; ag2814's only when its centre is not inside w00's block (then its letters are tested against w00's block)
$PY -I - > blocks.tsv <<'PY'
import csv
rows = [next(csv.DictReader(open(f'l_{s}/blocks.tsv'), delimiter='\t')) for s in ('w00', 'ag2814')]
keys = list(rows[0])
print('\t'.join(keys)); print('\t'.join(rows[0][k] for k in keys))
b = rows[0]; c = rows[1]
inside = all(int(b[f'{a}0']) <= (int(c[f'{a}0']) + int(c[f'{a}1'])) // 2 < int(b[f'{a}1']) for a in 'zyx')
if not inside:
    print('\t'.join(c[k] for k in keys))
PY
log "blocks: $(tail -n +2 blocks.tsv | cut -f1 | tr '\n' ' ')"
export ROOT=$S PY VILLA=$S/villa BIN=$S/bin CKPT_DIR=$S/checkpoints/ckpt343 WORK=/mnt/nvme2/scroll-prizes/scratch/inkfirst-0841 \
  KEEP_BLOCKS=1 RESULTS=$R/results TMPDIR=/mnt/nvme2/scroll-prizes/scratch SAMPLE_ARGS=--per-sheet \
  CUDA_VISIBLE_DEVICES=GPU-2d9651e9-5a94-e0cb-6a99-9300d8056524 VILLA_BATCH=8 TORCHDYNAMO_DISABLE=1
bash $S/bin/inkfirst_blocks.sh $R/blocks.tsv $V $P 9.366 readerv2,d9v4c 96 256 1
for m in readerv2 d9v4c; do
  nice -n 5 $PY $S/bin/inkfirst_scroll_map.py $R/results $R/map_$m --model $m --label "PHerc0841 known text" > $R/map_$m.log 2>&1
  for o in fwd rev; do
    nice -n 5 $PY $S/bin/inkfirst_cluster_view.py $R/results $R/map_$m/clusters_$o.tsv $R/view_$m --order $o --top 6 \
      --model $m --label "PHerc0841 known text" >> $R/view_$m.log 2>&1
  done
done
for seg in w00 ag2814; do
  id=$(grep -q b0841ag2814 blocks.tsv && [ $seg = ag2814 ] && echo b0841ag2814 || echo b0841w00)
  maps=$H/heldout/maps; [ $seg = ag2814 ] && maps=$H/c0841_ag2814/maps
  nice -n 5 $PY $S/bin/inkfirst_letters_test.py $R/results/$id/summary.npz l_$seg/letters3d.npz $A/boxes_c0841_${seg}_66.json \
    $R/letters_$seg --maps $maps --render c0841_${seg}_66 --layer s26 > $R/letters_$seg.log 2>&1
  log "$seg letters test: $(tail -2 $R/letters_$seg.log | head -1)"
done
log INKFIRST0841-EXIT
