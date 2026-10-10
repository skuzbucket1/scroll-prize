#!/bin/bash
# Snap (Nieuwlaar's snap_meshes.py, MIT) + Lasagna-flatten the community PHerc0191 fit windings (rodriguescarson/
# eligible-scroll-spiral-fits, z 11600-12400) so they can go through render + ink like our own windings.
# Usage: prep_community.sh <CUDA GPU UUID for flatten>      Output: data/PHerc0191/flatten/community-snapped-wNNN/tifxyz/flatten.tifxyz
case "$*" in *GPU-33b8aac6*) echo "REFUSED: GTX 1660 SUPER"; exit 97;; esac
GPU=$1; S=~/scroll-prizes; D=/mnt/nvme/scroll-prizes/data/PHerc0191; export TMPDIR=/mnt/nvme/scroll-prizes/tmp
until grep -q "SURFMIRROR-EXIT: 0" $S/mirror-surf-z11k.log 2>/dev/null; do sleep 30; done
export SURF_ZARR=$D/surf-m7/20250821151635-surface-20260413222639-surface-m7-L0-th0.2.zarr
M=$D/community-fit; OUT=$D/snapped/community; mkdir -p $OUT; ls $M | grep -E "^w[0-9]+$" > $OUT/windings.txt
echo "[$(date -Is)] snap $(wc -l < $OUT/windings.txt) windings"
cd $S && $S/villa/vesuvius/.venv/bin/python -I bin/snap_meshes_nieuwlaar.py "$M" PHerc0191 "$OUT" --windings $OUT/windings.txt \
   --z0 11100 --z1 12600 --level 0 --procs 3 > $OUT/snap.log 2>&1; echo "[$(date -Is)] snap rc=$?"; tail -3 $OUT/snap.log | cut -c1-200
head -1 $OUT/snap_report.tsv 2>/dev/null; cat $OUT/snap_report.tsv 2>/dev/null | tail -n +2 | cut -f1-6
for w in $(cat $OUT/windings.txt); do
  SEG=$(ls -d $OUT/${w}* 2>/dev/null | head -1); [ -n "$SEG" ] || { echo "no snapped $w"; continue; }
  $S/bin/flatten_winding.sh "$SEG" $D/flatten/community-snapped-$w $GPU > /dev/null 2>&1
  echo "[$(date -Is)] flatten $w rc=$? $(ls $D/flatten/community-snapped-$w/tifxyz/ 2>/dev/null | tr '\n' ' ')"
done
echo "PREPCOMM-EXIT: 0"
