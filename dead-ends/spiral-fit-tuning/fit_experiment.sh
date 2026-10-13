#!/usr/bin/env bash
# Controlled spiral-fit experiment on PHerc0191. Usage: fit_experiment.sh <tag> <CUDA GPU UUID> '<extra overrides JSON>'
# GUARD (Ted, 2026-10-09): GPU 1 = GTX 1660 SUPER is NOT usable for any of this work (fitter 0.04 it/s; ink inference writes all-zero maps). Refuse its UUID.
case "$*" in *GPU-33b8aac6-6d34-6282-b644-f5407aa8f190*) echo "REFUSED: GPU-33b8aac6-6d34-6282-b644-f5407aa8f190 (GTX 1660 SUPER) is not usable for this work; use GPU 0/2/3" >&2; exit 97;; esac
set -uo pipefail
TAG=$1; GPU=$2; EXTRA=${3:-'{}'}; D=/mnt/nvme/scroll-prizes/data/PHerc0191; S=$D/spiral-dataset
cd ~/scroll-prizes/villa/spiral-fitting
BASE='{"z_begin":9000,"z_end":10000,"optimizer_num_training_steps":10000,"input_use_verified_patches":false,"input_use_tracks":true,"input_use_outer_shell":false,"input_use_winding_inference":false,"input_use_fibers":false,"input_use_pcl_absolute":false,"input_use_pcl_relative":false,"input_use_pcl_same_winding":false,"input_use_pcl_drawn_control_points":false,"dense_spacing_mode":"grad_mag","loss_weight_shell_outer":0,"output_save_png_visualizations":true}'
export FIT_SPIRAL_CONFIG_OVERRIDES=$(python3 -c '
import json,re,sys; want=json.loads(sys.argv[1]); want.update(json.loads(sys.argv[2])); src=open("config.py").read()
keep={k:v for k,v in want.items() if re.search(r"[\x22\x27]%s[\x22\x27]|self\.%s\b" % (k,k), src)}
print(json.dumps(keep)); print("dropped unknown keys:", [k for k in want if k not in keep], file=sys.stderr)' "$BASE" "$EXTRA")
echo "overrides: $FIT_SPIRAL_CONFIG_OVERRIDES"
export FIT_SPIRAL_OUT_DIR=$D/spiral-output FIT_SPIRAL_CACHE_DIR=/mnt/nvme/scroll-prizes/cache/spiral FIT_SPIRAL_RUN_TAG=$TAG CUDA_VISIBLE_DEVICES=$GPU
echo "[$(date -Is)] start fit $TAG on $GPU"; t0=$(date +%s)
~/.local/bin/uv run python fit_spiral.py --dataset "$S" > ~/scroll-prizes/fit-$TAG-full.log 2>&1; rc=$?
grep -E "^step [0-9]+: loss" ~/scroll-prizes/fit-$TAG-full.log | tail -2 | cut -c1-160
R=$(ls -td $D/spiral-output/*${TAG}*/ 2>/dev/null | head -1); [ -n "$R" ] && python3 -c "import json; s=json.load(open('$R/satisfaction_metrics_fitted.json'))['summary']; print('satisfied_track_points_fraction', round(s['satisfied_track_points_fraction'],4), 'satisfied_tracks_fraction', round(s['satisfied_tracks_fraction'],4))" 2>/dev/null
echo "[$(date -Is)] fit $TAG done rc=$rc in $(( $(date +%s)-t0 ))s"; echo "FIT-EXIT: $rc"
