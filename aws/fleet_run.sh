#!/usr/bin/env bash
# Upload each worker's segments and batch list, start run_batch.sh detached on every worker.
source "$(dirname "$0")/lib.sh"
P=$STATE/fleet/plan.tsv; [ -s "$P" ] || { echo "no plan" >&2; exit 2; }
for w in $(cut -f1 "$P" | sort -u); do
  export ISTATE=$STATE/fleet/$w; [ -n "$(instance_ip)" ] || { log "$w has no instance; skipping"; continue; }
  B=$ISTATE/batch.tsv; : > "$B"
  while IFS=$'\t' read -r W NAME SEG URL UM MODELS DEPTHS; do
    [ "$W" = "$w" ] || continue
    rssh "mkdir -p /opt/scroll/jobs/$NAME"; rsync_to "${SEG%/}" "/opt/scroll/jobs/$NAME/"
    printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$NAME" "/opt/scroll/jobs/$NAME/$(basename "${SEG%/}")" "$URL" "$UM" "$MODELS" "$DEPTHS" >> "$B"
  done < "$P"
  rsync_to "$B" /opt/scroll/jobs/batch.tsv
  rssh "nohup bash /opt/scroll/bin/run_batch.sh > /opt/scroll/results/batch.log 2>&1 < /dev/null &"
  log "$w started $(wc -l < "$B" | tr -d ' ') segments"
done
