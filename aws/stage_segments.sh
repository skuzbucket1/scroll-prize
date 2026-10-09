#!/usr/bin/env bash
# Pull flattened winding meshes from the GPU box to the Mac and write the fleet manifest.
# Usage: aws/stage_segments.sh [--skip-done] [w070 w069 ... | all]
#   all          every winding that has a flattened mesh on the box (data/PHerc0191/flatten/exp-30k-snapped-wNNN)
#   --skip-done  leave out windings whose four-model ensemble already exists on the box (ink-triage/ensemble/<w>)
# Output: data/aws-stage/segments/<name>/flatten.tifxyz and data/aws-stage/manifest.tsv
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd); ROOT=$(cd "$HERE/.." && pwd)
BOX=${BOX:-tbienapfl@100.74.214.106}; D=/mnt/nvme/scroll-prizes/data/PHerc0191
URL=https://vesuvius-challenge-open-data.s3.amazonaws.com/PHerc0191/volumes/20250821151635-9.362um-1.2m-113keV-masked.zarr
MODELS=${MODELS:-hybrid_3d2d-seed42,hybrid_3d2d-seed43,dnative,hecate}; DEPTHS=${DEPTHS:-0,1}
SKIP=0; [ "${1:-}" = "--skip-done" ] && { SKIP=1; shift; }
WS="$*"; [ -z "$WS" ] || [ "$WS" = all ] && WS=$(ssh -o BatchMode=yes $BOX "ls -d $D/flatten/exp-30k-snapped-w*/tifxyz/flatten.tifxyz" | sed -E 's|.*snapped-(w[0-9]+)/.*|\1|' | sort)
[ $SKIP -eq 1 ] && DONE=$(ssh -o BatchMode=yes $BOX "ls $D/ink-triage/ensemble 2>/dev/null" || true) || DONE=""
ST=$ROOT/data/aws-stage; mkdir -p $ST/segments; : > $ST/manifest.tsv
n=0
for w in $WS; do
  echo " $DONE " | grep -q " $w " && { echo "skip $w (ensemble exists on the box)"; continue; }
  name=exp30k_snapped_$w
  mkdir -p $ST/segments/$name
  rsync -a -e "ssh -o BatchMode=yes" "$BOX:$D/flatten/exp-30k-snapped-$w/tifxyz/flatten.tifxyz" "$ST/segments/$name/" || { echo "missing $w"; continue; }
  printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$name" "$ST/segments/$name/flatten.tifxyz" "$URL" 9.362 "$MODELS" "$DEPTHS" >> $ST/manifest.tsv
  n=$((n + 1))
done
echo "staged $n segments -> $ST/manifest.tsv ($(du -sh $ST/segments | cut -f1)); models=$MODELS depths=$DEPTHS"
