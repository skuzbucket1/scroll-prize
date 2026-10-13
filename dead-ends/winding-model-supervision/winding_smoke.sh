#!/bin/bash
# Winding-model native-phase SMOKE run on the PHerc0191 pilot band (z 9000-10000).
# Gates: (1) level-0 CT chunks for the band are mirrored — the mirror writes in S3 listing
# (lexicographic) order, so a non-empty chunk dir "85" means dirs <= 83 (z < 10752) are complete;
# (2) both fit experiments finished (frees GPU-7937f33e). Picks the bootstrap fit with the best
# satisfied_track_points_fraction. Measures bytes/slab, slabs/s and peak VRAM so the full band
# run can be sized against disk (recipe: ~25 MB/slab uncompressed with the HF model).
set -u
S=~/scroll-prizes; D=$S/data/PHerc0191
VOL=$(ls -d $D/volumes/*.zarr | head -1)
OUT=$D/winding/band9000-10000; mkdir -p "$OUT"
LOG=$S/winding-smoke.log
exec >>"$LOG" 2>&1
echo "[$(date -u +%FT%TZ)] waiting: level-0 chunk dir 85 non-empty, FIT-EXIT in exp-30k and exp-track2x"
until [ -d "$VOL/0/85" ] && [ "$(ls "$VOL/0/85" | wc -l)" -gt 0 ]; do sleep 120; done
until grep -q FIT-EXIT $S/fit-exp-30k.log 2>/dev/null && grep -q FIT-EXIT $S/fit-exp-track2x.log 2>/dev/null; do sleep 120; done
echo "[$(date -u +%FT%TZ)] gates open"
best=""; bestv=0
for r in $D/spiral-output/*/; do
  f=$r/satisfaction_metrics_fitted.json; [ -f "$f" ] || continue
  v=$(python3 -I -c 'import json,sys;print(json.load(open(sys.argv[1]))["summary"]["satisfied_track_points_fraction"])' "$f")
  echo "candidate $r satisfied_track_points_fraction=$v"
  if python3 -I -c 'import sys;sys.exit(0 if float(sys.argv[1])>float(sys.argv[2]) else 1)' "$v" "$bestv"; then best=$r; bestv=$v; fi
done
echo "bootstrap: $best ($bestv)"
CK=$best/checkpoint_fitted.ckpt
MESHES=$(ls -d $best/meshes/*/ | head -1)
echo "meshes: $MESHES ($(ls "$MESHES" | grep -c spliced) spliced)"
cd $S/villa/vesuvius
export CUDA_VISIBLE_DEVICES=GPU-7937f33e-73c8-2a4f-d7c6-9c4c3c20c74f
rc=1
for bs in 2 1; do
  rm -rf "$OUT/smoke.zarr" "$OUT/smoke.tmp"
  ( while true; do nvidia-smi --id=$CUDA_VISIBLE_DEVICES --query-gpu=memory.used --format=csv,noheader,nounits; sleep 5; done ) > "$OUT/smoke_bs${bs}_vram.txt" 2>/dev/null &
  SAMP=$!
  t0=$(date +%s)
  ~/.local/bin/uv run --extra models python src/vesuvius/neural_tracing/winding_models/infer_winding_volume.py \
    "$CK" "$OUT/smoke.zarr" \
    --model-ckpt $S/checkpoints/winding_model_9um/ckpt_final.pth \
    --reference-zarr "$VOL" --volume-scale 0 \
    --umbilicus $D/spiral-dataset/umbilicus.json \
    --seed-source meshes --meshes-dir "$MESHES" \
    --z-range 9000 10000 --winding-range 10 110 --winding-step 3 --seed-spacing 60 \
    --batch-size $bs --extract-threads 8 --gpus 0 \
    --max-slabs 256 --max-slabs-selection first --native-phase-only > "$OUT/smoke_bs${bs}.log" 2>&1
  rc=$?; kill $SAMP 2>/dev/null
  echo "smoke bs=$bs rc=$rc wall=$(( $(date +%s) - t0 ))s peakVRAM_MiB=$(sort -n "$OUT/smoke_bs${bs}_vram.txt" | tail -1)"
  tail -5 "$OUT/smoke_bs${bs}.log"
  [ $rc -eq 0 ] && break
done
if [ $rc -eq 0 ]; then
  echo "cache size: $(du -sh "$OUT/smoke.zarr" | cut -f1) ($(du -sb "$OUT/smoke.zarr" | cut -f1) bytes) for 256 slabs"
  grep -iE "seed|slab|wrote|slabs/s" "$OUT/smoke_bs${bs}.log" | tail -12
fi
echo "[$(date -u +%FT%TZ)] SMOKE-EXIT: $rc"
