#!/usr/bin/env bash
# Push our pipeline scripts (box/bin incl. Nieuwlaar's MIT ink343 scripts) and the remote job scripts; finish model setup.
source "$(dirname "$0")/lib.sh"
[ -n "$(instance_ip)" ] || { echo "no instance in aws/state" >&2; exit 4; }
rssh 'mkdir -p /opt/scroll/bin /opt/scroll/jobs /opt/scroll/results'
rsync_to "$ROOT/box/bin/ink343" /opt/scroll/bin/
rsync_to "$HERE/remote/" /opt/scroll/bin/
rsync_to "$ROOT/box/bin/stroke_score.py" /opt/scroll/bin/
rssh 'bash /opt/scroll/bin/setup_models.sh'
# Scan-Quality-Map (jcooperkai-sys/Scan-Quality-Map, MIT): per-segment scan-quality maps next to the ink maps. Non-fatal.
rssh 'cd /opt/scroll && UV=$(command -v uv || echo ~/.local/bin/uv) && ($UV venv -q -p 3.12 sqm-venv && $UV pip install -q -p sqm-venv/bin/python git+https://github.com/jcooperkai-sys/Scan-Quality-Map) > /opt/scroll/sqm-install.log 2>&1 && /opt/scroll/sqm-venv/bin/sqm --help > /dev/null 2>&1 && echo SQM-OK || echo "SQM-INSTALL-FAILED (see /opt/scroll/sqm-install.log)"'
# Lasagna (villa/lasagna) for on-worker flattening of snapped meshes; only when the run ships unflattened windings.
if [ "${FLATTEN:-0}" = 1 ]; then
  rssh 'cd /opt/scroll/villa/lasagna && export PATH=$HOME/.local/bin:$PATH && python3 scripts/bootstrap_venv.py > /opt/scroll/lasagna-env.log 2>&1 && echo LASAGNA-OK || echo "LASAGNA-FAILED (see /opt/scroll/lasagna-env.log)"'
fi
