#!/usr/bin/env bash
# On a fleet worker: process every line of /opt/scroll/jobs/batch.tsv (name, segment dir, volume URL, native um, models, depths),
# render + ink via run_segment.sh (resumable), then the four-model ensemble images (Nieuwlaar's ensemble_maps.py).
# Progress in /opt/scroll/results/progress.txt; BATCH-EXIT marker at the end.
set -uo pipefail
B=/opt/scroll/jobs/batch.tsv; OUT=/opt/scroll/results; mkdir -p $OUT
N=$(grep -cv '^\s*$' $B); k=0
PY=/opt/scroll/villa/vesuvius/.venv/bin/python
while IFS=$'\t' read -r NAME SEG URL UM MODELS DEPTHS; do
  [ -n "$NAME" ] || continue; k=$((k + 1))
  echo "$k/$N $NAME start $(date -u +%FT%TZ)" > $OUT/progress.txt
  [ -f $OUT/$NAME/DONE ] && continue
  bash /opt/scroll/bin/run_segment.sh "$NAME" "$SEG" "$URL" "$UM" "$MODELS" "$DEPTHS" > $OUT/$NAME.run.log 2>&1
  SD=$(echo "$DEPTHS" | tr ',' ' ')
  mkdir -p $OUT/$NAME/ensemble
  (cd /opt/scroll/villa/vesuvius && $PY /opt/scroll/bin/ink343/ensemble_maps.py --surface /opt/scroll/work/${NAME}_66.zarr --name ${NAME}_66 \
      --maps $OUT/$NAME/maps --out $OUT/$NAME/ensemble --stat-depths $SD --write-depths $SD > $OUT/$NAME/ensemble/ensemble.log 2>&1) \
    && touch $OUT/$NAME/DONE
  rm -rf /opt/scroll/work/${NAME}_66.zarr          # renders are ~1 GB each; keep the disk small
  echo "$k/$N $NAME done $(date -u +%FT%TZ)" > $OUT/progress.txt
done < $B
echo "BATCH-EXIT: 0 $(date -u +%FT%TZ)" >> $OUT/progress.txt
