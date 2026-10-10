#!/bin/bash
# Phase B1 (research plan 2026-10-10, approved by Ted): mirror one band of PHerc0813 (z 12000-13000) and the scroll-wide
# inputs a spiral fit needs, into data/PHerc0813/source/. CT level 0 rows 93-101 (z 11904-13055) + levels 2-5 complete;
# m7 surface prediction level 0 rows 62-67 (192-voxel chunks, z 11904-13055); normal grids (umbilicus); Lasagna
# nx/ny/grad_mag levels 2-4; spiral tracks dataset. Resumable (size-verified). Marker: MIRROR0813-EXIT.
B=https://vesuvius-challenge-open-data.s3.amazonaws.com; M="python3 -I /home/tbienapfl/scroll-prizes/bin/mirror_s3_v2.py"
S=/mnt/nvme/scroll-prizes/data/PHerc0813/source; mkdir -p $S
V=PHerc0813/volumes/20250821151723-9.362um-1.2m-113keV-masked.zarr; VL=$S/volume/20250821151723-9.362um-1.2m-113keV-masked.zarr
SF=PHerc0813/representations/predictions/surfaces/20250821151723-surface-20260413222639-surface-m7-L0-th0.2
LA=PHerc0813/representations/predictions/lasagna/20250821151723-lasagna-20260419180421
echo "[$(date -Is)] start; free: $(df -h /mnt/nvme | tail -1)"
echo "== CT meta + levels 5..2"; $M $B "$V/" $VL 24 --levels 5,4,3,2 2>&1 | tail -3
for f in 0/.zarray 1/.zarray; do mkdir -p $VL/$(dirname $f); curl -s "$B/$V/$f" -o $VL/$f; done
for z in $(seq 93 101); do echo "== CT level 0 row $z"; $M $B "$V/0/$z/" $VL/0/$z 24 2>&1 | tail -1; done
echo "== m7 surface prediction band"; SL=$S/surface-m7/$(basename $SF).zarr; mkdir -p $SL/0
for f in .zattrs .zgroup 0/.zarray 1/.zarray; do mkdir -p $SL/$(dirname $f); curl -s "$B/$SF.zarr/$f" -o $SL/$f; done
for z in $(seq 62 67); do $M $B "$SF.zarr/0/$z/" $SL/0/$z 24 2>&1 | tail -1; done
echo "== normal grids"; $M $B "$SF.normal-grids/" $S/normal-grids 32 2>&1 | tail -2
echo "== Lasagna"; LL=$S/lasagna/$(basename $LA); mkdir -p $LL; curl -s "$B/$LA/PHerc0813.lasagna.json" -o $LL/PHerc0813.lasagna.json
for k in nx ny grad_mag; do $M $B "$LA/PHerc0813_$k.ome.zarr/" $LL/PHerc0813_$k.ome.zarr 24 --levels 2,3,4 2>&1 | tail -1; done
echo "== tracks"; mkdir -p $S/tracks
wget -q -r -np -nH --cut-dirs=3 -R "index.html*" -e robots=off -P $S/tracks https://dl.ash2txt.org/datasets/spiral_datasets/PHerc0813/20250821151723/tracks/; echo "wget rc=$?"
du -sh $S/* 2>/dev/null; echo "[$(date -Is)] done; free: $(df -h /mnt/nvme | tail -1)"
echo "MIRROR0813-EXIT: 0"
