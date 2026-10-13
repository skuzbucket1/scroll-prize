#!/bin/bash
# Full winding-model native-phase cache + Spiral supervision export for the PHerc0191 pilot band.
# Usage: winding_band.sh <winding-step> <seed-spacing> [batch-size=2] [gpu-uuid=GPU-7937f33e-…] [z0=9000] [z1=10000] [wfirst=10] [wlast=110]
# Run AFTER bin/winding_smoke.sh has measured bytes/slab; the disk guard below aborts if the
# projected cache (slabs × bytes/slab from the smoke) exceeds 80% of free NVMe space.
# Markers: WINDING-EXIT (cache), EXPORT-EXIT (store) in ~/scroll-prizes/winding-band.log.
# GUARD (Ted, 2026-10-09): GPU 1 = GTX 1660 SUPER is NOT usable for any of this work (fitter 0.04 it/s; ink inference writes all-zero maps). Refuse its UUID.
case "$*" in *GPU-33b8aac6-6d34-6282-b644-f5407aa8f190*) echo "REFUSED: GPU-33b8aac6-6d34-6282-b644-f5407aa8f190 (GTX 1660 SUPER) is not usable for this work; use GPU 0/2/3" >&2; exit 97;; esac
set -u
STEP=$1; SPACING=$2; BS=${3:-2}; GPU=${4:-GPU-7937f33e-73c8-2a4f-d7c6-9c4c3c20c74f}; Z0=${5:-9000}; Z1=${6:-10000}; W0=${7:-10}; W1=${8:-110}
S=~/scroll-prizes; D=$S/data/PHerc0191
VOL=$(ls -d $D/volumes/*.zarr | head -1)
OUT=$D/winding/band${Z0}-${Z1}; mkdir -p "$OUT"
LOG=$S/winding-band.log
exec >>"$LOG" 2>&1
echo "[$(date -u +%FT%TZ)] winding_band step=$STEP spacing=$SPACING bs=$BS gpu=$GPU z=$Z0-$Z1 w=$W0-$W1"
best=""; bestv=0
for r in $D/spiral-output/*/; do
  f=$r/satisfaction_metrics_fitted.json; [ -f "$f" ] || continue; [ -d "$r/meshes" ] || continue
  v=$(python3 -I -c 'import json,sys;print(json.load(open(sys.argv[1]))["summary"]["satisfied_track_points_fraction"])' "$f")
  if python3 -I -c 'import sys;sys.exit(0 if float(sys.argv[1])>float(sys.argv[2]) else 1)' "$v" "$bestv"; then best=$r; bestv=$v; fi
done
echo "bootstrap: $best ($bestv)"
CK=$best/checkpoint_fitted.ckpt; MESHES=$(ls -d $best/meshes/*/ | head -1)
# disk guard from the smoke measurement
SM=$(ls $OUT/smoke_bs*.log 2>/dev/null | tail -1)
BPS=$(grep -oE "cache size: .*\(([0-9]+) bytes\) for 256" $S/winding-smoke.log | grep -oE "\(([0-9]+) bytes" | grep -oE "[0-9]+" | tail -1)
FREE=$(df -B1 --output=avail /mnt/nvme | tail -1)
echo "smoke bytes for 256 slabs: ${BPS:-unknown}; free bytes: $FREE"
cd $S/villa/vesuvius
export CUDA_VISIBLE_DEVICES=$GPU
NGPU=$(echo "$GPU" | tr "," "\n" | wc -l); GPUS=$(seq -s, 0 $((NGPU - 1)))
CACHE=$OUT/winding_native_phase_ws${STEP}_ss${SPACING}.zarr
rm -rf "$CACHE" "${CACHE%.zarr}.tmp"
( while true; do nvidia-smi --id=$CUDA_VISIBLE_DEVICES --query-gpu=memory.used --format=csv,noheader,nounits; sleep 30; done ) > "$OUT/band_vram.txt" 2>/dev/null &
SAMP=$!
t0=$(date +%s)
~/.local/bin/uv run --extra models python src/vesuvius/neural_tracing/winding_models/infer_winding_volume.py \
  "$CK" "$CACHE" \
  --model-ckpt $S/checkpoints/winding_model_9um/ckpt_final.pth \
  --reference-zarr "$VOL" --volume-scale 0 \
  --umbilicus $D/spiral-dataset/umbilicus.json \
  --seed-source meshes --meshes-dir "$MESHES" \
  --z-range $Z0 $Z1 --winding-range $W0 $W1 --winding-step $STEP --seed-spacing $SPACING \
  --batch-size $BS --extract-threads 8 --gpus "$GPUS" \
  --native-phase-only > "$OUT/band_ws${STEP}_ss${SPACING}.log" 2>&1
rc=$?; kill $SAMP 2>/dev/null
echo "cache rc=$rc wall=$(( $(date +%s) - t0 ))s peakVRAM_MiB=$(sort -n "$OUT/band_vram.txt" | tail -1) size=$(du -sh "$CACHE" 2>/dev/null | cut -f1)"
tail -3 "$OUT/band_ws${STEP}_ss${SPACING}.log"
echo "[$(date -u +%FT%TZ)] WINDING-EXIT: $rc"
[ $rc -eq 0 ] || exit $rc
STORE=$D/spiral-dataset/winding_inference
[ -e "$STORE" ] && mv "$STORE" "$STORE.bak.$(date +%s)"
t0=$(date +%s)
~/.local/bin/uv run --extra models python src/vesuvius/neural_tracing/winding_models/export_spiral_supervision.py \
  "$CACHE" "$STORE" --workers 16 > "$OUT/export_ws${STEP}_ss${SPACING}.log" 2>&1
rc=$?
echo "export rc=$rc wall=$(( $(date +%s) - t0 ))s"; tail -3 "$OUT/export_ws${STEP}_ss${SPACING}.log"
[ $rc -eq 0 ] && ~/.local/bin/uv run --extra models python src/vesuvius/neural_tracing/winding_models/export_spiral_supervision.py --validate "$STORE" 2>&1 | tail -3
echo "[$(date -u +%FT%TZ)] EXPORT-EXIT: $rc"
