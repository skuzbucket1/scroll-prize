#!/usr/bin/env bash
# On a fleet worker: process every line of /opt/scroll/jobs/batch.tsv (name, segment dir, volume URL, native um, models, depths),
# render + ink via run_segment.sh (resumable), then the four-model ensemble images (Nieuwlaar's ensemble_maps.py).
# Progress in /opt/scroll/results/progress.txt; BATCH-EXIT marker at the end.
set -uo pipefail
B=/opt/scroll/jobs/batch.tsv; OUT=/opt/scroll/results; mkdir -p $OUT
N=$(grep -cv '^\s*$' $B); k=0
PY=/opt/scroll/villa/vesuvius/.venv/bin/python
# Scan-Quality-Map in the background (CPU, streams the volume from S3), one segment at a time, while the GPU does ink.
SQMPID=""
if [ -f /opt/scroll/jobs/sqm.on ] && [ -x /opt/scroll/sqm-venv/bin/sqm ]; then
  ( export SQM_CACHE=/opt/scroll/cache/sqm SQM_CACHE_GB=20
    while IFS=$'\t' read -r NAME SEG URL UM MODELS DEPTHS <&3; do
      [ -n "$NAME" ] || continue; [ -f $OUT/$NAME/sqm/quality.png ] && continue; mkdir -p $OUT/$NAME
      MESH="$SEG"
      if [ "$(basename "${SEG%/}")" != flatten.tifxyz ]; then   # wait for run_segment.sh to flatten it (max 1 h)
        MESH=$OUT/$NAME/flatten/tifxyz/flatten.tifxyz; for i in $(seq 1 240); do [ -d "$MESH" ] && break; sleep 15; done
        [ -d "$MESH" ] || { echo "sqm $NAME skipped: no flattened mesh" >> $OUT/sqm-progress.txt; continue; }
      fi
      t0=$(date +%s); timeout ${SQM_TIMEOUT:-1500} nice -n 10 /opt/scroll/sqm-venv/bin/sqm segment --mesh "$MESH" --volume "$URL" \
        --voxel-um "$UM" --level 0 --block 96 --patch 16 --overlay --out $OUT/$NAME/sqm > $OUT/$NAME/sqm.log 2>&1
      echo "sqm $NAME rc=$? $(( $(date +%s)-t0 ))s" >> $OUT/sqm-progress.txt
    done 3< $B ) &
  SQMPID=$!
fi
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
  # stroke score (bin/stroke_score.py) on the worker, so only small results need fetching: the models this batch ran
  SM=$(echo "$MODELS" | tr ',' '\n' | sed -e 's/^hybrid_3d2d-seed42$/ink9-42/' -e 's/^hybrid_3d2d-seed43$/ink9-43/' | paste -sd, -)
  for d in $SD; do
    (cd /opt/scroll/villa/vesuvius && $PY /opt/scroll/bin/stroke_score.py --surface /opt/scroll/work/${NAME}_66.zarr --maps $OUT/$NAME/maps \
        --name ${NAME}_66 --out $OUT/$NAME/strokes --um "$UM" --depth $d --models "$SM" --crops 3 >> $OUT/$NAME/strokes.log 2>&1) || true
  done
  rm -rf /opt/scroll/work/${NAME}_66.zarr          # renders are ~1 GB each; keep the disk small
  echo "$k/$N $NAME done $(date -u +%FT%TZ)" > $OUT/progress.txt
done < $B
[ -n "$SQMPID" ] && { echo "waiting for sqm $(date -u +%FT%TZ)" >> $OUT/progress.txt; wait $SQMPID; }
echo "BATCH-EXIT: 0 $(date -u +%FT%TZ)" >> $OUT/progress.txt
