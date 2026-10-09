#!/usr/bin/env bash
# Launch the workers named in aws/state/fleet/plan.tsv (in parallel), bootstrap them, push the pipeline. SPENDS MONEY.
# Usage: aws/fleet_up.sh --yes [max_hours]      (max_hours = hard self-terminate limit per worker; default from fleet_plan)
source "$(dirname "$0")/lib.sh"
[ "${1:-}" = "--yes" ] || { echo "refusing to launch without --yes (this starts paid EC2 instances)"; exit 2; }
check_account; require_net
P=$STATE/fleet/plan.tsv; [ -s "$P" ] || { echo "no plan: run aws/fleet_plan.sh N" >&2; exit 2; }
export FLEET_MAX_HOURS=${2:-$MAX_HOURS}
WORKERS=$(cut -f1 "$P" | sort -u)
log "launching $(echo $WORKERS | wc -w) workers ($MARKET, types: ${INSTANCE_TYPES:-$INSTANCE_TYPE}; hard limit ${FLEET_MAX_HOURS} h each)"
for w in $WORKERS; do
  ( ISTATE=$STATE/fleet/$w WORKER_NAME=$w "$HERE/spot_up.sh" > "$STATE/fleet/$w.up.log" 2>&1 && \
    ISTATE=$STATE/fleet/$w "$HERE/spot_push.sh" >> "$STATE/fleet/$w.up.log" 2>&1 && echo "$w READY" || echo "$w FAILED (see aws/state/fleet/$w.up.log)" ) &
  sleep 3
done
wait
grep -l READY "$STATE"/fleet/*.up.log >/dev/null 2>&1 || true
for w in $WORKERS; do printf '%s  %s  %s\n' "$w" "$(cat "$STATE/fleet/$w/instance_id" 2>/dev/null || echo '-')" "$(tail -1 "$STATE/fleet/$w.up.log")"; done
