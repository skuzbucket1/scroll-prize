#!/usr/bin/env bash
# Proof of concept, end to end: request a spot instance, bootstrap, run ONE ink map (ink_9um seed 42, d = +1) on the
# PHerc. 343 winning segment (our positive control; mesh by Erwin Nieuwlaar, MIT), fetch the results, terminate.
# Expected cost: well under $1 (about 30-40 min at ~$0.31/h on g4dn.2xlarge spot). Teardown runs even on failure.
# Usage: aws/poc.sh [--keep]   (--keep leaves the instance running for inspection; terminate later with aws/spot_down.sh)
source "$(dirname "$0")/lib.sh"
KEEP=0; [ "${1:-}" = "--keep" ] && KEEP=1
save_logs(){ [ -n "$(instance_ip)" ] && rssh 'cat /var/log/scroll-bootstrap.log; echo ===; cat /opt/scroll/bootstrap.times /opt/scroll/torch.txt 2>/dev/null' > "$STATE/bootstrap-$(instance_id).log" 2>/dev/null || true; }
[ $KEEP -eq 1 ] || trap 'save_logs; log "teardown"; "$HERE/spot_down.sh"' EXIT
T0=$(date +%s)
"$HERE/spot_up.sh"
"$HERE/spot_push.sh"
SEG=$ROOT/data/prior-art/pherc343-first-letters/outputs/concat_w047-w048_R5B2_z9500-11000.tifxyz
[ -d "$SEG" ] || { echo "control mesh missing: clone https://github.com/Nieuwlaar/pherc343-first-letters into data/prior-art/" >&2; exit 9; }
URL=https://vesuvius-challenge-open-data.s3.amazonaws.com/PHerc0343/volumes/20250521140437-8.640um-1.2m-116keV-masked.zarr
"$HERE/spot_run.sh" control343 "$SEG" "$URL" 8.64 hybrid_3d2d-seed42 1
"$HERE/spot_fetch.sh"
log "POC done in $(( ($(date +%s)-T0) / 60 )) min; compare data/aws-results/*/control343/previews/hybrid_3d2d-seed42_d+1_read.png with the GPU box's control preview"
