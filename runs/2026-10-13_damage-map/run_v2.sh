#!/bin/bash
# Damage map v0 (2026-10-13, plan B; Ted: map the cracks, holes and folds, then search the cleaner papyrus). Every tile of
# the known text (PHerc. 343 letter boxes; PHerc0841 ag2814 and w00 with human labels) and of every null winding of the
# triage evaluation (PHerc0813 exp30k-z12000, PHerc0191 exp30k-z11200), with the Reader v2 + d9v4C maps at d +1 (neither
# trained on these segments), then the report. CPU only, nice 19, two at a time.
# v2 (same day): holes = a dark surface (v1 asked for dark in 7 of 9 sheet layers and missed the thin voids seen by eye);
# outputs in tiles_v2/, png_v2/, report_v2.txt; then flags_check.py tiles_v2. Marker DAMAGE-V2-EXIT in run_v2.log.
S=/home/tbienapfl/scroll-prizes; R=$S/runs/2026-10-13_damage-map; B=$S/bin; D=/mnt/nvme/scroll-prizes/data; H=$D/controls9um/heldout
PY="nice -n 19 $S/villa/vesuvius/.venv/bin/python -I"
cd $R && mkdir -p tiles_v2 png_v2 logs
$PY $B/damage_map.py tiles $D/PHerc0343/control/control343_66.zarr $D/PHerc0343/ink/control/maps control343_66 8.64 tiles_v2/k_343.npz \
  --boxes $S/runs/2026-10-12_inkfirst-343/letter_boxes.json --png png_v2/343.jpg
$PY $B/damage_map.py tiles /mnt/nvme2/scroll-prizes/controls/c0841_ag2814_66.zarr $D/controls9um/c0841_ag2814/maps c0841_ag2814_66 9.366 \
  tiles_v2/k_0841_ag2814.npz --labels $H/0841-ag2814/labels.zarr --sup $H/0841-ag2814/supervision.zarr --png png_v2/0841_ag2814.jpg
$PY $B/damage_map.py tiles /mnt/nvme2/scroll-prizes/controls/c0841_w00_66.zarr $H/maps c0841_w00_66 9.366 \
  tiles_v2/k_0841_w00.npz --labels $H/0841-w00/labels.zarr --sup $H/0841-w00/supervision.zarr --png png_v2/0841_w00.jpg
# the null windings, from the triage evaluation's own list
$S/villa/vesuvius/.venv/bin/python -I - > jobs_v2.txt <<'EOF'
import json
cfg = json.load(open('/home/tbienapfl/scroll-prizes/runs/2026-10-12_triage-eval/rv2d9_ct.json'))
for it in cfg['nulls']:
    sc = 'PHerc0813' if '0813' in it['maps'] else 'PHerc0191'
    for w in it['windings']:
        print(f"{it['renders']}/{w}.zarr {it['maps']} {w} {it['um']} tiles_v2/n_{sc[5:]}_{w}.npz png_v2/{sc[5:]}_{w}.jpg")
EOF
xargs -P 2 -L 1 sh -c "$PY $B/damage_map.py tiles \$0 \$1 \$2 \$3 \$4 --png \$5 >> logs/tiles_v2.log 2>&1" < jobs_v2.txt
$PY $B/damage_map.py report report_v2 343=tiles_v2/k_343.npz 0841-ag2814=tiles_v2/k_0841_ag2814.npz 0841-w00=tiles_v2/k_0841_w00.npz \
  null:0813=$(ls tiles_v2/n_0813_*.npz | paste -sd,) null:0191=$(ls tiles_v2/n_0191_*.npz | paste -sd,)
$PY flags_check.py tiles_v2 > flags_check_v2.txt 2>&1
echo "[$(date -Is)] DAMAGE-V2-EXIT"
