#!/usr/bin/env bash
# Terminate every Project-tagged instance (all fleet workers) and clear fleet instance state (plan and results stay).
source "$(dirname "$0")/lib.sh"
"$HERE/spot_down.sh" --all
for d in "$STATE"/fleet/w*/; do [ -d "$d" ] && rm -f "$d"/instance_id "$d"/instance_ip "$d"/launched_at "$d"/instance_type; done
log "fleet state cleared"
