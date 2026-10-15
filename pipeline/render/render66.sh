#!/usr/bin/env bash
# 66-layer surface volume of a (flattened) tifxyz: layer k samples the CT at (k - 32.5) voxels along the normal; depth d = k - 33.
# Usage: CT=<volume.zarr or URL> render66.sh <segment.tifxyz> <out.zarr> [threads=4] [cache_gb=8]
# 2026-10-15 (audit B2): CT is required (it used to default to the PHerc0191 volume); the render is written to <out minus .zarr>.partial.zarr
# and moved into place only when vc_render_tifxyz exits 0 and the surface layer has CT in at least MIN_VALID (default 0.05)
# of its pixels; <out>/.ok marks a finished render (callers skip only when it exists); the script exits with the real code.
set -uo pipefail; export PATH=$HOME/.local/bin:$PATH
SEG=$1; OUT=${2%/}; T=${3:-4}; C=${4:-8}; PART=${OUT%.zarr}.partial.zarr
: ${CT:?set CT=<volume.zarr or URL>}
[ -f "$OUT/.ok" ] && { echo "RENDER66-EXIT: 0 (exists)"; exit 0; }
t0=$(date +%s); rm -rf "$PART"
OMP_NUM_THREADS=$T vc_render_tifxyz --volume "$CT" --group-idx 0 --scale 1 --segmentation "$SEG" --num-slices 66 --slice-step 1 --cache-gb $C --zarr-output "$PART"; rc=$?
if [ $rc -eq 0 ]; then
  v=$(${PYV:-${PY:-$HOME/scroll-prizes/villa/vesuvius/.venv/bin/python}} -I - "$PART" <<'PY'
import sys, zarr, numpy as np
a = np.asarray(zarr.open(sys.argv[1] + '/0', mode='r')[33]); print(f'{(a > 0).mean():.4f}')
PY
); [ -n "$v" ] || v=0
  if awk -v v="$v" -v m="${MIN_VALID:-0.05}" 'BEGIN{exit !(v >= m)}'; then
    rm -rf "$OUT"; mv "$PART" "$OUT" && echo "valid $v" > "$OUT/.ok" || rc=1
  else
    echo "surface layer valid share $v < ${MIN_VALID:-0.05}: render kept as $PART"; rc=3
  fi
fi
echo "[$(date -Is)] render66 rc=$rc in $(( $(date +%s)-t0 ))s -> $OUT"; echo "RENDER66-EXIT: $rc"; exit $rc
