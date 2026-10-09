#!/bin/bash
cd ~/scroll-prizes/villa/vesuvius
~/.local/bin/uv run --extra models python - <<'PY'
from huggingface_hub import snapshot_download
for repo, d in (("scrollprize/hecate", "hecate"), ("Nieuwlaar/ink9um-dense-native", "dense_native")):
    p = snapshot_download(repo, local_dir=f"/home/tbienapfl/scroll-prizes/checkpoints/{d}"); print("downloaded", repo, "->", p)
PY
ls -la ~/scroll-prizes/checkpoints/hecate ~/scroll-prizes/checkpoints/dense_native | head -30
echo "HFINK-EXIT: $?"
