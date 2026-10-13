#!/bin/bash
# run_depth_sweep.sh - all four ink models, both directions, at every depth d in [D_MIN, D_MAX], for one surface volume.
#
#   run_depth_sweep.sh <surface.zarr> <out_dir> [D_MIN] [D_MAX]        (defaults -15 +15)
#
# Order: d = 0 first, then outwards (|d| = 1, 2, ...), so a partial run already holds the central depths.
# Maps that already exist are skipped (the run can be resumed). MODELS overrides the model list.
# P_VILLA / P_HEC (default 1 / 1) run that many villa / Hecate jobs at the same time; on a 24 GB GPU I used 2 + 2
# concurrently (peak GPU memory ~7.5 GB on an RTX 4090, ~10 GB on an RTX 5090).
set -euo pipefail
export LC_ALL=C          # decimal point in awk output, whatever the host locale
[[ $# -ge 2 ]] || { awk 'NR > 1 && /^#/ {print; next} NR > 1 {exit}' "$0"; exit 2; }
Z=$1; OUT=$2; DMIN=${3:--15}; DMAX=${4:-15}
HERE=$(cd "$(dirname "$0")" && pwd)
MODELS=${MODELS:-"dnative hybrid_3d2d-seed42 hybrid_3d2d-seed43 hecate"}
P_VILLA=${P_VILLA:-1}; P_HEC=${P_HEC:-1}
N=${N_LAYERS:-66}; NAME=$(basename "$Z" .zarr)
mkdir -p "$OUT/logs"

depths(){  # d = 0, -1, +1, -2, +2, ... within [DMIN, DMAX]
  local a
  for a in $(seq 0 30); do
    (( 0 >= DMIN && 0 <= DMAX && a == 0 )) && echo 0
    (( a > 0 && -a >= DMIN )) && echo $(( -a ))
    (( a > 0 && a <= DMAX )) && echo "$a"
  done
  return 0
}
done_already(){  # <model> <d>
  if [[ $1 == hecate ]]; then
    local zc; zc=$(awk -v n="$N" -v d="$2" 'BEGIN{printf "%.2f", (n - 1) / 2 + d}')
    [[ -s $OUT/${NAME}__hecate__L${N}zc${zc}.png && -s $OUT/${NAME}__hecate__L${N}zc${zc}_reverse.png ]]
  else
    local s=$(( N / 2 + $2 - 8 ))
    [[ -s $OUT/${NAME}__$1__L${N}s${s}.tif && -s $OUT/${NAME}__$1__L${N}s${s}_reverse.tif ]]
  fi
}
queue(){  # <kind: villa|hecate> <parallel>
  local kind=$1 par=$2 d m
  for d in $(depths); do
    for m in $MODELS; do
      [[ $kind == hecate && $m != hecate ]] && continue
      [[ $kind == villa && $m == hecate ]] && continue
      done_already "$m" "$d" && continue
      while (( $(jobs -rp | wc -l) >= par )); do sleep 2; done
      ( t0=$(date +%s)
        if "$HERE/run_ink.sh" "$Z" "$m" "$d" "$OUT" > "$OUT/logs/${m}_d${d}.log" 2>&1; then rc=0; else rc=$?; fi
        printf '%s\t%s\t%s\t%s\n' "$m" "$d" "$(( $(date +%s) - t0 ))" "$rc" >> "$OUT/logs/timings.tsv" ) &
    done
  done
  wait
}
queue villa "$P_VILLA" &
queue hecate "$P_HEC" &
wait
echo "done: $(ls "$OUT" | grep -c -E '\.(tif|png)$') maps in $OUT; timings in $OUT/logs/timings.tsv"
awk -F'\t' '$4 != 0 {n++} END {if (n) {print n " failed job(s), see logs"; exit 1}}' "$OUT/logs/timings.tsv"
