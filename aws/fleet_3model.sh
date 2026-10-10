#!/usr/bin/env bash
# Three-model ink pass (ink_9um seeds 42/43 + dense_native, no Hecate) at depths 0,+1 on every flattened PHerc0191 winding
# that the box has not ensembled and that is not in EXCLUDE, with the stroke score computed on each worker. SPENDS MONEY.
# Usage: aws/fleet_3model.sh N --yes          then: aws/fleet_rank.sh  (LOOK rows -> Hecate pass / eyes)
# Rationale (2026-10-09): Hecate costs ~22-25 min per pass on a T4 (two passes per depth) = ~85 of ~100 min per winding;
# three models separate the PHerc. 343 control from PHerc0191 negatives almost as well (6.3x vs <= 1.5x stroke area).
HERE=$(cd "$(dirname "$0")" && pwd)
N=${1:?usage: fleet_3model.sh N --yes}; [ "${2:-}" = "--yes" ] || { echo "refusing to launch without --yes"; exit 2; }
[ -f "$(dirname "$0")/spot.env" ] && source "$(dirname "$0")/spot.env"; BOX=${BOX:?set BOX in aws/spot.env}
EXCLUDE=${EXCLUDE:-w068 w069 w070 w071 w072 w073 w074}     # box four-model queue + the first AWS run
WS=$(ssh -o BatchMode=yes $BOX 'ls -d /mnt/nvme/scroll-prizes/data/PHerc0191/flatten/exp-30k-snapped-w*/tifxyz/flatten.tifxyz' |
     sed -E 's|.*snapped-(w[0-9]+)/.*|\1|' | sort | grep -vxF -f <(tr ' ' '\n' <<< "$EXCLUDE") | tr '\n' ' ')
echo "$(wc -w <<< "$WS" | tr -d ' ') windings: $WS"
MODELS=hybrid_3d2d-seed42,hybrid_3d2d-seed43,dnative DEPTHS=${DEPTHS:-0,1} exec "$HERE/fleet.sh" "$N" --yes $WS
