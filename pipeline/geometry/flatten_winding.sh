#!/usr/bin/env bash
# Flatten one tifxyz segment with Lasagna (the organisers' recommended step before rendering).
# Usage: flatten_winding.sh <tifxyz dir (abs)> <out dir (abs)> [CUDA GPU UUID]
# Output: <out dir>/tifxyz/flatten.tifxyz ; log <out dir>/flatten.log ; marker FLATTEN-EXIT in the log.
set -uo pipefail
case "$*" in *GPU-33b8aac6-6d34-6282-b644-f5407aa8f190*) echo "REFUSED: GTX 1660 SUPER is not usable" >&2; exit 97;; esac
SEG=$1; OUT=$2; export CUDA_VISIBLE_DEVICES=${3:-GPU-7937f33e-73c8-2a4f-d7c6-9c4c3c20c74f}
mkdir -p "$OUT"
printf '{"external_surfaces": [{"path": "%s"}]}\n' "$SEG" > "$OUT/flatten_input.json"
cd ~/scroll-prizes/villa/lasagna
t0=$(date +%s)
.venv/bin/python fit.py configs/flatten_fast_nofilter.json "$OUT/flatten_input.json" --out-dir "$OUT" --device cuda > "$OUT/flatten.log" 2>&1; rc=$?
echo "[$(date -Is)] flatten rc=$rc in $(( $(date +%s)-t0 ))s -> $(ls -d $OUT/tifxyz/*.tifxyz 2>/dev/null | head -1)" | tee -a "$OUT/flatten.log"
echo "FLATTEN-EXIT: $rc" >> "$OUT/flatten.log"
exit $rc
