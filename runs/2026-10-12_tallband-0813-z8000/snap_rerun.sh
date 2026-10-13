#!/bin/bash
# Re-run the PHerc0813 z8000 snap (the first one was killed for memory at 17:47 UTC: 3 workers next to a 16 GB render cache).
# Waits until the control renders are done (their render66 holds 16 GB), then 2 workers. Stops at SNAP-GATE for a check
# before flatten / render / ink. Marker SNAP-GATE (snap_rerun.log).
R=~/scroll-prizes/runs/2026-10-12_tallband-0813-z8000; B=~/scroll-prizes/bin
until grep -q CONTROLS-RENDER-EXIT ~/scroll-prizes/runs/2026-10-12_controls-render/run.log 2>/dev/null; do sleep 60; done
echo "[$(date -Is)] snap with 2 workers; free: $(free -g | awk '/Mem/ {print $7}') GB available"
SNAP_PROCS=2 nice -n 5 bash $B/snap_band.sh PHerc0813 exp30k-z8000 8000 10500 > $R/snap2.log 2>&1
tail -4 $R/snap2.log
echo "[$(date -Is)] SNAP-GATE: check snap2.log + snapped/snap_report.tsv before flatten, render and ink"
