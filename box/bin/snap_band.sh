#!/usr/bin/env bash
# Snap every fitted winding of one fit onto the scroll's m7 surface prediction (Nieuwlaar's snap, MIT), any scroll.
# In: data/<scroll>/geometry/<fit-id>/fit/meshes/fitted_*/wNNN, data/<scroll>/source/surface-m7/*.zarr (level 0 over the band).
# Out: data/<scroll>/geometry/<fit-id>/snapped/<winding>/ (tifxyz) + snap_report.tsv. Usage: snap_band.sh <scroll> <fit-id> <z0> <z1>
# Marker: SNAP-EXIT.
set -uo pipefail
SC=$1; FIT=$2; Z0=$3; Z1=$4; S=~/scroll-prizes; D=/mnt/nvme/scroll-prizes/data/$SC; G=$D/geometry/$FIT
export TMPDIR=/mnt/nvme/scroll-prizes/scratch SURF_ZARR=$(ls -d $D/source/surface-m7/*.zarr | head -1)
MESHES=$(ls -d $G/fit/meshes/fitted_*/ | head -1); OUT=$G/snapped; mkdir -p $OUT
ls $MESHES | grep -E "^w[0-9]+" > $OUT/windings.txt
echo "[$(date -Is)] snap $(wc -l < $OUT/windings.txt) windings from $MESHES onto $SURF_ZARR"; t0=$(date +%s)
cd $S && $S/villa/vesuvius/.venv/bin/python -I bin/snap_meshes_nieuwlaar.py "$MESHES" $SC "$OUT" --windings $OUT/windings.txt \
   --z0 $Z0 --z1 $Z1 --level 0 --procs 3 > $OUT/snap.log 2>&1; rc=$?
echo "[$(date -Is)] snap rc=$rc in $(( $(date +%s)-t0 ))s"; tail -2 $OUT/snap.log | cut -c1-160
awk -F'\t' 'NR>1 {s+=$3; n++} END {if (n) printf "windings %d, mean frac_snapped %.3f\n", n, s/n}' $OUT/snap_report.tsv 2>/dev/null
echo "SNAP-EXIT: $rc"
