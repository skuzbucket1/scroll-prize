#!/bin/bash
# Two gated follow-up fits on the pilot band (10k steps, bin/fit_experiment.sh):
#  exp-dirlow : waits WINDING-EXIT (GPU 3 free) — sym_dirichlet weight 10 -> 2.5 so the flow field can stretch
#               into the fat sectors; dense outer shell active at winding 125 (pilot's count), gap expander 130.
#  exp-wm     : waits EXPORT-EXIT: 0 (winding_inference store present) — dense_spacing_mode winding_model with the
#               same shell settings; first use of the winding-model supervision on this scroll.
S=~/scroll-prizes
exec >> $S/queue-after-winding.log 2>&1
until grep -q "WINDING-EXIT" $S/winding-band.log 2>/dev/null; do sleep 120; done
echo "[$(date -u +%FT%TZ)] WINDING-EXIT seen -> exp-dirlow on GPU-7937f33e"
setsid -f bash -c "$S/bin/fit_experiment.sh exp-dirlow GPU-7937f33e-73c8-2a4f-d7c6-9c4c3c20c74f '{\"loss_weight_sym_dirichlet\":2.5,\"input_use_outer_shell\":true,\"loss_weight_shell_outer\":1.0,\"shell_outer_winding_idx\":125,\"model_gap_expander_num_windings\":130,\"output_save_png_visualizations\":true}' > $S/fit-exp-dirlow.log 2>&1" > /dev/null 2>&1 < /dev/null
until grep -q "EXPORT-EXIT" $S/winding-band.log 2>/dev/null; do sleep 120; done
if grep -q "EXPORT-EXIT: 0" $S/winding-band.log; then
  echo "[$(date -u +%FT%TZ)] EXPORT-EXIT: 0 -> exp-wm on GPU-54088dd3"
  setsid -f bash -c "$S/bin/fit_experiment.sh exp-wm GPU-54088dd3-29fc-b2d3-0096-c5b75aea4345 '{\"dense_spacing_mode\":\"winding_model\",\"input_use_winding_inference\":true,\"input_use_outer_shell\":true,\"loss_weight_shell_outer\":1.0,\"shell_outer_winding_idx\":125,\"model_gap_expander_num_windings\":130,\"output_save_png_visualizations\":true}' > $S/fit-exp-wm.log 2>&1" > /dev/null 2>&1 < /dev/null
else
  echo "[$(date -u +%FT%TZ)] export failed; exp-wm not launched"
fi
echo "[$(date -u +%FT%TZ)] QUEUE-EXIT: 0"
