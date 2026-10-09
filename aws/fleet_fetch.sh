#!/usr/bin/env bash
# Copy results from every worker to data/aws-results/fleet/<worker>/. Default: ensemble images, previews, logs, timings.
# --maps also copies the raw ink maps (~20 MB each; ~320 MB per segment).
source "$(dirname "$0")/lib.sh"
P=$STATE/fleet/plan.tsv; [ -s "$P" ] || { echo "no plan" >&2; exit 2; }
EX=(--exclude 'maps/'); [ "${1:-}" = "--maps" ] && EX=()
for w in $(cut -f1 "$P" | sort -u); do
  export ISTATE=$STATE/fleet/$w; [ -n "$(instance_ip)" ] || continue
  OUT=$ROOT/data/aws-results/fleet/$w; mkdir -p "$OUT"
  rsync_from /opt/scroll/results/ "$OUT/" "${EX[@]}" && log "$w -> $OUT ($(du -sh "$OUT" | cut -f1))"
done
