#!/usr/bin/env bash
# Resume the paused CT volume mirror once the three lasagna stores (fitter prerequisites) have finished downloading.
D=/mnt/nvme/scroll-prizes/data/PHerc0191
for st in nx ny grad_mag; do until grep -q 'MIRROR-EXIT' "$D/mirror-lasagna-v2-PHerc0191_$st.log" 2>/dev/null; do sleep 60; done; done
P=$(pgrep -f 'mirror_s3.py.*volumes/' | head -1); [ -n "$P" ] && kill -CONT "$P" && echo "[$(date -Is)] volume mirror RESUMED (pid $P)" || echo "[$(date -Is)] volume mirror process not found"
