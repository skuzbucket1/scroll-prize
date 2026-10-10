#!/usr/bin/env bash
# One command: stage -> plan -> launch N workers -> run -> poll + fetch -> fetch -> terminate. SPENDS MONEY.
# Usage: aws/fleet.sh N --yes [winding list | all]      e.g. aws/fleet.sh 10 --yes all
#        aws/fleet.sh N --yes --resume                  (skip stage/plan/launch: workers already bootstrapped and pushed)
#   MIN_PER_SEGMENT=15 sizes the plan and hard limit (default 35 = four models)
#   FETCH_MAPS=1 also copies the raw ink maps in the final fetch (~320 MB per segment; needed for bin/stroke_score.py)
# Teardown runs on exit, on failure and on Ctrl-C. Results: data/aws-results/fleet/<worker>/<segment>/ensemble/*.png
source "$(dirname "$0")/lib.sh"
N=${1:?usage: fleet.sh N --yes [windings|all]}; [ "${2:-}" = "--yes" ] || { echo "refusing to launch without --yes"; exit 2; }
shift 2
RESUME=0; [ "${1:-}" = "--resume" ] && { RESUME=1; shift; }   # workers already up and pushed (aws/fleet_rebootstrap.sh)
trap 'log "teardown"; "$HERE/fleet_fetch.sh" ${FETCH_MAPS:+--maps} || true; "$HERE/fleet_down.sh"' EXIT
if [ $RESUME -eq 0 ]; then
  "$HERE/stage_segments.sh" --skip-done "${@:-all}"
  PLAN=$("$HERE/fleet_plan.sh" "$N" "${MIN_PER_SEGMENT:-35}"); echo "$PLAN"
  MH=$(echo "$PLAN" | grep -oE 'FLEET_MAX_HOURS=[0-9]+' | cut -d= -f2)
  "$HERE/fleet_up.sh" --yes "${MH:-$MAX_HOURS}"
fi
"$HERE/fleet_run.sh"
while true; do
  sleep 300; S=$("$HERE/fleet_status.sh"); echo "$S" | tail -1
  "$HERE/fleet_fetch.sh" > /dev/null 2>&1 || true
  # every worker's batch has ended (all segments, plus the SQM step if on; even if a segment failed): stop paying
  NW=$(cut -f1 "$STATE/fleet/plan.tsv" | sort -u | wc -l | tr -d ' ')
  [ "$(echo "$S" | grep -c 'BATCH-EXIT')" -ge "$NW" ] && { log "all batches ended"; break; }
  [ -z "$(awsc ec2 describe-instances --filters "Name=tag:Project,Values=$PROJECT_TAG" "Name=instance-state-name,Values=running" --query 'Reservations[].Instances[].InstanceId' --output text)" ] && { log "no running workers left"; break; }
done
log "fleet finished"
