#!/bin/bash
# Download the public winding model (scrollprize/winding_model_9um) into checkpoints/.
cd ~/scroll-prizes/villa/vesuvius
OUT=~/scroll-prizes/checkpoints/winding_model_9um
mkdir -p "$OUT"
~/.local/bin/uv run --extra models python - "$OUT" <<'PY'
import sys
from huggingface_hub import snapshot_download
p = snapshot_download("scrollprize/winding_model_9um", local_dir=sys.argv[1])
print("downloaded to", p)
PY
rc=$?
ls -la "$OUT"
echo "HFWIND-EXIT: $rc"
