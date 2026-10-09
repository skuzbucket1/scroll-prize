#!/usr/bin/env bash
# One command: stage -> plan -> launch N workers -> run -> poll + fetch -> fetch -> terminate. SPENDS MONEY.
# Usage: aws/fleet.sh N --yes [winding list | all]      e.g. aws/fleet.sh 10 --yes all
# Teardown runs on exit, on failure and on Ctrl-C. Results: data/aws-results/fleet/<worker>/<segment>/ensemble/*.png
source "$(dirname "$0")/lib.sh"
N=${1:?usage: fleet.sh N --yes [windings|all]}; [ "${2:-}" = "--yes" ] || { echo "refusing to launch without --yes"; exit 2; }
shift 2
trap 'log "teardown"; "$HERE/fleet_fetch.sh" || true; "$HERE/fleet_down.sh"' EXIT
"$HERE/stage_segments.sh" --skip-done "${@:-all}"
PLAN=$("$HERE/fleet_plan.sh" "$N"); echo "$PLAN"
MH=$(echo "$PLAN" | grep -oE 'FLEET_MAX_HOURS=[0-9]+' | cut -d= -f2)
"$HERE/fleet_up.sh" --yes "${MH:-$MAX_HOURS}"
"$HERE/fleet_run.sh"
while true; do
  sleep 300; S=$("$HERE/fleet_status.sh"); echo "$S" | tail -1
  "$HERE/fleet_fetch.sh" > /dev/null 2>&1 || true
  echo "$S" | awk '/segments done:/ { split($3, a, "/"); exit !(a[1] == a[2] && a[2] > 0) }' && break
  [ -z "$(awsc ec2 describe-instances --filters "Name=tag:Project,Values=$PROJECT_TAG" "Name=instance-state-name,Values=running" --query 'Reservations[].Instances[].InstanceId' --output text)" ] && { log "no running workers left"; break; }
done
log "fleet finished"
