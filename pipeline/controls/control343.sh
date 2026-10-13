#!/usr/bin/env bash
# Positive control: run the PHerc. 343 winning segment (Nieuwlaar, MIT) through OUR fast-ink pipeline unchanged:
# 66-layer render (streamed CT) -> ink_9um seed 42 at d +1/0/+2/-1 via run_ink.sh -> our triage previews.
# Expectation: the published letters (πα̣ντ̣ογιν̣ομ̣…) are visible in the d+1 READING-side preview. Usage: control343.sh <CUDA GPU UUID>
set -uo pipefail; export PATH=$HOME/.local/bin:$PATH
case "$*" in *GPU-33b8aac6*) echo REFUSED; exit 97;; esac
export CUDA_VISIBLE_DEVICES=$1
S=~/scroll-prizes; C=/mnt/nvme/scroll-prizes/data/PHerc0343/control; CACHE=/mnt/nvme/scroll-prizes/cache/PHerc0343-l0
URL=https://vesuvius-challenge-open-data.s3.amazonaws.com/PHerc0343/volumes/20250521140437-8.640um-1.2m-116keV-masked.zarr
SEG=$C/concat_w047-w048_R5B2_z9500-11000.tifxyz; Z=$C/control343_66.zarr
t0=$(date +%s)
if [ ! -d $Z/0 ]; then
  OMP_NUM_THREADS=3 vc_render_tifxyz --volume "$CACHE" --remote-url "$URL" --group-idx 0 --scale 1 --segmentation "$SEG" \
     --num-slices 66 --slice-step 1 --cache-gb 6 --zarr-output "$Z" > $C/render.log 2>&1 || { echo "render failed"; tail -5 $C/render.log; echo "CONTROL-EXIT: 1"; exit 1; }
fi
echo "render done in $(( $(date +%s)-t0 ))s; cache $(du -sh $CACHE | cut -f1)"
export CKPT_DIR=$S/checkpoints/ckpt343 PY=$S/villa/vesuvius/.venv/bin/python N_LAYERS=66 NATIVE_UM=8.64 VILLA_BATCH=4 TMPDIR=/mnt/nvme/scroll-prizes/tmp
cd $S/villa/vesuvius
for d in 1 0 2 -1; do nice -n 5 bash $S/bin/ink343/run_ink.sh "$Z" hybrid_3d2d-seed42 $d $C/maps > $C/ink_d$d.log 2>&1 || echo "ink failed d=$d"; done
$PY -I - "$C/maps" "control343_66" "$C/preview" <<'PYS'
import sys, glob, os, numpy as np, tifffile
from PIL import Image
mdir, name, pref = sys.argv[1:4]
for f in sorted(glob.glob(os.path.join(mdir, name + "__hybrid_3d2d-seed42__L66s*.tif"))):
    s = int(f.split("L66s")[1].split("_")[0].split(".")[0]); d = s + 8 - 33
    side = "read" if f.endswith("_reverse.tif") else "blind"
    a = tifffile.imread(f).astype(np.float32); v = np.clip((a - 64) / 128, 0, 1)
    im = Image.fromarray((v * 255).astype(np.uint8)); im = im.resize((im.width // 2, im.height // 2), Image.LANCZOS)
    im.save(f"{pref}_d{d:+d}_{side}.png")
print("previews written")
PYS
echo "CONTROL-EXIT: 0 in $(( $(date +%s)-t0 ))s"
