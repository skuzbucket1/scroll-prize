#!/usr/bin/env bash
# Research plan Phase A3 scorer (CPU): whenever all four models exist for a (winding, depth), write the ensemble images
# (Nieuwlaar's ensemble_maps.py) and the stroke score with review crops (tools/stroke-score), then re-rank.
# Stops when every deep_look.sh worker has written DEEPLOOK-EXIT and nothing is left to score.
# Usage: deep_score.sh <fit-id> w073 ...
FIT=$1; shift; WS="$*"
S=~/scroll-prizes; P=/mnt/nvme/scroll-prizes/data/PHerc0191; Z=$P/renders/$FIT; M=$P/ink/$FIT/maps; E=$P/ink/$FIT/ens4; O=$P/scores/$FIT/ens4
R=/mnt/nvme/scroll-prizes/runs/2026-10-10_deeplook-$FIT; PY=$S/villa/vesuvius/.venv/bin/python; export TMPDIR=/mnt/nvme/scroll-prizes/scratch
export PYTHONPATH=/mnt/nvme/scroll-prizes/tools/stroke-score/src
complete() { local w=$1 d=$2 s=$((25 + $2)) zc; zc=$(awk -v d=$d 'BEGIN{printf "%.2f", 32.5 + d}')
  for f in $M/${w}__hybrid_3d2d-seed42__L66s$s $M/${w}__hybrid_3d2d-seed43__L66s$s $M/${w}__dnative__L66s$s; do [ -s $f.tif ] && [ -s ${f}_reverse.tif ] || return 1; done
  [ -s $M/${w}__hecate__L66zc$zc.png ] && [ -s $M/${w}__hecate__L66zc${zc}_reverse.png ]; }
while true; do
  new=0
  for d in 0 1 -1 2 -2 3; do for w in $WS; do
    js=$O/$w/${w}__strokes_d$(printf %+03d $d).json
    [ -f $js ] && continue; complete $w $d || continue
    mkdir -p $E/$w $O/$w
    (cd $S/villa/vesuvius && nice -n 10 $PY $S/bin/ink343/ensemble_maps.py --surface $Z/$w.zarr --name $w --maps $M --out $E/$w \
       --stat-depths $d --write-depths $d > $E/$w/ensemble_d$d.log 2>&1)
    nice -n 10 $PY -m stroke_score.cli score --surface $Z/$w.zarr --name $w --maps $M --um 9.362 --depth $d --out $O/$w --crops 3 > $O/$w/score_d$d.log 2>&1
    echo "[$(date -Is)] scored $w d$d: $(tail -c 300 $O/$w/score_d$d.log | tr -d '\n' | cut -c1-220)"; new=1
  done; done
  [ $new = 1 ] && nice -n 10 $PY -m stroke_score.cli rank $O --out $O/ranking.tsv 2> $O/rank.log && echo "[$(date -Is)] ranked: $(cat $O/rank.log)"
  n=$(grep -l "DEEPLOOK-EXIT" $R/gpu*.log 2>/dev/null | wc -l); w=$(ls $R/gpu*.log 2>/dev/null | wc -l)
  [ "$n" -ge "$w" ] && [ "$w" -gt 0 ] && [ $new = 0 ] && { echo "DEEPSCORE-EXIT: 0"; exit 0; }
  sleep 300
done
