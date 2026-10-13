#!/usr/bin/env bash
# Render + ink selected fitted windings from a spiral-fit run. Usage: winding_qa.sh <run dir> <out dir> <CUDA GPU UUID> [w040 w070 ...]
# GUARD (Ted, 2026-10-09): GPU 1 = GTX 1660 SUPER is NOT usable for any of this work (fitter 0.04 it/s; ink inference writes all-zero maps). Refuse its UUID.
case "$*" in *GPU-33b8aac6-6d34-6282-b644-f5407aa8f190*) echo "REFUSED: GPU-33b8aac6-6d34-6282-b644-f5407aa8f190 (GTX 1660 SUPER) is not usable for this work; use GPU 0/2/3" >&2; exit 97;; esac
set -uo pipefail; export PATH=$HOME/.local/bin:$PATH
RUN=$1; OUT=$2; export CUDA_VISIBLE_DEVICES=$3; shift 3; WINDINGS=${*:-"w040 w070 w100"}; mkdir -p "$OUT"
D=/mnt/nvme/scroll-prizes/data/PHerc0191; VOL=$D/volumes/20250821151635-9.362um-1.2m-113keV-masked.zarr
URL=https://vesuvius-challenge-open-data.s3.amazonaws.com/PHerc0191/volumes/20250821151635-9.362um-1.2m-113keV-masked.zarr
MESHES=$(ls -d $RUN/meshes/fitted_*/ | head -1); cd ~/scroll-prizes/villa/vesuvius
for w in $WINDINGS; do
  M=$(ls -d $MESHES/${w}_* 2>/dev/null | head -1); [ -n "$M" ] || { echo "no mesh $w"; continue; }
  echo "[$(date -Is)] $w area_cm2=$(python3 -c "import json;print(round(json.load(open('$M/meta.json')).get('area_cm2',0),2))")"; t0=$(date +%s)
  if ls $VOL/0/7[0-8] >/dev/null 2>&1 && [ "$(ls $VOL/0/74 2>/dev/null | wc -l)" -gt 50 ]; then VARGS=(-v "$VOL"); else VARGS=(-v "$OUT/volume_cache" --remote-url "$URL" --prefetch-remote); fi
  vc_render_tifxyz "${VARGS[@]}" -s "$M" --scale 1 -g 0 --num-slices 28 --slice-step 1 --flip-normals --surface-interpolation smooth --voxel-size 9.362 --voxel-unit micrometer --cache-gb 12 --zarr-output "$OUT/$w.zarr" --log-path "$OUT/$w.render.log" || { echo "RENDER FAILED $w"; continue; }
  echo "  rendered in $(( $(date +%s)-t0 ))s"; ~/.local/bin/uv run --extra models python ~/scroll-prizes/bin/zarr_slice_preview.py "$OUT/$w.zarr" "$OUT/${w}_render_z14_ds2.tif" 0 14 2 | cut -c1-120
  for ck in hybrid_3d2d-seed42/step-075000 hybrid_3d2d-seed43/step-075000; do tag=${ck#hybrid_3d2d-}; tag=${tag/\/step-0/-}
    ~/.local/bin/uv run --extra models python -m vesuvius.ink_detection.inference.infer "$OUT/$w.zarr" ~/scroll-prizes/checkpoints/ink_9um/$ck.pth "$OUT/${w}_ink_${tag}.tif" --resolution 0 --overlap 0.5 --blend-mode hann --batch-size 4 --direction both --no-compile --num-workers 3 2>"$OUT/${w}_ink_${tag}.err" >/dev/null || echo "INFER FAILED $w $tag"
  done
  for t in "$OUT"/${w}_ink_*.tif; do case "$t" in *_preview*) continue;; esac; ~/.local/bin/uv run --extra models python ~/scroll-prizes/bin/tif_preview.py "$t" "${t%.tif}_preview-ds2.tif" 2 --rescale9um | cut -c1-120; done
done
echo "[$(date -Is)] done"; echo "WINDINGQA-EXIT: 0"
