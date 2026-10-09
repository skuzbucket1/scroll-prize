#!/usr/bin/env bash
# 66-layer surface volume of a (flattened) tifxyz: layer k samples the CT at (k - 32.5) voxels along the normal; depth d = k - 33.
# Usage: render66.sh <segment.tifxyz> <out.zarr> [threads=4] [cache_gb=8]
set -uo pipefail; export PATH=$HOME/.local/bin:$PATH
SEG=$1; OUT=$2; T=${3:-4}; C=${4:-8}
CT=/mnt/nvme/scroll-prizes/data/PHerc0191/volumes/20250821151635-9.362um-1.2m-113keV-masked.zarr
t0=$(date +%s)
OMP_NUM_THREADS=$T vc_render_tifxyz --volume "$CT" --group-idx 0 --scale 1 --segmentation "$SEG" --num-slices 66 --slice-step 1 --cache-gb $C --zarr-output "$OUT"; rc=$?
echo "[$(date -Is)] render66 rc=$rc in $(( $(date +%s)-t0 ))s -> $OUT"; echo "RENDER66-EXIT: $rc"
