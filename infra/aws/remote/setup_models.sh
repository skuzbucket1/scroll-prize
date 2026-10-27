#!/usr/bin/env bash
# On the instance: lay out the four ink checkpoints the way Nieuwlaar's run_ink.sh expects (CKPT_DIR).
set -euo pipefail
H=/opt/scroll/hf; C=/opt/scroll/ckpt343; mkdir -p $C
ln -sfn $H/ink_9um/hybrid_3d2d-seed42/step-075000.pth $C/hybrid_3d2d-seed42_step-075000.pth
ln -sfn $H/ink_9um/hybrid_3d2d-seed43/step-075000.pth $C/hybrid_3d2d-seed43_step-075000.pth
ln -sfn $H/hecate/hecate_9.6um.pth $C/hecate_9.6um.pth
ln -sfn $H/hecate/hecate.py $C/hecate.py
if [ ! -s $C/dense_native-016000.pth ]; then
  cd /opt/scroll/villa/vesuvius && $HOME/.local/bin/uv run --no-sync python /opt/scroll/bin/ink343/rebuild_dense_native_pth.py \
    $H/ink9um-dense-native/weights/dense_native_016000.safetensors $H/ink9um-dense-native/training/configs/train_dense_native.json $C/dense_native-016000.pth
fi
# Extra 9 um ink models (MIT): Reader V3 (Domenico Russo; it replaced Reader v2 everywhere on 2026-10-27) and d9v4C
# (TAUIL-Abd-Elilah), same villa inference path as ink_9um. Reader V3 is pinned to the revision the GPU machine reads with
# and its sha256 checked: a wrong file stops the setup (exit 1), so no instance reads with a different model.
get() { [ -s "$C/$2" ] || curl -sfL --retry 3 "$1" -o "$C/$2.part" && mv -f "$C/$2.part" "$C/$2" 2>/dev/null || true
        echo "$2 sha256 $(sha256sum "$C/$2" 2>/dev/null | cut -c1-8)…$(sha256sum "$C/$2" 2>/dev/null | cut -c61-64)"; }
get https://huggingface.co/domenicor046/reader-v3/resolve/39f626e595304c35c6ef574ffc0b6cc1e0ed44cb/reader-v3.pth reader-v3.pth
[ "$(sha256sum $C/reader-v3.pth 2>/dev/null | cut -c1-64)" = ea405417450abd8ace1b8ff79ebce3adb646c5e48ab95da46844d77efe984d8a ] ||
  { echo "reader-v3.pth: wrong or missing file"; echo "SETUP-MODELS-FAILED"; exit 1; }
get https://github.com/TAUIL-Abd-Elilah/9um-reader-letter-shape/releases/download/v1.0/d9v4C_ft-006000.pth d9v4C_ft-006000.pth
ls -la $C | awk '{print $5, $9, $10, $11}'
echo "SETUP-MODELS-DONE"
