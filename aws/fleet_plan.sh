#!/usr/bin/env bash
# Split the staged manifest across N workers and estimate wall time and cost. Read-only (no AWS calls).
# Usage: aws/fleet_plan.sh N [minutes_per_segment=35]
source "$(dirname "$0")/lib.sh"
N=${1:?usage: fleet_plan.sh N [min_per_segment]}; MPS=${2:-35}
M=$ROOT/data/aws-stage/manifest.tsv; [ -s "$M" ] || { echo "no manifest: run aws/stage_segments.sh first" >&2; exit 2; }
mkdir -p "$STATE/fleet"; P=$STATE/fleet/plan.tsv; : > "$P"
awk -v n="$N" 'BEGIN{FS=OFS="\t"} NF { printf "w%02d\t%s\n", (NR-1) % n + 1, $0 }' "$M" > "$P"
TOTAL=$(wc -l < "$M" | tr -d ' ')
if [ "${MARKET:-spot}" = ondemand ]; then RATE=${ONDEMAND_PRICE:-0.752}; else RATE=$MAX_PRICE; fi
python3 - "$TOTAL" "$N" "$MPS" "$RATE" <<'PY'
import sys, math
total, n, mps, rate = int(sys.argv[1]), int(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4])
per = math.ceil(total / n); wall_h = per * mps / 60 + 0.1          # + bootstrap/fetch overhead
inst_h = total * mps / 60 + n * 0.1
print(f"{total} segments on {n} workers: up to {per} each; ~{wall_h:.1f} h wall; ~{inst_h:.1f} instance-hours")
print(f"estimated cost ~${inst_h * rate:.2f} at ${rate}/h (worst case if every worker runs to the hard limit: see FLEET_MAX_HOURS)")
print(f"suggested FLEET_MAX_HOURS={math.ceil(wall_h + 1)}")
PY
cut -f1 "$P" | sort | uniq -c | awk '{print "  " $2 ": " $1 " segments"}'
