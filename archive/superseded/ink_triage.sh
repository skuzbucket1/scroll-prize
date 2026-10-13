#!/usr/bin/env bash
# Fast ink pass over every triaged winding: ink_9um seed 42 at d = +1, 0, +2, -1 (both sides), then a preview per depth.
# Works through render66/exp30k_snapped_<w>_66.zarr in triage order as they appear; waits for new ones until TRIAGE-EXIT.
# Usage: ink_triage.sh <CUDA GPU UUID>
set -uo pipefail
case "$*" in *GPU-33b8aac6*) echo "REFUSED: GTX 1660 SUPER" >&2; exit 97;; esac
export CUDA_VISIBLE_DEVICES=$1
S=~/scroll-prizes; D=/mnt/nvme/scroll-prizes/data/PHerc0191; R6=$D/render66; OUT=$D/ink-triage; mkdir -p $OUT/previews $OUT/claims
export CKPT_DIR=$S/checkpoints/ckpt343 PY=$S/villa/vesuvius/.venv/bin/python N_LAYERS=66 NATIVE_UM=9.362 VILLA_BATCH=4 TMPDIR=/mnt/nvme/scroll-prizes/tmp
order=$(python3 -c "print(' '.join('w%03d'%w for w in sorted(range(20,120), key=lambda w:(abs(w-70), w))))")
cd $S/villa/vesuvius
while true; do
  did=0
  for w in $order; do
    z=$R6/exp30k_snapped_${w}_66.zarr
    [ -f $D/triage/previews/${w}_ct_d0.png ] || continue          # render finished (preview is written after it)
    [ -f $OUT/previews/${w}_done ] && continue
    mkdir $OUT/claims/$w 2>/dev/null || { [ "$(cat $OUT/claims/$w/gpu 2>/dev/null)" = "$CUDA_VISIBLE_DEVICES" ] || continue; }   # one worker per winding
    echo $CUDA_VISIBLE_DEVICES > $OUT/claims/$w/gpu
    echo "[$(date -Is)] $w"
    for d in 1 0 2 -1; do
      s=$(( 33 + d - 8 )); f=$OUT/maps/exp30k_snapped_${w}_66__hybrid_3d2d-seed42__L66s${s}
      [ -s ${f}.tif ] && [ -s ${f}_reverse.tif ] && continue          # resume: map pair already there
      nice -n 5 bash $S/bin/ink343/run_ink.sh "$z" hybrid_3d2d-seed42 $d $OUT/maps > $OUT/${w}_d${d}.log 2>&1 || echo "  ink failed $w d=$d"
    done
    $PY -I - "$OUT/maps" "exp30k_snapped_${w}_66" "$OUT/previews/$w" <<'PYS' || echo "  preview failed $w"
import sys, glob, os, numpy as np, tifffile
from PIL import Image
mdir, name, pref = sys.argv[1:4]
for f in sorted(glob.glob(os.path.join(mdir, name + "__hybrid_3d2d-seed42__L66s*.tif"))):
    s = int(f.split("L66s")[1].split("_")[0].split(".")[0]); d = s + 8 - 33
    side = "read" if f.endswith("_reverse.tif") else "blind"
    a = tifffile.imread(f).astype(np.float32)
    v = np.clip((a - 64) / 128, 0, 1)                       # (p - 0.25) / 0.5 display stretch
    im = Image.fromarray((v * 255).astype(np.uint8)); im = im.resize((im.width // 2, im.height // 2), Image.LANCZOS)
    im.save(f"{pref}_d{d:+d}_{side}.png")
print("previews", pref)
PYS
    touch $OUT/previews/${w}_done; did=1
  done
  grep -q TRIAGE-EXIT $S/triage-windings.log 2>/dev/null && [ $did -eq 0 ] && break
  [ $did -eq 0 ] && sleep 120
done
echo "INKTRIAGE-EXIT: 0"
