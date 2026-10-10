#!/usr/bin/env bash
# Pull flattened winding meshes from the GPU box to the Mac and write the fleet manifest.
# Usage: aws/stage_segments.sh [--skip-done] [w070 w069 ... | all]
#   all          every winding that has a flattened mesh on the box (data/PHerc0191/flatten/exp-30k-snapped-wNNN)
#   --skip-done  leave out windings whose four-model ensemble already exists on the box (ink-triage/ensemble/<w>)
#   FLATTEN_PREFIX (default exp-30k-snapped) / NAME_PREFIX (default exp30k_snapped) select another flattened set,
#   e.g. FLATTEN_PREFIX=community-snapped NAME_PREFIX=community_snapped for the community PHerc0191 fit.
#   SNAPPED_DIR=<box dir of snapped windings> NAME_PREFIX=<prefix> ships SNAPPED (unflattened) meshes instead; the workers
#   flatten them (needs FLATTEN=1 at launch). Windings = subfolder names (e.g. w070_exp30k-z11200 -> w070).
# Output: data/aws-stage/segments/<name>/flatten.tifxyz (or <name>/<snapped dir>) and data/aws-stage/manifest.tsv
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd); ROOT=$(cd "$HERE/.." && pwd)
[ -f "$(dirname "$0")/spot.env" ] && source "$(dirname "$0")/spot.env"; BOX=${BOX:?set BOX in aws/spot.env}; D=/mnt/nvme/scroll-prizes/data/PHerc0191
URL=https://vesuvius-challenge-open-data.s3.amazonaws.com/PHerc0191/volumes/20250821151635-9.362um-1.2m-113keV-masked.zarr
MODELS=${MODELS:-hybrid_3d2d-seed42,hybrid_3d2d-seed43,dnative,hecate}; DEPTHS=${DEPTHS:-0,1}
FP=${FLATTEN_PREFIX:-exp-30k-snapped}; NP=${NAME_PREFIX:-exp30k_snapped}
SKIP=0; [ "${1:-}" = "--skip-done" ] && { SKIP=1; shift; }
SD=${SNAPPED_DIR:-}
if [ -n "$SD" ]; then
  WS="$*"; [ -z "$WS" ] || [ "$WS" = all ] && WS=$(ssh -o BatchMode=yes $BOX "ls $SD" | grep -E '^w[0-9]+' | sed -E 's/^(w[0-9]+).*/\1/' | sort -u)
else
  WS="$*"; [ -z "$WS" ] || [ "$WS" = all ] && WS=$(ssh -o BatchMode=yes $BOX "ls -d $D/flatten/$FP-w*/tifxyz/flatten.tifxyz" | sed -E 's|.*-(w[0-9]+)/tifxyz/.*|\1|' | sort)
fi
[ $SKIP -eq 1 ] && DONE=$(ssh -o BatchMode=yes $BOX "ls $D/ink-triage/ensemble 2>/dev/null" || true) || DONE=""
ST=$ROOT/data/aws-stage; mkdir -p $ST/segments; : > $ST/manifest.tsv
n=0
for w in $WS; do
  echo " $DONE " | grep -q " $w " && { echo "skip $w (ensemble exists on the box)"; continue; }
  name=${NP}_$w
  mkdir -p $ST/segments/$name
  if [ -n "$SD" ]; then
    src=$(ssh -o BatchMode=yes $BOX "ls -d $SD/${w}* 2>/dev/null | head -1"); [ -n "$src" ] || { echo "missing $w"; continue; }
    rsync -a -e "ssh -o BatchMode=yes" "$BOX:$src" "$ST/segments/$name/" || { echo "missing $w"; continue; }
    seg="$ST/segments/$name/$(basename "$src")"
  else
    rsync -a -e "ssh -o BatchMode=yes" "$BOX:$D/flatten/$FP-$w/tifxyz/flatten.tifxyz" "$ST/segments/$name/" || { echo "missing $w"; continue; }
    seg="$ST/segments/$name/flatten.tifxyz"
  fi
  printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$name" "$seg" "$URL" 9.362 "$MODELS" "$DEPTHS" >> $ST/manifest.tsv
  n=$((n + 1))
done
echo "staged $n segments -> $ST/manifest.tsv ($(du -sh $ST/segments | cut -f1)); models=$MODELS depths=$DEPTHS"
