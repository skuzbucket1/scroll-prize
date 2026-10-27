#!/usr/bin/env bash
# On the instance: 66-layer render of one tifxyz segment straight from the public S3 volume, then ink maps for the given
# models and depths with Nieuwlaar's run_ink.sh, then quick previews. Resumable (existing renders/maps are skipped).
# Usage: run_segment.sh <name> <segment.tifxyz dir> <volume zarr URL> <native_um> <models,comma> <depths,comma>
# The VC3D release of 2026-10 streams a remote --volume itself (chunks kept in ~/.VC3D/remote_cache) and refuses the old
# --volume <cache dir> --remote-url <URL> pair, so the URL is passed as --volume, with the chunks prefetched first.
# GROUP_IDX=<level> renders from that pyramid level of the volume (default 0); native_um is then that level's voxel size.
# 2026-10-15 (audit B1/B2/B3/B6): native_um must match the volume name at level 0; the render goes to <name>_66.partial.zarr
# and is moved into place (with .ok) only when complete; each ink job's real exit code is logged; RUN-EXIT is 0 only when
# every (model, depth, face) map exists, otherwise 1 with the missing maps listed.
set -uo pipefail
NAME=$1; SEG=$2; URL=$3; UM=$4; MODELS=${5//,/ }; DEPTHS=${6//,/ }
[[ "$UM" =~ ^[0-9]+(\.[0-9]+)?$ ]] || { echo "native_um '$UM' is not a number"; echo "RUN-EXIT: 1"; exit 1; }
VU=$(echo "$URL" | grep -oE -- '-[0-9]+\.[0-9]+um-' | tr -d 'um-' | head -1)
if [ -n "$VU" ] && [ "${GROUP_IDX:-0}" = 0 ] && ! awk -v a="$UM" -v b="$VU" 'BEGIN{exit !((a - b) ^ 2 < 1e-6)}'; then
  echo "native_um $UM does not match the volume ($VU um)"; echo "RUN-EXIT: 1"; exit 1; fi
R=/opt/scroll/results/$NAME; W=/opt/scroll/work; mkdir -p $R/maps $R/previews $W /opt/scroll/cache/$NAME
TIM=$R/timings.tsv; [ -f $TIM ] || printf 'step\tseconds\trc\n' > $TIM
# Snapped but not yet flattened (anything not named flatten.tifxyz): flatten here with Lasagna first.
if [ "$(basename "${SEG%/}")" != flatten.tifxyz ]; then
  F=$R/flatten
  if [ ! -d $F/tifxyz/flatten.tifxyz ]; then
    printf '{"external_surfaces": [{"path": "%s"}]}\n' "${SEG%/}" > $W/${NAME}_flatten_in.json
    t0=$(date +%s)
    (cd /opt/scroll/villa/lasagna && .venv/bin/python fit.py configs/flatten_fast_nofilter.json $W/${NAME}_flatten_in.json \
       --out-dir $F --device cuda > $R/flatten.log 2>&1); rc=$?
    printf 'flatten\t%s\t%s\n' $(( $(date +%s)-t0 )) $rc >> $TIM
    [ -d $F/tifxyz/flatten.tifxyz ] || { tail -5 $R/flatten.log; echo "RUN-EXIT: 1"; exit 1; }
  fi
  SEG=$F/tifxyz/flatten.tifxyz
fi
Z=$W/${NAME}_66.zarr; ZP=$W/${NAME}_66.partial.zarr
if [ ! -f $Z/.ok ]; then
  t0=$(date +%s); rm -rf $ZP
  QT_QPA_PLATFORM=offscreen OMP_NUM_THREADS=$(nproc) /opt/scroll/vc3d/AppRun vc_render_tifxyz --volume "$URL" --prefetch-remote \
     --group-idx ${GROUP_IDX:-0} --scale 1 --segmentation "$SEG" --num-slices 66 --slice-step 1 --cache-gb 8 --zarr-output "$ZP" > $R/render.log 2>&1
  rc=$?; printf 'render66\t%s\t%s\n' $(( $(date +%s)-t0 )) $rc >> $TIM; [ $rc -eq 0 ] || { tail -5 $R/render.log; echo "RUN-EXIT: 1"; exit 1; }
  v=$(/opt/scroll/villa/vesuvius/.venv/bin/python -I -c "import sys, zarr, numpy as np; print(f'{(np.asarray(zarr.open(sys.argv[1] + \"/0\", mode=\"r\")[33]) > 0).mean():.4f}')" $ZP 2>/dev/null)
  awk -v v="${v:-0}" 'BEGIN{exit !(v >= 0.05)}' || { echo "render has CT in only ${v:-0} of the surface layer"; echo "RUN-EXIT: 1"; exit 1; }
  rm -rf $Z; mv $ZP $Z && echo "valid $v" > $Z/.ok
fi
export CKPT_DIR=/opt/scroll/ckpt343 PY=/opt/scroll/villa/vesuvius/.venv/bin/python HECATE_PY=/opt/scroll/ckpt343/hecate.py PREP_PY=/opt/scroll/bin/ink343/hecate_prep.py
export N_LAYERS=66 NATIVE_UM=$UM VILLA_BATCH=4 HEC_BATCH=4 HEC_DEVICE=cuda TMPDIR=/opt/scroll/tmp; mkdir -p $TMPDIR
cd /opt/scroll/villa/vesuvius
# INK_PAR (env, else /opt/scroll/jobs/ink_par, else 1): that many (model, depth) maps at once. 2026-10-27: one Reader V3 pass keeps one CPU
# thread busy and the A10G at 0-25 %, so the depths of a winding run side by side (same maps, each its own process and temp folder).
INK_PAR=${INK_PAR:-$(cat /opt/scroll/jobs/ink_par 2>/dev/null || echo 1)}
for d in $DEPTHS; do for m in $MODELS; do
  if [ "$m" = hecate ]; then zc=$(awk -v d="$d" 'BEGIN{printf "%.2f", 32.5 + d}'); f=$R/maps/${NAME}_66__hecate__L66zc${zc}; ext=png
  else s=$(( 33 + d - 8 )); f=$R/maps/${NAME}_66__${m}__L66s${s}; ext=tif; fi
  [ -s $f.$ext ] && [ -s ${f}_reverse.$ext ] && continue
  while [ $(jobs -rp | wc -l) -ge $INK_PAR ]; do wait -n; done
  ( t0=$(date +%s); bash /opt/scroll/bin/ink343/run_ink.sh "$Z" $m $d $R/maps > $R/ink_${m}_d${d}.log 2>&1; rc=$?
    printf 'ink %s d=%s\t%s\t%s\n' $m $d $(( $(date +%s)-t0 )) $rc >> $TIM ) &
done; done
wait
miss=""
for d in $DEPTHS; do for m in $MODELS; do
  if [ "$m" = hecate ]; then zc=$(awk -v d="$d" 'BEGIN{printf "%.2f", 32.5 + d}'); f=$R/maps/${NAME}_66__hecate__L66zc${zc}; ext=png
  else f=$R/maps/${NAME}_66__${m}__L66s$(( 25 + d )); ext=tif; fi
  for g in $f.$ext ${f}_reverse.$ext; do [ -s $g ] || miss="$miss $(basename $g)"; done
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
[ -z "$miss" ] || { echo "missing maps:$miss"; echo "RUN-EXIT: 1"; exit 1; }
echo "RUN-EXIT: 0"
