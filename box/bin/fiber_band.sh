#!/usr/bin/env bash
# Fiber-direction inference (SD2 model, README 9 um transfer recipe) on PHerc0191 z-band 8500-10500 at level 0, local mirror.
set -uo pipefail
D=/mnt/nvme/scroll-prizes/data/PHerc0191; V=$D/volumes/20250821151635-9.362um-1.2m-113keV-masked.zarr; OUT=$D/fiber/band8500-10500; mkdir -p "$OUT"
until grep -q 'HFSD2-EXIT: 0' ~/scroll-prizes/hf-fiber-sd2.log 2>/dev/null; do sleep 60; done
until grep -q 'MIRROR-EXIT' $D/mirror-volume.log 2>/dev/null; do sleep 120; done
until grep -q 'FIT-EXIT' ~/scroll-prizes/fit-exp-30k.log 2>/dev/null && grep -q 'FIT-EXIT' ~/scroll-prizes/fit-exp-track2x.log 2>/dev/null; do sleep 120; done
CK=~/scroll-prizes/checkpoints/lasagna-fiber/s1a_128_2_single_8x8_20260728_094259_best_25_9k.pt
cd ~/scroll-prizes/villa/vesuvius; export PYTHONPATH=/mnt/nvme/scroll-prizes/villa; export CUDA_VISIBLE_DEVICES=GPU-2d9651e9-5a94-e0cb-6a99-9300d8056524
echo "[$(date -Is)] start fiber inference (level 0, crop z 8500-10500, 256^3 tiles)"; t0=$(date +%s)
~/.local/bin/uv run --extra models python -m vesuvius.neural_tracing.fiber_trace_3d.infer --input "$V/0" --output "$OUT/fiber.lasagna.json" --checkpoint "$CK" --devices all --no-download --crop 0 0 8500 8387 8387 2000 --tile-size 256 --overlap 48 --border 16 --inference-scaledown-power 2 > "$OUT/infer.log" 2>&1; rc=$?
echo "[$(date -Is)] done rc=$rc in $(( $(date +%s)-t0 ))s"; tail -5 "$OUT/infer.log" | cut -c1-160; ls "$OUT"; [ -f "$OUT/fiber.lasagna.json" ] && head -c 600 "$OUT/fiber.lasagna.json"; echo; echo "FIBER-EXIT: $rc"
