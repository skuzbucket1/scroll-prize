#!/usr/bin/env bash
# Direction-field tracer test, attempt 2: Fiber output converted to the tracer's x/y/z layout (bin/make_dirfield_zarr.py),
# used as a "normal" field with the Fiber presence map as the confidence weight. Honest exit codes.
set -uo pipefail; export PATH=$HOME/.local/bin:$PATH
D=/mnt/nvme/scroll-prizes/data/PHerc0191; F=$D/fiber/band8500-10500; G=$D/grow-test; mkdir -p $G/dirfield2
until grep -q 'DIRFIELD-EXIT' ~/scroll-prizes/dirfield-build.log 2>/dev/null; do sleep 60; done
grep -q 'DIRFIELD-EXIT: 0' ~/scroll-prizes/dirfield-build.log || { echo "dirfield build failed"; echo "DIRTEST2-EXIT: 90"; exit 1; }
SURF="https://vesuvius-challenge-open-data.s3.amazonaws.com/PHerc0191/representations/predictions/surfaces/20250821151635-surface-20260413222639-surface-m7-L0-th0.2.zarr"
fail=0
for GEN in 70 150; do
  P=$G/dirfield2/params_$GEN.json
  cat > "$P" <<JSON
{"mode":"seed","cache_size":4000000000,"generations":$GEN,"thread_limit":4,
 "direction_fields":[{"zarr":"$F/dirfield.zarr","dir":"normal","scale":2,"weight_zarr":"$F/fiber_presence.ome.zarr","weight":1.0}]}
JSON
  mkdir -p $G/dirfield2/out_$GEN; t0=$(date +%s)
  vc_grow_seg_from_seed -v "$SURF" -t $G/dirfield2/out_$GEN/ -p "$P" --seed 5259 2852 9404 > $G/dirfield2/grow_$GEN.log 2>&1; rc=$?
  echo "[$(date -Is)] grow gen=$GEN rc=$rc in $(( $(date +%s)-t0 ))s: $(grep -E 'generated surface|discard|area' $G/dirfield2/grow_$GEN.log | tail -1 | cut -c1-160)"
  [ $rc -ne 0 ] && { fail=1; tail -3 $G/dirfield2/grow_$GEN.log | cut -c1-200; continue; }
  M=$(ls -d $G/dirfield2/out_$GEN/auto_grown_* 2>/dev/null | tail -1)
  if [ -n "$M" ]; then
    ~/scroll-prizes/bin/patch_qa.sh "$M" "$G/dirfield2/qa_$GEN" GPU-7937f33e-73c8-2a4f-d7c6-9c4c3c20c74f 2>&1 | grep -E 'geometry|selfcross|render|ink|area|cm2|FAILED' | head -8
  else
    echo "no auto_grown_* patch written for gen=$GEN"; fail=1
  fi
done
echo "DIRTEST2-EXIT: $fail"
