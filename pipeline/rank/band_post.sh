#!/usr/bin/env bash
# Scorer for band_models.sh (CPU): whenever every model and depth exists for a winding, run post_models.py (mean-z ensemble,
# stroke score with the CT void mask, row-structure score, JPEG previews) into <run dir>/post/<scroll>/<w>/, then rank.
# Stops when <workers> MODELS-EXIT lines for this scroll are in <run dir>/gpu*.log and nothing is left.
# Usage: band_post.sh <scroll> <fit-id> <run dir> <models,comma> <depths,comma> <workers> w061 w062 ...   Marker: POST-EXIT.
SC=$1; FIT=$2; RUN=$3; MODELS=$4; DEPTHS=$5; NW=$6; shift 6; WS="$*"
S=~/scroll-prizes; P=/mnt/nvme/scroll-prizes/data/$SC; Z=$P/renders/$FIT; M=$P/ink/$FIT/maps; O=$RUN/post/$SC
PY=$S/villa/vesuvius/.venv/bin/python; export TMPDIR=/mnt/nvme/scroll-prizes/scratch; mkdir -p $O
complete() { local m d f; for m in ${MODELS//,/ }; do for d in ${DEPTHS//,/ }; do f=$M/$1__${m}__L66s$((25 + d))
  [ -s $f.tif ] && [ -s ${f}_reverse.tif ] || return 1; done; done; }
rank() { $PY -I - "$O" > $O/ranking.tsv <<'PY'
import json, glob, sys
rows = []
for f in glob.glob(sys.argv[1] + '/*/*__post.json'):
    j = json.load(open(f))
    for d, r in j['depths'].items():
        rows.append((r['row_R'], j['name'], int(d), r['row_B'], r['area_R'], r['area_B'], r['window_R'], r['window_B']))
print('name\tdepth\trow_R\trow_B\tarea_R\tarea_B\twindow_R\twindow_B')
for r in sorted(rows, reverse=True): print(f'{r[1]}\t{r[2]:+d}\t{r[0]:.3f}\t{r[3]:.3f}\t{r[4]:.4f}\t{r[5]:.4f}\t{r[6]:.4f}\t{r[7]:.4f}')
PY
}
while true; do
  new=0
  for w in $WS; do
    [ -f $O/$w/${w}__post.json ] && continue; complete $w || continue
    (cd $S/bin && nice -n 10 $PY -I post_models.py $M $w 9.362 "$MODELS" "$DEPTHS" $O/$w $Z/$w.zarr > $O/$w.log 2>&1)
    echo "[$(date -Is)] $SC $w: $(grep -h area_R $O/$w.log | tr '\n' ' ' | cut -c1-240)"; new=1
  done
  [ $new = 1 ] && rank
  n=$(cat $RUN/gpu*.log 2>/dev/null | grep -c "MODELS-EXIT: 0 $SC")
  [ "$n" -ge "$NW" ] && [ $new = 0 ] && { rank; echo "POST-EXIT: 0 $SC"; exit 0; }
  sleep 120
done
