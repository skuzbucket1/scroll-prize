#!/usr/bin/env bash
# Copy results (maps, previews, logs, timings; not the large renders) back to data/aws-results/<instance id>/.
source "$(dirname "$0")/lib.sh"
[ -n "$(instance_ip)" ] || { echo "no instance in aws/state" >&2; exit 4; }
OUT=$ROOT/data/aws-results/$(instance_id); mkdir -p "$OUT"
rsync_from /opt/scroll/results/ "$OUT/"
rssh 'cat /opt/scroll/bootstrap.times /opt/scroll/torch.txt /opt/scroll/vc3d.txt 2>/dev/null' > "$OUT/instance-info.txt" || true
log "results in $OUT"; du -sh "$OUT"
