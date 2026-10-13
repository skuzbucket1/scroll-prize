#!/bin/bash
# Mirror the m7 surface prediction (level 0) for band z chunk rows 57..65 (z 10944-12672).
B=https://vesuvius-challenge-open-data.s3.amazonaws.com
P="PHerc0191/representations/predictions/surfaces/20250821151635-surface-20260413222639-surface-m7-L0-th0.2.zarr"
D=/mnt/nvme/scroll-prizes/data/PHerc0191/surf-m7/20250821151635-surface-20260413222639-surface-m7-L0-th0.2.zarr
mkdir -p "$D/0"
for f in .zattrs .zgroup 0/.zarray 1/.zarray; do mkdir -p "$D/$(dirname $f)"; curl -s "$B/$P/$f" -o "$D/$f"; done
for z in 57 58 59 60 61 62 63 64 65; do
  echo "[$(date -u +%FT%TZ)] z chunk row $z"
  python3 -I /home/tbienapfl/scroll-prizes/bin/mirror_s3_v2.py "$B" "$P/0/$z/" "$D/0/$z" 24 2>&1 | tail -2
done
du -sh "$D"; echo "SURFMIRROR-EXIT: 0"
