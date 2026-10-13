#!/bin/bash
# Third snap attempt for PHerc0813 z8000 (two were killed for memory, 2026-10-12): after the triage re-run (3 workers) has
# finished, 2 workers, unspliced windings only (the spliced ones are not flattened). Stops at SNAP-GATE.
R=~/scroll-prizes/runs/2026-10-12_tallband-0813-z8000; B=~/scroll-prizes/bin
until grep -q TRIAGE2-EXIT ~/scroll-prizes/runs/2026-10-12_triage-eval/run2.log 2>/dev/null; do sleep 60; done
echo "[$(date -Is)] snap: 2 workers, unspliced only; $(free -g | awk '/Mem/ {print $7}') GB available"
SNAP_PROCS=2 SNAP_SKIP_SPLICED=1 nice -n 5 bash $B/snap_band.sh PHerc0813 exp30k-z8000 8000 10500 > $R/snap3.log 2>&1
tail -4 $R/snap3.log
echo "[$(date -Is)] SNAP-GATE: check snap3.log + snapped/snap_report.tsv before flatten, render and ink"
