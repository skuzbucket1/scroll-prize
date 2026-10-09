#!/usr/bin/env bash
# First ink-inference smoke test: pre-rendered 7.91 um surface volume of PHercParis4 segment 20231016151002 + ink_9um checkpoint.
set -uo pipefail
cd ~/scroll-prizes
until grep -q 'UV-SYNC-EXIT:' uv-sync-vesuvius.log 2>/dev/null; do sleep 20; done
until grep -q 'DL-EXIT:' dl-surfvol-7.91um.log 2>/dev/null; do sleep 20; done
grep -q 'UV-SYNC-EXIT: 0' uv-sync-vesuvius.log || { echo "uv sync failed"; echo "INFER-EXIT: 90"; exit 1; }
grep -q 'DL-EXIT: 0' dl-surfvol-7.91um.log || { echo "download failed"; echo "INFER-EXIT: 91"; exit 1; }
RUN=$HOME/scroll-prizes/runs/20231016151002-7.91um-ink9um-s42-075k; mkdir -p "$RUN"
IN=$HOME/scroll-prizes/data/PHercParis4/segments/20231016151002/surface-volumes/7.91um-54keV-volume-20230205180739.zarr
CK=$HOME/scroll-prizes/checkpoints/ink_9um/hybrid_3d2d-seed42/step-075000.pth
export CUDA_VISIBLE_DEVICES=GPU-2d9651e9-5a94-e0cb-6a99-9300d8056524   # RTX 3060 12 GB at PCI 01:00.0
cd ~/scroll-prizes/villa/vesuvius
echo "[$(date -Is)] start"; nvidia-smi --query-gpu=index,name,memory.used --format=csv,noheader
run() { ~/.local/bin/uv run --extra models python -m vesuvius.ink_detection.inference.infer "$IN" "$CK" "$RUN/pred.tif" --resolution 0 --overlap 0.5 --blend-mode hann --batch-size 4 --direction both "$@"; }
if ! run; then echo "[$(date -Is)] first attempt failed; retry with --no-compile --batch-size 2"; run --no-compile --batch-size 2; fi
rc=$?; echo "[$(date -Is)] done rc=$rc"; ls -la "$RUN"; echo "INFER-EXIT: $rc"
