#!/usr/bin/env bash
# Phase 2 pilot: 1000-slice band fit on PHerc0191 via the minimal input route (tracks + lasagna normals + umbilicus), one RTX 3060.
set -uo pipefail
D=/mnt/nvme/scroll-prizes/data/PHerc0191; S=$D/spiral-dataset
until grep -q 'ASSEMBLE-EXIT:' ~/scroll-prizes/assemble-pherc0191.log 2>/dev/null; do sleep 60; done
grep -q 'ASSEMBLE-EXIT: 0' ~/scroll-prizes/assemble-pherc0191.log || { echo "assembly failed"; echo "PILOT-EXIT: 90"; exit 1; }
cd ~/scroll-prizes/villa/spiral-fitting
WANT='{"z_begin":9000,"z_end":10000,"optimizer_num_training_steps":10000,"input_use_verified_patches":false,"input_use_tracks":true,"input_use_outer_shell":false,"input_use_winding_inference":false,"input_use_fibers":false,"input_use_pcl_absolute":false,"input_use_pcl_relative":false,"input_use_pcl_same_winding":false,"input_use_pcl_drawn_control_points":false,"dense_spacing_mode":"grad_mag","loss_weight_shell_outer":0,"output_save_png_visualizations":true}'
# keep only override keys that exist in config.py — unknown keys make fit_spiral.py raise
export FIT_SPIRAL_CONFIG_OVERRIDES=$(python3 -c '
import json,re,sys; want=json.loads(sys.argv[1]); src=open("config.py").read()
keep={k:v for k,v in want.items() if re.search(r"[\x22\x27]%s[\x22\x27]|self\.%s\b" % (k,k), src)}
print(json.dumps(keep)); print("dropped unknown keys:", [k for k in want if k not in keep], file=sys.stderr)' "$WANT")
echo "overrides: $FIT_SPIRAL_CONFIG_OVERRIDES"
export FIT_SPIRAL_OUT_DIR=$D/spiral-output FIT_SPIRAL_CACHE_DIR=/mnt/nvme/scroll-prizes/cache/spiral FIT_SPIRAL_RUN_TAG=pilot-z9000-10000
export CUDA_VISIBLE_DEVICES=GPU-2d9651e9-5a94-e0cb-6a99-9300d8056524
mkdir -p "$FIT_SPIRAL_OUT_DIR" "$FIT_SPIRAL_CACHE_DIR"
echo "[$(date -Is)] start pilot fit"; t0=$(date +%s)
~/.local/bin/uv run python fit_spiral.py --dataset "$S" > ~/scroll-prizes/pilot-fit-full.log 2>&1; rc=$?
grep -E 'step|loss|satisf|Error|error|Traceback' ~/scroll-prizes/pilot-fit-full.log | tail -25 | cut -c1-200
echo "[$(date -Is)] pilot done rc=$rc in $(( $(date +%s)-t0 ))s"; ls -la "$FIT_SPIRAL_OUT_DIR" 2>/dev/null | tail -4; echo "PILOT-EXIT: $rc"
