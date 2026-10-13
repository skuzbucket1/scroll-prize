#!/usr/bin/env bash
# Geometry triage for all snapped exp-30k windings: flatten (Lasagna) -> 66-layer render -> CT preview of the surface layer.
# Order: from w070 outwards. Skips windings already done. Usage: triage_windings.sh <CUDA GPU UUID>
set -uo pipefail
case "$*" in *GPU-33b8aac6*) echo "REFUSED: GTX 1660 SUPER" >&2; exit 97;; esac
GPU=$1; S=~/scroll-prizes; D=/mnt/nvme/scroll-prizes/data/PHerc0191
SN=$D/snapped/exp-30k; FL=$D/flatten; R6=$D/render66; PV=$D/triage/previews; mkdir -p $PV
order=$(python3 -c "print(' '.join('w%03d'%w for w in sorted(range(20,120), key=lambda w:(abs(w-70), w))))")
for w in $order; do
  seg=$SN/${w}_exp-30k; [ -d $seg ] || continue
  out=$FL/exp-30k-snapped-$w; z=$R6/exp30k_snapped_${w}_66.zarr
  [ -f $PV/${w}_ct_d0.png ] && continue
  echo "[$(date -Is)] $w"
  [ -d $out/tifxyz/flatten.tifxyz ] || $S/bin/flatten_winding.sh $seg $out $GPU > /dev/null 2>&1 || { echo "  flatten failed $w"; continue; }
  [ -d $z/0 ] || $S/bin/render66.sh $out/tifxyz/flatten.tifxyz $z 3 6 > $R6/render_$w.log 2>&1 || { echo "  render failed $w"; continue; }
  $S/villa/vesuvius/.venv/bin/python -I - "$z" "$PV/${w}_ct_d0.png" <<'PY' || echo "  preview failed $w"
import sys, zarr, numpy as np
from PIL import Image
a = zarr.open(sys.argv[1], mode="r")["0"]
L = a[33]                                   # layer 33 = d 0
L = L[::2, ::2]
v = L[L > 0]
lo, hi = (np.percentile(v, [1, 99.5]) if v.size else (0, 255))
img = np.clip((L.astype(np.float32) - lo) / max(hi - lo, 1) * 255, 0, 255).astype(np.uint8)
img[L == 0] = 0
Image.fromarray(img).save(sys.argv[2]); print("  preview", img.shape)
PY
done
echo "TRIAGE-EXIT: 0"
