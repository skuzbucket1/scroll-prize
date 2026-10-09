#!/usr/bin/env bash
# Re-run the (fixed) bootstrap on fleet workers that are already running, then push the pipeline. Use after a bootstrap
# failure that was not the instance's fault (e.g. an apt mirror mid-sync) instead of paying for new launches.
# The hard limit restarts: shutdown -h +FLEET_MAX_HOURS*60 from the re-run.   Usage: aws/fleet_rebootstrap.sh [max_hours=2]
source "$(dirname "$0")/lib.sh"
check_account
P=$STATE/fleet/plan.tsv; [ -s "$P" ] || { echo "no plan" >&2; exit 2; }
MH=${1:-2}
for w in $(cut -f1 "$P" | sort -u); do
  ( export ISTATE=$STATE/fleet/$w; [ -n "$(instance_ip)" ] || { echo "$w no instance"; exit 0; }
    UD=$ISTATE/userdata.sh
    sed -e "s|@MAX_MINUTES@|$(( MH * 60 ))|g" -e "s|@VILLA_COMMIT@|$VILLA_COMMIT|g" -e "s|@VC3D_RELEASE@|$VC3D_RELEASE|g" "$HERE/userdata.sh.tmpl" > "$UD"
    rsync_to "$UD" /tmp/userdata.sh
    rssh 'pkill -f "[r]un_batch.sh"; pkill -f "[r]un_segment.sh"; sudo rm -f /opt/scroll/BOOTSTRAP-FAILED /opt/scroll/BOOTSTRAP-DONE; sudo nohup bash /tmp/userdata.sh > /dev/null 2>&1 < /dev/null &' || true
    log "$w re-bootstrapping"
    for i in $(seq 1 120); do
      st=$(rssh 'test -f /opt/scroll/BOOTSTRAP-DONE && echo done || (test -f /opt/scroll/BOOTSTRAP-FAILED && echo failed) || echo wait' 2>/dev/null || echo wait)
      [ "$st" = done ] && break
      [ "$st" = failed ] && { rssh 'tail -20 /var/log/scroll-bootstrap.log'; echo "$w BOOTSTRAP FAILED again"; exit 7; }
      sleep 15
    done
    [ "$st" = done ] || { echo "$w bootstrap timed out"; exit 8; }
    "$HERE/spot_push.sh" >> "$STATE/fleet/$w.up.log" 2>&1 && echo "$w READY" || echo "$w PUSH FAILED" ) &
  sleep 2
done
wait
