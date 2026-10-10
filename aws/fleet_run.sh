#!/usr/bin/env bash
# Upload each worker's segments and batch list, start run_batch.sh detached on every worker.
# Usage: aws/fleet_run.sh [--chain]   (--chain: do not start now; queue run_batch.sh behind the one already running)
# The plan is read on fd 3: ssh inside the loop would otherwise swallow the rest of the plan from stdin (2026-10-09 bug:
# workers got 1-3 of their 6 segments).
source "$(dirname "$0")/lib.sh"
CHAIN=0; [ "${1:-}" = "--chain" ] && CHAIN=1
P=$STATE/fleet/plan.tsv; [ -s "$P" ] || { echo "no plan" >&2; exit 2; }
for w in $(cut -f1 "$P" | sort -u); do
  export ISTATE=$STATE/fleet/$w; [ -n "$(instance_ip)" ] || { log "$w has no instance; skipping"; continue; }
  B=$ISTATE/batch.tsv; : > "$B"
  while IFS=$'\t' read -r W NAME SEG URL UM MODELS DEPTHS <&3; do
    [ "$W" = "$w" ] || continue
    rssh "mkdir -p /opt/scroll/jobs/$NAME" < /dev/null; rsync_to "${SEG%/}" "/opt/scroll/jobs/$NAME/" < /dev/null
    printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$NAME" "/opt/scroll/jobs/$NAME/$(basename "${SEG%/}")" "$URL" "$UM" "$MODELS" "$DEPTHS" >> "$B"
  done 3< "$P"
  rsync_to "$B" /opt/scroll/jobs/batch.tsv < /dev/null
  if [ $CHAIN -eq 1 ]; then
    rsync_to "$HERE/remote/chain_batch.sh" /opt/scroll/bin/ < /dev/null
    rssh "nohup bash /opt/scroll/bin/chain_batch.sh >> /opt/scroll/results/batch.log 2>&1 < /dev/null &" < /dev/null
    log "$w queued $(wc -l < "$B" | tr -d ' ') segments behind the running batch"
  else
    rssh "nohup bash /opt/scroll/bin/run_batch.sh > /opt/scroll/results/batch.log 2>&1 < /dev/null &" < /dev/null
    log "$w started $(wc -l < "$B" | tr -d ' ') segments"
  fi
done
