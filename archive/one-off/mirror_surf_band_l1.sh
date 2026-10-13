#!/bin/bash
B=https://vesuvius-challenge-open-data.s3.amazonaws.com
P="PHerc0191/representations/predictions/surfaces/20250821151635-surface-20260413222639-surface-m7-L0-th0.2.zarr"
D=/mnt/nvme/scroll-prizes/data/PHerc0191/surf-m7/20250821151635-surface-20260413222639-surface-m7-L0-th0.2.zarr
mkdir -p "$D/1"; curl -s "$B/$P/1/.zarray" -o "$D/1/.zarray"
for z in 22 23 24 25 26 27; do echo "[$(date -u +%FT%TZ)] L1 z row $z"; python3 -I /home/tbienapfl/scroll-prizes/bin/mirror_s3_v2.py "$B" "$P/1/$z/" "$D/1/$z" 16 2>&1 | tail -1; done
echo "SURFMIRRORL1-EXIT: 0"
