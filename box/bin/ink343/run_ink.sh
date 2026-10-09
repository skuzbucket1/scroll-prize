#!/bin/bash
# run_ink.sh - one ink map pair (reading side + blind side) for one surface volume, one model and one depth d.
#
#   run_ink.sh <surface.zarr> <model> <d> <out_dir>
#
#   surface.zarr  66-layer surface volume rendered from a submitted mesh (zarr group with array "0", Z,Y,X uint8),
#                 as written by mesh/render_66_layers.sh (layer k samples the CT at k - 32.5 voxels along
#                 the mesh normal; d = k - 33; + = away from the scroll axis; no --flip-normals)
#   model         dnative | hybrid_3d2d-seed42 | hybrid_3d2d-seed43 | hecate
#   d             integer depth, -15..+15 for the 66-layer renders
#   out_dir       output directory
#
# Outputs (same names as in my runs):
#   villa models:  <name>__<model>__L66s<s>.tif (forward = BLIND side) and <name>__<model>__L66s<s>_reverse.tif (reverse =
#                  READING side); uint8 = trunc(255 * p), with s = d + 25 (layers s..s+16, centre layer 33 + d)
#   hecate:        <name>__hecate__L66zc<zc>.png (forward, BLIND) and ..._reverse.png (READING side), 9.6 um grid,
#                  uint8 = round(255 * p), with zc = 32.5 + d
#
# Environment: CKPT_DIR (/opt/ckpt), PY (/opt/venv/bin/python), HECATE_PY ($CKPT_DIR/hecate.py),
#              PREP_PY (hecate_prep.py next to this script), N_LAYERS (66), NATIVE_UM (8.64),
#              VILLA_BATCH (4), HEC_BATCH (4), HEC_DEVICE (cuda), TMPDIR (needs ~10 bytes per output pixel).
set -euo pipefail
export LC_ALL=C          # decimal point in awk output, whatever the host locale
[[ $# -eq 4 ]] || { awk 'NR > 1 && /^#/ {print; next} NR > 1 {exit}' "$0"; exit 2; }
Z=$(cd "$(dirname "$1")" && pwd)/$(basename "$1"); MODEL=$2; D=$3; OUT=$4
HERE=$(cd "$(dirname "$0")" && pwd)
CKPT_DIR=${CKPT_DIR:-/opt/ckpt}; PY=${PY:-/opt/venv/bin/python}
HECATE_PY=${HECATE_PY:-$CKPT_DIR/hecate.py}; PREP_PY=${PREP_PY:-$HERE/hecate_prep.py}
N=${N_LAYERS:-66}; UM=${NATIVE_UM:-8.64}
NAME=$(basename "$Z" .zarr)
mkdir -p "$OUT"; OUT=$(cd "$OUT" && pwd)
T=$(mktemp -d "${TMPDIR:-/tmp}/run_ink.XXXXXX"); trap 'rm -rf "$T"' EXIT

case $MODEL in
  dnative)
    CK=$CKPT_DIR/dense_native-016000.pth
    [[ -s $CK ]] || CK=$CKPT_DIR/dense_native-016000.rebuilt.pth ;;
  hybrid_3d2d-seed42|hybrid_3d2d-seed43) CK=$CKPT_DIR/${MODEL}_step-075000.pth ;;
  hecate) CK=$CKPT_DIR/hecate_9.6um.pth ;;
  *) echo "unknown model $MODEL"; exit 2 ;;
esac
[[ -s $CK ]] || { echo "checkpoint missing: $CK (run fetch_checkpoints.sh)"; exit 3; }

# All maps of this submission were computed on level-0-only copies of the renders (villa's occupancy scan then runs at
# full resolution). A full VC3D render also holds pyramid levels 1-5; present such a render as level 0 only, via a
# symlink, so that villa selects exactly the same patches.
ZIN=$Z
if [[ -d $Z/1 && -f $Z/0/.zarray ]]; then
  mkdir -p "$T/l0.zarr"; echo '{"zarr_format": 2}' > "$T/l0.zarr/.zgroup"; ln -s "$Z/0" "$T/l0.zarr/0"; ZIN=$T/l0.zarr
fi

if [[ $MODEL != hecate ]]; then
  # 17-layer window s..s+16 centred on layer N/2 + d (= 33 + d); --layer-end is exclusive
  S=$(( N / 2 + D - 8 )); E=$(( S + 17 ))
  (( S >= 0 && E <= N )) || { echo "d=$D gives layers $S..$((E - 1)), outside 0..$((N - 1))"; exit 2; }
  (cd "$T" && TMPDIR=$T "$PY" -m vesuvius.ink_detection.inference.infer "$ZIN" "$CK" "$T/out.tif" \
      --overlap 0.5 --blend-mode hann --batch-size "${VILLA_BATCH:-4}" --direction both \
      --layer-start "$S" --layer-end "$E")
  [[ -s $T/out.tif && -s $T/out_reverse.tif ]] || { echo "infer produced no output"; exit 4; }
  mv -f "$T/out.tif" "$OUT/${NAME}__${MODEL}__L${N}s${S}.tif"
  mv -f "$T/out_reverse.tif" "$OUT/${NAME}__${MODEL}__L${N}s${S}_reverse.tif"
  echo "$OUT/${NAME}__${MODEL}__L${N}s${S}{,_reverse}.tif"
else
  # 16 planes at 9.6 um centred on native layer (N-1)/2 + d (= 32.5 + d), linear interpolation in depth
  ZC=$(awk -v n="$N" -v d="$D" 'BEGIN{printf "%.2f", (n - 1) / 2 + d}')
  [[ -s $HECATE_PY ]] || { echo "hecate.py missing: $HECATE_PY"; exit 3; }
  "$PY" "$PREP_PY" --src "$Z" --out "$T/prep.zarr" --native-um "$UM" --native-um-z "$UM" --target-um 9.6 \
      --z-center "$ZC" --nz 16
  for R in "" --reverse; do
    SUF=""; [[ -n $R ]] && SUF=_reverse
    (cd "$T" && TMPDIR=$T "$PY" "$HECATE_PY" --checkpoint "$CK" --input "$T/prep.zarr" --spacing-um 9.6 \
        --output "$T/out$SUF.png" --device "${HEC_DEVICE:-cuda}" --batch-size "${HEC_BATCH:-4}" $R)
  done
  [[ -s $T/out.png && -s $T/out_reverse.png ]] || { echo "hecate produced no output"; exit 4; }
  mv -f "$T/out.png" "$OUT/${NAME}__hecate__L${N}zc${ZC}.png"
  mv -f "$T/out_reverse.png" "$OUT/${NAME}__hecate__L${N}zc${ZC}_reverse.png"
  [[ -s $T/out.json ]] && mv -f "$T/out.json" "$OUT/${NAME}__hecate__L${N}zc${ZC}.json"
  [[ -s $T/out_reverse.json ]] && mv -f "$T/out_reverse.json" "$OUT/${NAME}__hecate__L${N}zc${ZC}_reverse.json"
  echo "$OUT/${NAME}__hecate__L${N}zc${ZC}{,_reverse}.png"
fi
