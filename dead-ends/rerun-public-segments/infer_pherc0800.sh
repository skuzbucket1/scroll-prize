#!/usr/bin/env bash
# PHerc0800 (First Letters eligible; not in ink_9um training data): ink inference on the 6 public auto_grown segments'
# pre-rendered 8.64 um surface volumes (31 layers), read from local copies (https reads aborted on a transient ServerDisconnectedError). Three checkpoints x both depth directions.
set -uo pipefail
cd ~/scroll-prizes
until grep -q "DL0800-EXIT:" dl-pherc0800.log 2>/dev/null; do sleep 15; done
grep -q "DL0800-EXIT: 0" dl-pherc0800.log || { echo "download failed"; echo "P0800-EXIT: 91"; exit 1; }

export CUDA_VISIBLE_DEVICES=GPU-7937f33e-73c8-2a4f-d7c6-9c4c3c20c74f   # RTX 3060 12 GB at PCI 07:00.0 (the other 3060 runs the sample smoke test)
S3=https://vesuvius-challenge-open-data.s3.amazonaws.com
SV=8.64um-1.2m-116keV-volume-20250521135224.zarr
RUN=$HOME/scroll-prizes/runs/PHerc0800-ink9um; mkdir -p "$RUN"
cd ~/scroll-prizes/villa/vesuvius
fail=0
for seg in 20251028222030-auto_grown_20251028222030940 20251028225813-auto_grown_20251028225813045 20251028213516-auto_grown_20251028213516907 20251028220042-auto_grown_20251028220042762 20251028220955-auto_grown_20251028220955262 20251029010146-auto_grown_20251029010146642; do
  short=${seg%%-*}
  for ck in hybrid_3d2d-seed42/step-075000 hybrid_3d2d-seed43/step-075000 hybrid_3d2d-seed42/step-040000; do
    [ -f "$HOME/scroll-prizes/checkpoints/ink_9um/$ck.pth" ] || { echo "missing checkpoint $ck"; continue; }
    tag=$(echo "$ck" | sed 's|hybrid_3d2d-||; s|/step-0*|-|'); out="$RUN/${short}_${tag}.tif"
    [ -s "$out" ] && continue
    echo "[$(date -Is)] $short $tag"
    ~/.local/bin/uv run --extra models python -m vesuvius.ink_detection.inference.infer "$HOME/scroll-prizes/data/PHerc0800/segments/$seg/surface-volumes/$SV" "$HOME/scroll-prizes/checkpoints/ink_9um/$ck.pth" "$out" --resolution 0 --overlap 0.5 --blend-mode hann --batch-size 4 --direction both --no-compile --num-workers 2 || { echo "  FAILED $short $tag"; fail=$((fail+1)); }
  done
done
echo "[$(date -Is)] previews (ds2, rescaled (p-0.25)/0.5)"
for t in "$RUN"/*.tif; do case "$t" in *_preview*) continue;; esac; ~/.local/bin/uv run --extra models python ~/scroll-prizes/bin/tif_preview.py "$t" "${t%.tif}_preview-ds2.tif" 2 --rescale9um; done
ls "$RUN" | wc -l; echo "P0800-EXIT: $fail"
