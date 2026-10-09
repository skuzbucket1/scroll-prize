#!/usr/bin/env bash
# On the instance: 66-layer render of one tifxyz segment straight from the public S3 volume, then ink maps for the given
# models and depths with Nieuwlaar's run_ink.sh, then quick previews. Resumable (existing renders/maps are skipped).
# Usage: run_segment.sh <name> <segment.tifxyz dir> <volume zarr URL> <native_um> <models,comma> <depths,comma>
set -uo pipefail
NAME=$1; SEG=$2; URL=$3; UM=$4; MODELS=${5//,/ }; DEPTHS=${6//,/ }
R=/opt/scroll/results/$NAME; W=/opt/scroll/work; mkdir -p $R/maps $R/previews $W /opt/scroll/cache/$NAME
TIM=$R/timings.tsv; [ -f $TIM ] || printf 'step\tseconds\trc\n' > $TIM
Z=$W/${NAME}_66.zarr
if [ ! -d $Z/0 ]; then
  t0=$(date +%s)
  QT_QPA_PLATFORM=offscreen OMP_NUM_THREADS=$(nproc) /opt/scroll/vc3d/AppRun vc_render_tifxyz --volume /opt/scroll/cache/$NAME --remote-url "$URL" \
     --group-idx 0 --scale 1 --segmentation "$SEG" --num-slices 66 --slice-step 1 --cache-gb 8 --zarr-output "$Z" > $R/render.log 2>&1
  rc=$?; printf 'render66\t%s\t%s\n' $(( $(date +%s)-t0 )) $rc >> $TIM; [ $rc -eq 0 ] || { tail -5 $R/render.log; echo "RUN-EXIT: 1"; exit 1; }
fi
export CKPT_DIR=/opt/scroll/ckpt343 PY=/opt/scroll/villa/vesuvius/.venv/bin/python HECATE_PY=/opt/scroll/ckpt343/hecate.py PREP_PY=/opt/scroll/bin/ink343/hecate_prep.py
export N_LAYERS=66 NATIVE_UM=$UM VILLA_BATCH=4 HEC_BATCH=4 HEC_DEVICE=cuda TMPDIR=/opt/scroll/tmp; mkdir -p $TMPDIR
cd /opt/scroll/villa/vesuvius
for d in $DEPTHS; do for m in $MODELS; do
  if [ "$m" = hecate ]; then zc=$(awk -v d="$d" 'BEGIN{printf "%.2f", 32.5 + d}'); f=$R/maps/${NAME}_66__hecate__L66zc${zc}; ext=png
  else s=$(( 33 + d - 8 )); f=$R/maps/${NAME}_66__${m}__L66s${s}; ext=tif; fi
  [ -s $f.$ext ] && [ -s ${f}_reverse.$ext ] && continue
  t0=$(date +%s); bash /opt/scroll/bin/ink343/run_ink.sh "$Z" $m $d $R/maps > $R/ink_${m}_d${d}.log 2>&1
  printf 'ink %s d=%s\t%s\t%s\n' $m $d $(( $(date +%s)-t0 )) $? >> $TIM
done; done
$PY - "$R/maps" "${NAME}_66" "$R/previews" <<'PY'
import sys, glob, os, numpy as np, tifffile
from PIL import Image
mdir, name, out = sys.argv[1:4]
for f in sorted(glob.glob(os.path.join(mdir, name + "__*__L66s*.tif"))):
    model = f.split("__")[1]; s = int(f.split("L66s")[1].split("_")[0].split(".")[0]); d = s + 8 - 33
    side = "read" if f.endswith("_reverse.tif") else "blind"
    a = tifffile.imread(f).astype(np.float32); v = np.clip((a - 64) / 128, 0, 1)
    im = Image.fromarray((v * 255).astype(np.uint8)); im = im.resize((max(1, im.width // 2), max(1, im.height // 2)), Image.LANCZOS)
    im.save(os.path.join(out, f"{model}_d{d:+d}_{side}.png"))
print("previews written")
PY
nvidia-smi --query-gpu=name,memory.used --format=csv,noheader >> $R/gpu.txt
echo "RUN-EXIT: 0"
