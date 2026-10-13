#!/usr/bin/env bash
set -u; cd ~/scroll-prizes
S3=https://vesuvius-challenge-open-data.s3.amazonaws.com; SV=8.64um-1.2m-116keV-volume-20250521135224.zarr; rc=0
for seg in 20251028222030-auto_grown_20251028222030940 20251028225813-auto_grown_20251028225813045 20251028213516-auto_grown_20251028213516907 20251028220042-auto_grown_20251028220042762 20251028220955-auto_grown_20251028220955262 20251029010146-auto_grown_20251029010146642; do
  python3 -I bin/fetch_zarr.py "$S3/PHerc0800/segments/$seg/surface-volumes/$SV" "data/PHerc0800/segments/$seg/surface-volumes/$SV" 0,1,2,3,4,5 8 || rc=1
done
du -sh data/PHerc0800; echo "DL0800-EXIT: $rc"
