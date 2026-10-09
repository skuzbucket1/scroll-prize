#!/usr/bin/env bash
# Upload a segment and run render + ink on the instance (detached), then wait for it.
# Usage: aws/spot_run.sh <name> <local segment.tifxyz dir> <volume zarr URL> <native_um> <models,comma> <depths,comma>
source "$(dirname "$0")/lib.sh"
[ $# -eq 6 ] || { sed -n '2,3p' "$0"; exit 2; }
NAME=$1; SEG=$2; URL=$3; UM=$4; MODELS=$5; DEPTHS=$6
[ -n "$(instance_ip)" ] || { echo "no instance in aws/state" >&2; exit 4; }
rssh "mkdir -p /opt/scroll/jobs/$NAME /opt/scroll/results/$NAME"
rsync_to "${SEG%/}" "/opt/scroll/jobs/$NAME/"
RSEG=/opt/scroll/jobs/$NAME/$(basename "${SEG%/}")
log "starting $NAME on $(instance_ip): models=$MODELS depths=$DEPTHS"
rssh "nohup bash /opt/scroll/bin/run_segment.sh '$NAME' '$RSEG' '$URL' '$UM' '$MODELS' '$DEPTHS' > /opt/scroll/results/$NAME/run.log 2>&1 < /dev/null &"
t0=$(date +%s)
while true; do
  out=$(rssh "tail -1 /opt/scroll/results/$NAME/run.log; tail -1 /opt/scroll/results/$NAME/timings.tsv 2>/dev/null" 2>/dev/null || true)
  echo "$out" | grep -q "RUN-EXIT" && break
  sleep 60; log "$NAME running $(( ($(date +%s)-t0) / 60 )) min: $(echo "$out" | tail -1)"
done
rssh "cat /opt/scroll/results/$NAME/timings.tsv; tail -1 /opt/scroll/results/$NAME/run.log"
