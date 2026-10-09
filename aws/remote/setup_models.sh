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
ls -la $C | awk '{print $5, $9, $10, $11}'
echo "SETUP-MODELS-DONE"
