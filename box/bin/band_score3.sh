#!/usr/bin/env bash
# Research plan Phase A4 scorer (CPU): whenever the three models exist for a (winding, depth), write the ensemble images
# (Nieuwlaar's ensemble_maps.py) and the stroke score with review crops (tools/stroke-score, three-model set), then re-rank.
# When both depths of a winding are scored and neither is near the flag line, its render is deleted (approved by Ted 2026-10-10;
# the meshes, maps, ensembles and scores stay). Kept: any LOOK row, area_R >= 0.012, R - B >= 0.008 or window >= 0.025.
# Stops when <workers> A4INK-EXIT lines are in <run dir>/gpu*.log and nothing is left to score.
# Usage: band_score3.sh <scroll> <fit-id> <run dir> <workers> w020 w021 ...   Marker: A4SCORE-EXIT.
SC=$1; FIT=$2; RUN=$3; NW=$4; shift 4; WS="$*"
S=~/scroll-prizes; P=/mnt/nvme/scroll-prizes/data/$SC; Z=$P/renders/$FIT; M=$P/ink/$FIT/maps; E=$P/ink/$FIT/ens3; O=$P/scores/$FIT/ens3
PY=$S/villa/vesuvius/.venv/bin/python; export TMPDIR=/mnt/nvme/scroll-prizes/scratch PYTHONPATH=/mnt/nvme/scroll-prizes/tools/stroke-score/src
complete() { local s=$((25 + $2)) f; for f in $M/$1__hybrid_3d2d-seed42__L66s$s $M/$1__hybrid_3d2d-seed43__L66s$s $M/$1__dnative__L66s$s; do
  [ -s $f.tif ] && [ -s ${f}_reverse.tif ] || return 1; done; }
js() { echo $O/$1/$1__strokes_d$(printf %+03d $2).json; }
while true; do
  new=0
  for d in 0 1; do for w in $WS; do
    [ -f $(js $w $d) ] && continue; complete $w $d || continue; [ -d $Z/$w.zarr/0 ] || continue
    mkdir -p $E/$w $O/$w
    (cd $S/villa/vesuvius && nice -n 10 $PY $S/bin/ink343/ensemble_maps.py --surface $Z/$w.zarr --name $w --maps $M --out $E/$w \
       --stat-depths $d --write-depths $d > $E/$w/ensemble_d$d.log 2>&1)
    nice -n 10 $PY -m stroke_score.cli score --surface $Z/$w.zarr --name $w --maps $M --um 9.362 --depth $d --out $O/$w --crops 3 \
       --models ink9-42,ink9-43,dnative > $O/$w/score_d$d.log 2>&1
    echo "[$(date -Is)] scored $w d$d: $(tail -c 300 $O/$w/score_d$d.log | tr -d '\n' | cut -c1-200)"; new=1
  done; done
  if [ $new = 1 ]; then
    nice -n 10 $PY -m stroke_score.cli rank $O --out $O/ranking.tsv 2> $O/rank.log && echo "[$(date -Is)] ranked: $(cat $O/rank.log)"
    for w in $WS; do
      [ -d $Z/$w.zarr ] && [ -s $(js $w 0) ] && [ -s $(js $w 1) ] || continue
      keep=$(awk -F'\t' -v w=$w '$1 == w && ($12 == "LOOK" || $4 >= 0.012 || $6 >= 0.008 || $7 >= 0.025) {k = 1} END {print k + 0}' $O/ranking.tsv)
      [ "$(awk -F'\t' -v w=$w '$1 == w' $O/ranking.tsv | wc -l)" -ge 2 ] || continue
      if [ "$keep" = 1 ]; then grep -qx $w $RUN/kept_renders.txt 2>/dev/null || echo $w >> $RUN/kept_renders.txt
      else case "$Z/$w.zarr" in $P/renders/$FIT/w[0-9][0-9][0-9].zarr) rm -rf "$Z/$w.zarr" && echo "$w $(date -Is)" >> $RUN/deleted_renders.txt;; esac; fi
    done
  fi
  n=$(cat $RUN/gpu*.log 2>/dev/null | grep -c "A4INK-EXIT")
  [ "$n" -ge "$NW" ] && [ $new = 0 ] && { echo "A4SCORE-EXIT: 0"; exit 0; }
  sleep 300
done
