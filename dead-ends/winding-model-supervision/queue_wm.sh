#!/bin/bash
# exp-wm: first fit with winding-model supervision; waits for the export of the winding cache.
S=~/scroll-prizes
exec >> $S/queue-after-winding.log 2>&1
until grep -q "EXPORT-EXIT" $S/winding-band.log 2>/dev/null; do sleep 120; done
if grep -q "EXPORT-EXIT: 0" $S/winding-band.log; then
  echo "[$(date -u +%FT%TZ)] EXPORT-EXIT: 0 -> exp-wm on GPU-54088dd3"
  setsid -f bash -c "$S/bin/fit_experiment.sh exp-wm GPU-54088dd3-29fc-b2d3-0096-c5b75aea4345 '{\"dense_spacing_mode\":\"winding_model\",\"input_use_winding_inference\":true,\"input_use_outer_shell\":true,\"loss_weight_shell_outer\":1.0,\"shell_outer_winding_idx\":125,\"model_gap_expander_num_windings\":130,\"output_save_png_visualizations\":true}' > $S/fit-exp-wm.log 2>&1" > /dev/null 2>&1 < /dev/null
else
  echo "[$(date -u +%FT%TZ)] export failed; exp-wm not launched"
fi
echo "[$(date -u +%FT%TZ)] QUEUE-EXIT: 0"
