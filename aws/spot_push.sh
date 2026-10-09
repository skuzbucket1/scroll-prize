#!/usr/bin/env bash
# Push our pipeline scripts (box/bin incl. Nieuwlaar's MIT ink343 scripts) and the remote job scripts; finish model setup.
source "$(dirname "$0")/lib.sh"
[ -n "$(instance_ip)" ] || { echo "no instance in aws/state" >&2; exit 4; }
rssh 'mkdir -p /opt/scroll/bin /opt/scroll/jobs /opt/scroll/results'
rsync_to "$ROOT/box/bin/ink343" /opt/scroll/bin/
rsync_to "$HERE/remote/" /opt/scroll/bin/
rsync_to "$ROOT/box/bin/stroke_score.py" /opt/scroll/bin/
rssh 'bash /opt/scroll/bin/setup_models.sh'
