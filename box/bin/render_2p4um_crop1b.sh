#!/usr/bin/env bash
# Crop render of PHercParis4 segment 20231016151002 from the remote 2.4 um volume at level 2 (9.6 um/px), 28 slices.
# Crop = upper part of the main text block (~6.2 cm x 2.0 cm) — input for the 9 um ink models.
set -uo pipefail
cd ~/scroll-prizes
until grep -q "DL0800-EXIT:" dl-pherc0800.log 2>/dev/null; do sleep 15; done


RUN=$HOME/scroll-prizes/runs/20231016151002-2.4um-g2-28-crop1b; mkdir -p "$RUN"
URL=https://vesuvius-challenge-open-data.s3.amazonaws.com/PHercParis4/volumes/20260411134726-2.400um-0.2m-78keV-masked.zarr
SEG=$HOME/scroll-prizes/data/PHercParis4/segments/20231016151002/mesh/20231016151002-on-20260411134726-2.4um.tifxyz
export PATH=$HOME/.local/bin:$PATH LD_LIBRARY_PATH=$HOME/.local/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}
echo "[$(date -Is)] start render"; t0=$(date +%s)
vc_render_tifxyz -v "$RUN/volume_cache" --remote-url "$URL" -s "$SEG" --scale 1 -g 2 --num-slices 28 --slice-step 1 \
  --crop-x 4000 --crop-y 900 --crop-width 6500 --crop-height 2100 \
  --voxel-size 2.4 --voxel-unit micrometer --cache-gb 12 --prefetch-remote \
  --zarr-output "$RUN/render.zarr" --log-path "$RUN/vc_render.log"
rc=$?; echo "[$(date -Is)] done rc=$rc in $(( $(date +%s)-t0 ))s"
du -sh "$RUN/render.zarr" ~/.VC3D/remote_cache 2>/dev/null; tail -5 "$RUN/vc_render.log" 2>/dev/null; df -h / | tail -1; echo "RENDER-EXIT: $rc"
