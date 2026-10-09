#!/bin/bash
# Export the compact Spiral supervision from the completed winding cache; append markers to winding-band.log so queue_wm.sh fires.
S=/home/tbienapfl/scroll-prizes; D=/mnt/nvme/scroll-prizes/data/PHerc0191; CACHE=/mnt/nvme/scroll-prizes/data/PHerc0191/winding/band9000-10000/winding_native_phase_ws8_ss96.zarr; STORE=/mnt/nvme/scroll-prizes/data/PHerc0191/spiral-dataset/winding_inference
exec >> $S/winding-band.log 2>&1
cd $S/villa/vesuvius
[ -e "$STORE" ] && mv "$STORE" "$STORE.bak.$(date +%s)"
t0=$(date +%s)
~/.local/bin/uv run --extra models python src/vesuvius/neural_tracing/winding_models/export_spiral_supervision.py "$CACHE" "$STORE" --workers 4 > $D/winding/band9000-10000/export_ws8_ss96.log 2>&1
rc=$?
echo "export rc=$rc wall=$(( $(date +%s)-t0 ))s"; tail -3 $D/winding/band9000-10000/export_ws8_ss96.log | cut -c1-200
if [ $rc -eq 0 ]; then ~/.local/bin/uv run --extra models python src/vesuvius/neural_tracing/winding_models/export_spiral_supervision.py --validate "$STORE" 2>&1 | tail -2 | cut -c1-200; fi
echo "[$(date -u +%FT%TZ)] EXPORT-EXIT: $rc"
