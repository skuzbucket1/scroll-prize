#!/usr/bin/env bash
# Tracer test with the community Lasagna normals as the direction field (converted by make_dirfield_zarr.py),
# plus the xy normal grids. Same seed/params as the Fiber-field normal-grid run (out_ng70) for a direct comparison.
set -uo pipefail; export PATH=$HOME/.local/bin:$PATH
S=~/scroll-prizes; D=/mnt/nvme/scroll-prizes/data/PHerc0191; G=$D/grow-test/dirfield2; LF=$D/fiber/dirfield_lasagna.zarr
until grep -q 'DIRFIELDL-EXIT' $S/dirfield-lasagna-build.log 2>/dev/null; do sleep 60; done
grep -q 'DIRFIELDL-EXIT: 0' $S/dirfield-lasagna-build.log || { echo "lasagna dirfield build failed"; echo "LASTRACE-EXIT: 90"; exit 1; }
cat > $G/params_lasagna70.json <<JSON
{"mode":"seed","cache_size":4000000000,"generations":70,"thread_limit":4,
 "normal_grid_path":"/mnt/nvme/scroll-prizes/data/PHerc0191/normal-grids","normal_grid_level":0,
 "direction_fields":[{"zarr":"$LF","dir":"normal","scale":2,"weight":1.0}]}
JSON
SURF="https://vesuvius-challenge-open-data.s3.amazonaws.com/PHerc0191/representations/predictions/surfaces/20250821151635-surface-20260413222639-surface-m7-L0-th0.2.zarr"
mkdir -p $G/out_lasagna70; t0=$(date +%s)
vc_grow_seg_from_seed -v "$SURF" -t $G/out_lasagna70/ -p $G/params_lasagna70.json --seed 5259 2852 9404 > $G/grow_lasagna70.log 2>&1; rc=$?
echo "[$(date -Is)] grow lasagna70 rc=$rc in $(( $(date +%s)-t0 ))s: $(grep -E 'generated surface' $G/grow_lasagna70.log | tail -1 | cut -c1-120)"
[ $rc -ne 0 ] && { tail -3 $G/grow_lasagna70.log | cut -c1-200; echo "LASTRACE-EXIT: $rc"; exit $rc; }
M=$(ls -d $G/out_lasagna70/auto_grown_* 2>/dev/null | tail -1)
[ -n "$M" ] && $S/bin/patch_qa.sh "$M" $G/qa_lasagna70 GPU-7937f33e-73c8-2a4f-d7c6-9c4c3c20c74f 2>&1 | grep -E 'geometry|selfcross|FAILED' | head -4
echo "LASTRACE-EXIT: 0"
