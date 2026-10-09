#!/bin/bash
# 1) dense (dz=1) outer shell for the pilot band z 8500-10500 -> swap into spiral-dataset/outer_shell
# 2) rerun the shell experiment (exp-shell105b) on GPU 2 with the dense shell
# 3) build the full-scroll dz=1 shell in the background -> outer_shell_dz1 (swap manually later)
S=~/scroll-prizes; D=$S/data/PHerc0191; SD=$D/spiral-dataset
VOL=$(ls -d $D/volumes/*.zarr | head -1)
PY=$S/villa/vesuvius/.venv/bin/python
exec >> $S/shell-dense.log 2>&1
echo "[$(date -u +%FT%TZ)] band dz=1 shell"
$PY -I $S/bin/make_outer_shell.py $VOL $SD/umbilicus.json $SD/outer_shell_band8500-10500 --level 2 --dz 1 --z-begin 8500 --z-end 10500 || { echo "SHELLBAND-EXIT: $?"; exit 1; }
[ -d $SD/outer_shell_dz8 ] || mv $SD/outer_shell $SD/outer_shell_dz8
rm -rf $SD/outer_shell; cp -r $SD/outer_shell_band8500-10500 $SD/outer_shell
echo "[$(date -u +%FT%TZ)] SHELLBAND-EXIT: 0 (outer_shell now = band dz1; dz8 kept as outer_shell_dz8)"
GPU=$(nvidia-smi --query-gpu=index,uuid --format=csv,noheader | awk -F', ' '$1==2{print $2}')
setsid -f bash -c "$S/bin/fit_experiment.sh exp-shell105b $GPU '{\"input_use_outer_shell\":true,\"loss_weight_shell_outer\":1.0,\"shell_outer_winding_idx\":105,\"shell_outer_winding_margin\":10,\"model_gap_expander_num_windings\":110,\"output_save_png_visualizations\":true}' > $S/fit-exp-shell105b.log 2>&1" > /dev/null 2>&1 < /dev/null
echo "[$(date -u +%FT%TZ)] launched exp-shell105b on $GPU"
echo "[$(date -u +%FT%TZ)] full dz=1 shell"
$PY -I $S/bin/make_outer_shell.py $VOL $SD/umbilicus.json $SD/outer_shell_dz1 --level 2 --dz 1
echo "[$(date -u +%FT%TZ)] SHELLDZ1-EXIT: $?"
