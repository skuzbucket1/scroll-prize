#!/usr/bin/env bash
# Copy results from every worker to data/aws-results/fleet/<worker>/. Default: ensemble images, previews, logs, timings.
# --maps also copies the raw ink maps (~110 MB per segment). Default is LITE: stroke scores (strokes/), the ensemble,
# ensemble_blind and CT images, logs and timings; per-model images and previews stay on the worker (FETCH_FULL=1 for all).
# Workers are fetched in parallel.
source "$(dirname "$0")/lib.sh"
P=$STATE/fleet/plan.tsv; [ -s "$P" ] || { echo "no plan" >&2; exit 2; }
EX=(--exclude 'maps/'); [ "${1:-}" = "--maps" ] && EX=()
[ "${FETCH_FULL:-0}" = 1 ] || EX+=(--exclude 'previews/' --exclude 'ensemble/*__dnative*' --exclude 'ensemble/*__hecate*' --exclude 'ensemble/*__ink9-4*')
for w in $(cut -f1 "$P" | sort -u); do
  export ISTATE=$STATE/fleet/$w; [ -n "$(instance_ip)" ] || continue
  OUT=$ROOT/data/aws-results/fleet/$w; mkdir -p "$OUT"
  ( rsync_from /opt/scroll/results/ "$OUT/" "${EX[@]}" && log "$w -> $OUT ($(du -sh "$OUT" | cut -f1))" ) &
done
wait
