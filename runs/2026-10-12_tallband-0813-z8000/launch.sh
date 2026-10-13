#!/bin/bash
# PHerc0813 tall band 2 (z 8000-10500): fit now on GPU 2 (the fit needs only tracks + lasagna + umbilicus, all local), mirror CT
# level 0 rows 62-81 and m7 rows 41-53 in parallel, snap when both are done. Markers: MIRROR-DONE, FIT-EXIT, SNAP-EXIT, TALL-GATE.
R=/mnt/nvme/scroll-prizes/runs/2026-10-12_tallband-0813-z8000; B=~/scroll-prizes/bin
U=https://vesuvius-challenge-open-data.s3.amazonaws.com; M="python3 -I $B/mirror_s3_v2.py"; S=/mnt/nvme/scroll-prizes/data/PHerc0813/source
V=PHerc0813/volumes/20250821151723-9.362um-1.2m-113keV-masked.zarr; VL=$S/volume/20250821151723-9.362um-1.2m-113keV-masked.zarr
SF=PHerc0813/representations/predictions/surfaces/20250821151723-surface-20260413222639-surface-m7-L0-th0.2; SL=$S/surface-m7/$(basename $SF).zarr
G2=GPU-7937f33e-73c8-2a4f-d7c6-9c4c3c20c74f; FIT=exp30k-z8000
( for z in $(seq 62 81); do $M $U "$V/0/$z/" $VL/0/$z 16 2>&1 | tail -1; done
  for z in $(seq 41 53); do $M $U "$SF.zarr/0/$z/" $SL/0/$z 16 2>&1 | tail -1; done
  echo "[$(date -Is)] MIRROR-DONE; free: $(df -h /mnt/nvme | tail -1)" ) > $R/mirror.log 2>&1 &
echo "[$(date -Is)] fit on GPU 2"
bash $B/fit_band.sh PHerc0813 $FIT $G2 8000 10500 30000 > $R/fit.log 2>&1
until grep -q MIRROR-DONE $R/mirror.log; do sleep 60; done
grep -q "FIT-EXIT: 0" $R/fit.log && bash $B/snap_band.sh PHerc0813 $FIT 8000 10500 > $R/snap.log 2>&1
echo "[$(date -Is)] TALL-GATE: fit + snap done; check fit.log / snap.log before flatten, render and ink"
wait
