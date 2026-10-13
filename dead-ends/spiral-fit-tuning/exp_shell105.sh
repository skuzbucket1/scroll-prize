#!/bin/bash
# Experiment: grad_mag fit of the pilot band WITH the real outer shell (from make_outer_shell.py)
# and the ray-audit winding count (shell_outer_winding_idx 105 instead of the default 130).
# Gated on SHELL-EXIT: 0. Runs on GPU index 2 (RTX 3060 Ti, otherwise idle). Log: fit-exp-shell105.log
until grep -q "SHELL-EXIT: 0" ~/scroll-prizes/outer-shell.log 2>/dev/null; do sleep 60; done
GPU=$(nvidia-smi --query-gpu=index,uuid --format=csv,noheader | awk -F', ' '$1==2{print $2}')
echo "shell ready; GPU index 2 = $GPU" > ~/scroll-prizes/fit-exp-shell105.log
~/scroll-prizes/bin/fit_experiment.sh exp-shell105 "$GPU" \
  '{"input_use_outer_shell":true,"loss_weight_shell_outer":1.0,"shell_outer_winding_idx":105,"shell_outer_winding_margin":10,"model_gap_expander_num_windings":110,"output_save_png_visualizations":true}' \
  >> ~/scroll-prizes/fit-exp-shell105.log 2>&1
