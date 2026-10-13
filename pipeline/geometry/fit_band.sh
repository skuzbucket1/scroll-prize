#!/usr/bin/env bash
# Spiral fit of one z band of any scroll with our best recipe (exp-30k: tracks only, grad_mag spacing, no outer shell, 30k steps).
# Dataset: data/<scroll>/inputs/spiral-dataset (assemble_spiral_dataset.sh). Output: data/<scroll>/geometry/<fit-id>/fit-runs/<run>/,
# linked as geometry/<fit-id>/fit. Usage: fit_band.sh <scroll> <fit-id> <CUDA GPU UUID> <z0> <z1> [steps=30000]
# Marker: FIT-EXIT.
set -uo pipefail
SC=$1; FIT=$2; GPU=$3; Z0=$4; Z1=$5; STEPS=${6:-30000}
case "$GPU" in 1|GPU-33b8aac6*) echo "REFUSED: GPU 1 (GTX 1660 SUPER) is not usable for this work" >&2; exit 97;; esac
D=/mnt/nvme/scroll-prizes/data/$SC; S=$D/inputs/spiral-dataset; G=$D/geometry/$FIT; mkdir -p $G/fit-runs
cd ~/scroll-prizes/villa/spiral-fitting
WANT='{"z_begin":'$Z0',"z_end":'$Z1',"optimizer_num_training_steps":'$STEPS',"input_use_verified_patches":false,"input_use_tracks":true,"input_use_outer_shell":false,"input_use_winding_inference":false,"input_use_fibers":false,"input_use_pcl_absolute":false,"input_use_pcl_relative":false,"input_use_pcl_same_winding":false,"input_use_pcl_drawn_control_points":false,"dense_spacing_mode":"grad_mag","loss_weight_shell_outer":0,"output_save_png_visualizations":true}'
export FIT_SPIRAL_CONFIG_OVERRIDES=$(python3 -c '
import json,re,sys; want=json.loads(sys.argv[1]); src=open("config.py").read()
keep={k:v for k,v in want.items() if re.search(r"[\x22\x27]%s[\x22\x27]|self\.%s\b" % (k,k), src)}
print(json.dumps(keep)); print("dropped unknown keys:", [k for k in want if k not in keep], file=sys.stderr)' "$WANT")
echo "overrides: $FIT_SPIRAL_CONFIG_OVERRIDES"
export FIT_SPIRAL_OUT_DIR=$G/fit-runs FIT_SPIRAL_CACHE_DIR=/mnt/nvme/scroll-prizes/cache/spiral-$SC FIT_SPIRAL_RUN_TAG=$FIT CUDA_VISIBLE_DEVICES=$GPU
export TMPDIR=/mnt/nvme/scroll-prizes/scratch
echo "[$(date -Is)] start fit $SC $FIT (z $Z0-$Z1, $STEPS steps) on $GPU"; t0=$(date +%s)
~/.local/bin/uv run python fit_spiral.py --dataset "$S" > $G/fit-full.log 2>&1; rc=$?
grep -E "^step [0-9]+: loss" $G/fit-full.log | tail -2 | cut -c1-160
R=$(ls -td $G/fit-runs/*/ 2>/dev/null | head -1)
if [ -n "$R" ]; then
  ln -sfn ${R%/} $G/fit
  python3 -c "import json; s=json.load(open('$R/satisfaction_metrics_fitted.json'))['summary']; print('satisfied_track_points_fraction', round(s['satisfied_track_points_fraction'],4), 'satisfied_tracks_fraction', round(s['satisfied_tracks_fraction'],4))" 2>/dev/null
fi
echo "[$(date -Is)] fit $FIT done rc=$rc in $(( $(date +%s)-t0 ))s"; echo "FIT-EXIT: $rc"
