#!/usr/bin/env bash
# Render + ink the 31 cm2 patch grown by vc_grow_seg_from_seed (PHerc0191, seed 5326 2948 9500, 150 generations).
set -uo pipefail; export PATH=$HOME/.local/bin:$PATH
D=/mnt/nvme/scroll-prizes/data/PHerc0191; G=$D/grow-test; M=$(ls -d $G/out/auto_grown_* | tail -1); OUT=$G/qa; mkdir -p "$OUT"
URL=https://vesuvius-challenge-open-data.s3.amazonaws.com/PHerc0191/volumes/20250821151635-9.362um-1.2m-113keV-masked.zarr
cd ~/scroll-prizes/villa/vesuvius; export CUDA_VISIBLE_DEVICES=GPU-7937f33e-73c8-2a4f-d7c6-9c4c3c20c74f
echo "[$(date -Is)] render patch $(basename $M) ($(python3 -c "import json;print(round(json.load(open('$M/meta.json'))['area_cm2'],1))") cm2)"; t0=$(date +%s)
vc_render_tifxyz -v "$OUT/volume_cache" --remote-url "$URL" --prefetch-remote -s "$M" --scale 1 -g 0 --num-slices 28 --slice-step 1 --flip-normals --surface-interpolation smooth --voxel-size 9.362 --voxel-unit micrometer --cache-gb 12 --zarr-output "$OUT/patch.zarr" --log-path "$OUT/patch.render.log" || { echo "RENDER FAILED: $(tail -2 $OUT/patch.render.log | tr '\n' ' ')"; echo "GROWQA-EXIT: 1"; exit 1; }
echo "  rendered in $(( $(date +%s)-t0 ))s"; ~/.local/bin/uv run --extra models python ~/scroll-prizes/bin/zarr_slice_preview.py "$OUT/patch.zarr" "$OUT/patch_render_z14_ds4.tif" 0 14 4
for ck in hybrid_3d2d-seed42/step-075000 hybrid_3d2d-seed43/step-075000; do tag=${ck#hybrid_3d2d-}; tag=${tag/\/step-0/-}
  ~/.local/bin/uv run --extra models python -m vesuvius.ink_detection.inference.infer "$OUT/patch.zarr" ~/scroll-prizes/checkpoints/ink_9um/$ck.pth "$OUT/patch_${tag}.tif" --resolution 0 --overlap 0.5 --blend-mode hann --batch-size 4 --direction both --no-compile --num-workers 3 2>"$OUT/patch_${tag}.err" >/dev/null || echo "INFER FAILED $tag: $(tail -1 $OUT/patch_${tag}.err)"
done
for t in "$OUT"/patch_seed*.tif; do case "$t" in *_preview*) continue;; esac; ~/.local/bin/uv run --extra models python ~/scroll-prizes/bin/tif_preview.py "$t" "${t%.tif}_preview-ds4.tif" 4 --rescale9um >/dev/null; done
echo "[$(date -Is)] done"; ls "$OUT"; echo "GROWQA-EXIT: 0"
