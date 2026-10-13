#!/usr/bin/env bash
# Progress of every fleet worker and a running cost estimate.
source "$(dirname "$0")/lib.sh"
P=$STATE/fleet/plan.tsv; [ -s "$P" ] || { echo "no plan" >&2; exit 2; }
if [ "${MARKET:-spot}" = ondemand ]; then RATE=${ONDEMAND_PRICE:-0.752}; else RATE=$MAX_PRICE; fi
tot=0; done_=0; cost=0
for w in $(cut -f1 "$P" | sort -u); do
  export ISTATE=$STATE/fleet/$w
  n=$(awk -v w="$w" -F'\t' '$1==w' "$P" | wc -l | tr -d ' '); tot=$((tot + n))
  if [ -n "$(instance_ip)" ]; then
    pr=$(rssh 'tail -1 /opt/scroll/results/progress.txt 2>/dev/null; ls /opt/scroll/results/*/DONE 2>/dev/null | wc -l' 2>/dev/null | tr '\n' ' ' || echo "unreachable")
    d=$(echo "$pr" | awk '{print $NF}'); done_=$((done_ + ${d:-0}))
    h=$(python3 -c "import time; print(round((time.time()-$(cat "$ISTATE/launched_at"))/3600, 2))")
    cost=$(python3 -c "print(round($cost + $h*$RATE, 2))")
    echo "$w  $(instance_id)  up ${h} h  $pr"
  else echo "$w  (no instance)"; fi
done
echo "segments done: $done_/$tot   running cost so far ~\$$cost at \$$RATE/h"
