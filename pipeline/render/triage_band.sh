#!/usr/bin/env bash
# Geometry triage of one fit's snapped windings (research plan Phase A1): flatten (Lasagna) -> 66-layer render -> CT preview
# of the surface layer, from w070 outwards. Several GPUs can share the list (claims). Skips windings already done.
# Usage: [SCROLL=PHerc0191] triage_band.sh <fit-id, e.g. exp30k-z11200> <CUDA GPU UUID> [first=20] [last=119]
# For another scroll the CT is data/<scroll>/source/volume/*.zarr (passed to render66.sh as CT).
set -uo pipefail
case "$*" in *GPU-33b8aac6*) echo "REFUSED: GTX 1660 SUPER" >&2; exit 97;; esac
FIT=$1; GPU=$2; W0=${3:-20}; W1=${4:-119}; S=~/scroll-prizes; P=/mnt/nvme/scroll-prizes/data/${SCROLL:-PHerc0191}
SN=$P/geometry/$FIT/snapped; FL=$P/geometry/$FIT/flattened; R=$P/renders/$FIT; Q=$P/geometry/$FIT/qa/triage
mkdir -p $FL $R/logs $Q/previews $Q/claims
export TMPDIR=/mnt/nvme/scroll-prizes/scratch
[ "${SCROLL:-PHerc0191}" = PHerc0191 ] || export CT=$(ls -d $P/source/volume/*.zarr | head -1)
order=$(python3 -c "print(' '.join('w%03d'%w for w in sorted(range($W0, $W1 + 1), key=lambda w: (abs(w - 70), w))))")
for w in $order; do
  seg=$(ls -d $SN/${w}_* 2>/dev/null | grep -v spliced | head -1); [ -n "$seg" ] || continue
  [ -f $Q/previews/${w}_ct_d0.png ] && continue
  mkdir $Q/claims/$w 2>/dev/null || continue; echo $GPU > $Q/claims/$w/gpu
  echo "[$(date -Is)] $w"
  [ -d $FL/$w/tifxyz/flatten.tifxyz ] || $S/bin/flatten_winding.sh $seg $FL/$w $GPU > /dev/null 2>&1 || { echo "  flatten failed $w"; continue; }
  [ -d $R/$w.zarr/0 ] || $S/bin/render66.sh $FL/$w/tifxyz/flatten.tifxyz $R/$w.zarr 3 6 > $R/logs/$w.log 2>&1 || { echo "  render failed $w"; continue; }
  $S/villa/vesuvius/.venv/bin/python -I - "$R/$w.zarr" "$Q/previews/${w}_ct_d0.png" <<'PY' || echo "  preview failed $w"
import sys, zarr, numpy as np
from PIL import Image
a = zarr.open(sys.argv[1], mode="r")["0"]
L = a[33][::2, ::2]                          # layer 33 = d 0, half resolution
v = L[L > 0]
lo, hi = (np.percentile(v, [1, 99.5]) if v.size else (0, 255))
img = np.clip((L.astype(np.float32) - lo) / max(hi - lo, 1) * 255, 0, 255).astype(np.uint8); img[L == 0] = 0
Image.fromarray(img).save(sys.argv[2]); print("  preview", img.shape)
PY
done
echo "TRIAGEBAND-EXIT: 0"
