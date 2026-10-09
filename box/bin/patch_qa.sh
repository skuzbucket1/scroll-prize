#!/usr/bin/env bash
# Patch QA: geometry stats (PCA aspect, self-cross), remote render (28 slices), ink_9um (2 seeds x both directions), previews.
# Usage: patch_qa.sh <tifxyz mesh dir> <out dir> <CUDA GPU UUID>   -> marker PATCHQA-EXIT in stdout
# GUARD (Ted, 2026-10-09): GPU 1 = GTX 1660 SUPER is NOT usable for any of this work (fitter 0.04 it/s; ink inference writes all-zero maps). Refuse its UUID.
case "$*" in *GPU-33b8aac6-6d34-6282-b644-f5407aa8f190*) echo "REFUSED: GPU-33b8aac6-6d34-6282-b644-f5407aa8f190 (GTX 1660 SUPER) is not usable for this work; use GPU 0/2/3" >&2; exit 97;; esac
set -uo pipefail; export PATH=$HOME/.local/bin:$PATH
M=$1; OUT=$2; export CUDA_VISIBLE_DEVICES=$3; mkdir -p "$OUT"
URL=https://vesuvius-challenge-open-data.s3.amazonaws.com/PHerc0191/volumes/20250821151635-9.362um-1.2m-113keV-masked.zarr
cd ~/scroll-prizes/villa/vesuvius
echo "[$(date -Is)] mesh $M area_cm2=$(python3 -c "import json;print(round(json.load(open('$M/meta.json')).get('area_cm2',0),2))")"
~/.local/bin/uv run --extra models python - "$M" <<'PY'
import sys, numpy as np, tifffile
m=sys.argv[1]; x=tifffile.imread(f"{m}/x.tif"); y=tifffile.imread(f"{m}/y.tif"); z=tifffile.imread(f"{m}/z.tif"); ok=z>0
P=np.stack([x[ok],y[ok],z[ok]],1).astype(np.float64); P-=P.mean(0); Q=P[::max(1,len(P)//20000)]; s=np.linalg.svd(Q,compute_uv=False); e=2*s/np.sqrt(len(Q))
print(f"  geometry: {ok.sum():,} pts; extents {e[0]:.0f} x {e[1]:.0f} x {e[2]:.0f} vx; thickness/extent {e[2]/e[0]:.3f} -> {'sheet-like' if e[2]/e[0]<0.1 else 'NOT sheet-like'}")
PY
vc_tifxyz_selfcross --surface "$M" -o "$OUT/selfcross.json" >/dev/null 2>&1 && echo "  selfcross clean: $(python3 -c "import json;print(json.load(open('$OUT/selfcross.json')).get('clean_of_transverse_self_intersection'))")"
t0=$(date +%s); vc_render_tifxyz -v "$OUT/volume_cache" --remote-url "$URL" --prefetch-remote -s "$M" --scale 1 -g 0 --num-slices 28 --slice-step 1 --flip-normals --surface-interpolation smooth --voxel-size 9.362 --voxel-unit micrometer --cache-gb 12 --zarr-output "$OUT/render.zarr" --log-path "$OUT/render.log" || { echo "RENDER FAILED: $(tail -2 $OUT/render.log | tr '\n' ' ')"; echo "PATCHQA-EXIT: 1"; exit 1; }
echo "  rendered in $(( $(date +%s)-t0 ))s"; ~/.local/bin/uv run --extra models python ~/scroll-prizes/bin/zarr_slice_preview.py "$OUT/render.zarr" "$OUT/render_z14_ds2.tif" 0 14 2 | cut -c1-160
for ck in hybrid_3d2d-seed42/step-075000 hybrid_3d2d-seed43/step-075000; do tag=${ck#hybrid_3d2d-}; tag=${tag/\/step-0/-}
  ~/.local/bin/uv run --extra models python -m vesuvius.ink_detection.inference.infer "$OUT/render.zarr" ~/scroll-prizes/checkpoints/ink_9um/$ck.pth "$OUT/ink_${tag}.tif" --resolution 0 --overlap 0.5 --blend-mode hann --batch-size 4 --direction both --no-compile --num-workers 3 2>"$OUT/ink_${tag}.err" >/dev/null || echo "INFER FAILED $tag: $(tail -1 $OUT/ink_${tag}.err)"
done
for t in "$OUT"/ink_*.tif; do case "$t" in *_preview*) continue;; esac; ~/.local/bin/uv run --extra models python ~/scroll-prizes/bin/tif_preview.py "$t" "${t%.tif}_preview-ds2.tif" 2 --rescale9um | cut -c1-140; done
echo "[$(date -Is)] done"; echo "PATCHQA-EXIT: 0"
