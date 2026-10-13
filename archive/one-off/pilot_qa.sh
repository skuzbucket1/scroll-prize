#!/usr/bin/env bash
# Pilot QA: render + ink three fitted windings (w040/w070/w100) from the PHerc0191 pilot spiral fit.
set -uo pipefail
export PATH=$HOME/.local/bin:$PATH
D=/mnt/nvme/scroll-prizes/data/PHerc0191; VOL=$D/volumes/20250821151635-9.362um-1.2m-113keV-masked.zarr
URL=https://vesuvius-challenge-open-data.s3.amazonaws.com/PHerc0191/volumes/20250821151635-9.362um-1.2m-113keV-masked.zarr
RUN=$(ls -td $D/spiral-output/*/ | head -1); MESHES=$(ls -d $RUN/meshes/fitted_*/ | head -1); OUT=$D/pilot-qa; mkdir -p "$OUT"; cd ~/scroll-prizes/villa/vesuvius
have=1; for zc in $(seq 70 78); do [ "$(ls $VOL/0/$zc 2>/dev/null | wc -l)" -gt 50 ] || have=0; done
if [ $have = 1 ]; then VARGS=(-v "$VOL"); echo "volume: local level-0 chunks"; else VARGS=(-v "$OUT/volume_cache" --remote-url "$URL" --prefetch-remote); echo "volume: band not mirrored yet -> remote streaming"; fi
export CUDA_VISIBLE_DEVICES=GPU-2d9651e9-5a94-e0cb-6a99-9300d8056524
for w in w040 w070 w100; do
  M=$(ls -d $MESHES/${w}_* 2>/dev/null | head -1); [ -n "$M" ] || { echo "no mesh $w"; continue; }
  echo "[$(date -Is)] render $w  area_cm2=$(python3 -c "import json;print(round(json.load(open('$M/meta.json')).get('area_cm2',0),2))")"; t0=$(date +%s)
  vc_render_tifxyz "${VARGS[@]}" -s "$M" --scale 1 -g 0 --num-slices 28 --slice-step 1 --flip-normals --surface-interpolation smooth --voxel-size 9.362 --voxel-unit micrometer --cache-gb 12 --zarr-output "$OUT/$w.zarr" --log-path "$OUT/$w.render.log" || { echo "RENDER FAILED $w: $(tail -2 $OUT/$w.render.log | tr '\n' ' ')"; continue; }
  echo "  rendered in $(( $(date +%s)-t0 ))s"; ~/.local/bin/uv run --extra models python ~/scroll-prizes/bin/zarr_slice_preview.py "$OUT/$w.zarr" "$OUT/${w}_render_z14_ds2.tif" 0 14 2
  for ck in hybrid_3d2d-seed42/step-075000 hybrid_3d2d-seed43/step-075000; do tag=$(echo $ck | sed 's|hybrid_3d2d-||; s|/step-0*|-|')
    ~/.local/bin/uv run --extra models python -m vesuvius.ink_detection.inference.infer "$OUT/$w.zarr" ~/scroll-prizes/checkpoints/ink_9um/$ck.pth "$OUT/${w}_${tag}.tif" --resolution 0 --overlap 0.5 --blend-mode hann --batch-size 4 --direction both --no-compile --num-workers 3 >/dev/null 2>"$OUT/${w}_${tag}.err" || echo "INFER FAILED $w $tag: $(tail -1 $OUT/${w}_${tag}.err)"
  done
  for t in "$OUT"/${w}_s4*.tif; do case "$t" in *_preview*) continue;; esac; ~/.local/bin/uv run --extra models python ~/scroll-prizes/bin/tif_preview.py "$t" "${t%.tif}_preview-ds2.tif" 2 --rescale9um >/dev/null; done
  echo "  $w done"
done
echo "[$(date -Is)] all done"; ls "$OUT" | grep -c . | xargs echo "files:"; echo "PILOTQA-EXIT: 0"
