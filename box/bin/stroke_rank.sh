#!/usr/bin/env bash
# Score every winding that has ink maps with bin/stroke_score.py and write one ranking table.
#   stroke_rank.sh [maps dir (default ink-triage/maps)]
# Per winding and depth: the single-model score (ink_9um seed 42, --tag _s42) wherever its maps exist, and the
# four-model ensemble score wherever all four models exist. Reference rows: the PHerc. 343 control (positive).
# Output: data/strokes/ranking.tsv (sorted by reading/blind stroke-area ratio) + per-winding json/png/crops.
set -uo pipefail
S=~/scroll-prizes; D=/mnt/nvme/scroll-prizes/data/PHerc0191; O=/mnt/nvme/scroll-prizes/data/strokes
M=${1:-$D/ink-triage/maps}; PY=$S/villa/vesuvius/.venv/bin/python
mkdir -p $O; T=$O/ranking.tmp; : > $T
score() {  # <set> <surface> <maps> <name> <out> <um> <depth> [extra args]
  local set=$1 z=$2 m=$3 n=$4 o=$5 um=$6 d=$7; shift 7
  local tag=""; [ "$set" = s42 ] && tag=_s42
  local js="$o/${n}__strokes${tag}_d$(printf %+03d $d).json"
  # incremental: re-score only when a map of this name/depth is newer than its json (FORCE=1 re-scores all)
  if [ "${FORCE:-0}" = 1 ] || [ ! -f "$js" ] || [ -n "$(find $m -maxdepth 1 -name "${n}__*" -newer "$js" | head -n 1)" ]; then
  nice -n 19 $PY $S/bin/stroke_score.py --surface $z --maps $m --name $n --out $o --um $um --depth $d --crops 3 "$@" \
    > /dev/null 2>> $O/rank-errors.log || return 0
  fi
  python3 - "$js" "$set" >> $T <<'PY'
import json, sys
j = json.load(open(sys.argv[1])); r, b = j['sides']['reading'], j['sides']['blind']
fr = r['stroke_frac'] / max(b['stroke_frac'], 1e-9); mr = r['tiles'].get('max', 0) / max(b['tiles'].get('max', 0), 1e-9)
t = (j['top_reading_tiles'] or [{}])[0]
print('\t'.join(str(x) for x in (j['name'], sys.argv[2], j['depth'], '%.2f' % fr, '%.4f' % r['stroke_frac'],
      '%.4f' % b['stroke_frac'], '%.3f' % r['tiles'].get('max', 0), '%.3f' % b['tiles'].get('max', 0), '%.2f' % mr,
      t.get('read_y', ''), t.get('read_x', ''), t.get('damage', ''), j['used_px'])))
PY
}
C=/mnt/nvme/scroll-prizes/data/PHerc0343/control
score s42 $C/control343_66.zarr $C/maps control343_66 $O/c343 8.64 1 --models ink9-42 --tag _s42
score ens4 $C/control343_66.zarr $C/maps control343_66 $O/c343 8.64 1
for n in $(ls $M | sed -nE 's/^(exp30k_snapped_w[0-9]+_66)__.*/\1/p' | sort -u); do
  w=$(echo $n | sed -E 's/.*_(w[0-9]+)_66/\1/'); z=$D/render66/$n.zarr; [ -d $z/0 ] || continue
  for d in -1 0 1 2; do
    s=$((d + 25)); h=$(printf %.2f $(echo "32.5 + $d" | bc))
    [ -f $M/${n}__hybrid_3d2d-seed42__L66s${s}_reverse.tif ] && [ -f $M/${n}__hybrid_3d2d-seed42__L66s${s}.tif ] && \
      score s42 $z $M $n $O/$w 9.362 $d --models ink9-42 --tag _s42
    [ -f $M/${n}__hecate__L66zc${h}_reverse.png ] && [ -f $M/${n}__hecate__L66zc${h}.png ] && \
    [ -f $M/${n}__dnative__L66s${s}_reverse.tif ] && [ -f $M/${n}__hybrid_3d2d-seed43__L66s${s}_reverse.tif ] && \
      score ens4 $z $M $n $O/$w 9.362 $d
  done
done
{ printf 'name\tset\tdepth\tarea_ratio_R/B\tarea_R\tarea_B\tmax_tile_R\tmax_tile_B\tmax_ratio\ttop_read_y\ttop_read_x\ttop_damage\tused_px\n'
  sort -t$'\t' -k4,4gr $T; } > $O/ranking.tsv
rm -f $T
echo "[$(date -Is)] ranked $(($(wc -l < $O/ranking.tsv) - 1)) rows -> $O/ranking.tsv"
echo "RANK-EXIT: 0"
