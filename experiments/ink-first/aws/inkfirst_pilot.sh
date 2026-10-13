#!/usr/bin/env bash
# Ink-first pilot on AWS (Ted approved 2026-10-12, ~$2.50): one on-demand g5.4xlarge (A10G 24 GB, 16 vCPU), or g6.4xlarge
# (L4 24 GB, 16 vCPU; Ted OK'd it as the fallback) when g5 has no capacity, blocks of
# PHerc0175A read straight from the public bucket, Reader v2, then fetch the small results and TERMINATE the instance
# (trap on every exit). Usage: experiments/ink-first/aws/inkfirst_pilot.sh <blocks.tsv> [models=readerv2] [par=4]
# Results: data/PHerc0175A/runs-aws/<date>_inkfirst-pilot/ (progress.log, timings.tsv, <block>/summary.npz, glow.png, galleries).
export INSTANCE_TYPES="g5.4xlarge g6.4xlarge" MARKET=ondemand ONDEMAND_PRICE=1.624 FLEET_MAX_HOURS=${FLEET_MAX_HOURS:-3} RETRY_MINUTES=${RETRY_MINUTES:-20}
AWS=$(cd "$(dirname "$0")/../../../infra/aws" && pwd)   # the shared AWS scripts (lib.sh, spot_*.sh) and state
export ISTATE=${ISTATE:-$AWS/state/inkfirst-pilot}
source "$AWS/lib.sh"
BL=$1; MODELS=${2:-readerv2}; PAR=${3:-4}
U=https://vesuvius-challenge-open-data.s3.amazonaws.com/PHerc0175A
CT=$U/volumes/20250521115057-8.640um-1.2m-116keV-masked.zarr
PRED=$U/representations/predictions/surfaces/20250521115057-surface-20260413222639-surface-m7-L0-th0.2.zarr
OUT=$ROOT/data/PHerc0175A/runs-aws/$(date -u +%Y-%m-%d)_inkfirst-pilot; mkdir -p "$OUT"; cp "$BL" "$OUT/blocks.tsv"
check_account
fetch_results(){ [ -n "$(instance_ip)" ] && rsync_from /opt/scroll/results/inkfirst/ "$OUT/" < /dev/null 2>/dev/null || true; }
teardown(){ pkill -TERM -P $$ 2>/dev/null; sleep 1; log "fetching results and tearing down"; fetch_results; bash "$HERE/spot_down.sh" < /dev/null; bash "$HERE/spot_status.sh" < /dev/null 2>&1 | tail -3; }
trap teardown EXIT
T0=$(date +%s)
bash "$HERE/spot_up.sh"
TYPE=$(cat "$ISTATE/instance_type"); log "instance type: $TYPE"
case $TYPE in g5.4xlarge) export ONDEMAND_PRICE=1.624;; g6.4xlarge) export ONDEMAND_PRICE=1.323;; *) echo "REFUSED: $TYPE is not an approved type" >&2; exit 5;; esac
bash "$HERE/spot_push.sh"
rssh 'mkdir -p /opt/scroll/bin/ink-first-src /opt/scroll/jobs /opt/scroll/results/inkfirst' < /dev/null
rsync_to "$ROOT/experiments/ink-first/tool/src/" /opt/scroll/bin/ink-first-src/ < /dev/null
rsync_to "$ROOT/experiments/ink-first/inkfirst_block_summary.py" /opt/scroll/bin/ < /dev/null
rsync_to "$ROOT/experiments/ink-first/viz_glow.py" /opt/scroll/bin/ < /dev/null
rsync_to "$ROOT/experiments/ink-first/aws/inkfirst_blocks.sh" /opt/scroll/bin/ < /dev/null
rsync_to "$BL" /opt/scroll/jobs/blocks.tsv < /dev/null
rssh "cd /opt/scroll && nohup bash /opt/scroll/bin/inkfirst_blocks.sh /opt/scroll/jobs/blocks.tsv $CT $PRED 8.64 $MODELS 96 256 $PAR > /opt/scroll/results/inkfirst/run.log 2>&1 < /dev/null &" < /dev/null
log "started: $(( $(wc -l < "$BL") - 1 )) blocks, $MODELS, $PAR cutters"
while true; do
  sleep 60
  p=$(rssh 'tail -1 /opt/scroll/results/inkfirst/progress.log 2>/dev/null' < /dev/null || echo "(ssh failed)")
  log "progress: $p"
  echo "$p" | grep -q BLOCKS-EXIT && break
  [ $(( $(date +%s) - T0 )) -gt $(( FLEET_MAX_HOURS * 3600 - 600 )) ] && { log "close to the hard limit: stopping"; break; }
done
log "pilot finished in $(( ($(date +%s) - T0) / 60 )) min"
