#!/bin/bash
# The PHerc. 343 winner's fit recipe on our band, with the pre-simplification fitter (villa 0fb38c45):
# surf-SDT + dense_spacing_mode phase, no shell, tracks + normals + umbilicus, 30k steps.
S=~/scroll-prizes; D=/mnt/nvme/scroll-prizes/data/PHerc0191
SP=/mnt/nvme/scroll-prizes/wt/spiral-0fb38c45/volume-cartographer/scripts/spiral
TAG=${1:-old-phase-30k}; GPU=${2:-GPU-2d9651e9-5a94-e0cb-6a99-9300d8056524}
case "$GPU" in *GPU-33b8aac6*) echo REFUSED; exit 97;; esac
until grep -q "SDT-EXIT" $S/surf-sdt.log 2>/dev/null; do sleep 120; done
grep -q "SDT-EXIT: 0" $S/surf-sdt.log || { echo "SDT build failed"; echo "FIT-EXIT: 90"; exit 1; }
cd $SP
export FIT_SPIRAL_CONFIG_OVERRIDES='{"z_begin":9000,"z_end":10000,"input_disable_patches":true,"loss_weight_shell_outer":0,"loss_weight_shell_patch_radius":0,"dense_spacing_mode":"phase","track_crossing_mode":"count","optimizer_num_training_steps":30000,"output_save_png_visualizations":true}'
export FIT_SPIRAL_OUT_DIR=$D/spiral-output-old FIT_SPIRAL_CACHE_DIR=/mnt/nvme/scroll-prizes/cache/spiral-old FIT_SPIRAL_RUN_TAG=$TAG CUDA_VISIBLE_DEVICES=$GPU
mkdir -p $FIT_SPIRAL_OUT_DIR $FIT_SPIRAL_CACHE_DIR
echo "[$(date -Is)] start old-fitter fit $TAG on $GPU"; echo "overrides: $FIT_SPIRAL_CONFIG_OVERRIDES"; t0=$(date +%s)
~/.local/bin/uv run python fit_spiral.py --dataset $D/spiral-dataset-old > $S/fit-$TAG-full.log 2>&1; rc=$?
grep -E "^step [0-9]+: loss" $S/fit-$TAG-full.log | tail -1 | cut -c1-300
R=$(ls -td $FIT_SPIRAL_OUT_DIR/*${TAG}*/ 2>/dev/null | head -1); [ -n "$R" ] && python3 -I -c "import json,sys; s=json.load(open(sys.argv[1]))['summary']; print('satisfied_track_points_fraction', round(s['satisfied_track_points_fraction'],4), 'satisfied_tracks_fraction', round(s['satisfied_tracks_fraction'],4))" "$R/satisfaction_metrics_fitted.json" 2>/dev/null
echo "[$(date -Is)] fit $TAG done rc=$rc in $(( $(date +%s)-t0 ))s"; echo "FIT-EXIT: $rc"
