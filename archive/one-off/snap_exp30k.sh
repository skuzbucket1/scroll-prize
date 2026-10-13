#!/bin/bash
# Post-hoc snap (Nieuwlaar's snap_meshes.py, MIT) of the exp-30k windings onto the m7 surface prediction (level 0 band mirror),
# then audit + render two windings for a visual check.
S=~/scroll-prizes; D=/mnt/nvme/scroll-prizes/data/PHerc0191
until grep -q "SURFMIRROR-EXIT: 0" $S/mirror-surf-band.log 2>/dev/null; do sleep 120; done
export SURF_ZARR=$D/surf-m7/20250821151635-surface-20260413222639-surface-m7-L0-th0.2.zarr
RUN=$(ls -d $D/spiral-output/*exp-30k); MESHES=$(ls -d $RUN/meshes/fitted_*/ | head -1); OUT=$D/snapped/exp-30k
mkdir -p $OUT; ls $MESHES | grep -E "^w0[2-9][0-9]_exp-30k$|^w1[01][0-9]_exp-30k$" > $OUT/windings.txt; wc -l < $OUT/windings.txt
cd $S && t0=$(date +%s)
villa/vesuvius/.venv/bin/python -I bin/snap_meshes_nieuwlaar.py "$MESHES" PHerc0191 "$OUT" --windings $OUT/windings.txt --z0 9000 --z1 10000 --level 0 --procs 4 > $OUT/snap.log 2>&1; rc=$?
echo "snap rc=$rc in $(( $(date +%s)-t0 ))s"; tail -4 $OUT/snap.log | cut -c1-200
# audit: how much did satisfaction-relevant geometry move? (in-mask + report columns)
head -3 $OUT/snap_report.tsv; awk -F'\t' 'NR>1 {s+=$4; m+=$5; n++} END {if (n) printf "mean frac_snapped %.3f  mean median_abs_off %.2f vox over %d windings\n", s/n, m/n, n}' $OUT/snap_report.tsv
# render + ink two snapped windings for the eye (same QA as pilot)
for w in w040_exp-30k w070_exp-30k; do $S/bin/patch_qa.sh $OUT/$w $D/snapped/qa_exp-30k_$w GPU-7937f33e-73c8-2a4f-d7c6-9c4c3c20c74f 2>&1 | grep -E "geometry|selfcross|FAILED" | head -3; done
echo "SNAP-EXIT: $rc"
