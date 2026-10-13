#!/bin/bash
# Wait for the exp30k-z11200 fit, then snap every fitted winding onto the m7 surface prediction (Nieuwlaar's snap, MIT).
# Output: data/PHerc0191/snapped/exp30k-z11200/<winding>/ (tifxyz) + snap_report.tsv; marker SNAPNEW-EXIT in the log.
S=~/scroll-prizes; D=/mnt/nvme/scroll-prizes/data/PHerc0191; TAG=exp30k-z11200; export TMPDIR=/mnt/nvme/scroll-prizes/tmp
until grep -q "FIT-EXIT" $S/fit-$TAG.log 2>/dev/null; do sleep 60; done
grep "FIT-EXIT" $S/fit-$TAG.log; grep -E "satisfied|loss" $S/fit-$TAG.log | tail -3
until grep -q "SURFMIRROR-EXIT: 0" $S/mirror-surf-z11k.log 2>/dev/null; do sleep 30; done
export SURF_ZARR=$D/surf-m7/20250821151635-surface-20260413222639-surface-m7-L0-th0.2.zarr
RUN=$(ls -td $D/spiral-output/*$TAG*/ | head -1); MESHES=$(ls -d $RUN/meshes/fitted_*/ | head -1); OUT=$D/snapped/$TAG
mkdir -p $OUT; ls $MESHES | grep -E "^w[0-9]+" > $OUT/windings.txt
echo "[$(date -Is)] snap $(wc -l < $OUT/windings.txt) windings from $MESHES"
cd $S && t0=$(date +%s)
$S/villa/vesuvius/.venv/bin/python -I bin/snap_meshes_nieuwlaar.py "$MESHES" PHerc0191 "$OUT" --windings $OUT/windings.txt \
   --z0 11200 --z1 12200 --level 0 --procs 3 > $OUT/snap.log 2>&1; rc=$?
echo "[$(date -Is)] snap rc=$rc in $(( $(date +%s)-t0 ))s"; tail -2 $OUT/snap.log | cut -c1-160
awk -F'\t' 'NR>1 {s+=$3; n++} END {if (n) printf "windings %d, mean frac_snapped %.3f\n", n, s/n}' $OUT/snap_report.tsv 2>/dev/null
echo "SNAPNEW-EXIT: $rc"
