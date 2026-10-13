#!/bin/bash
# The agreement rule with each model's render-wide median reading - blind removed (--relative), on every set at d +1, so
# that PHerc0841 ag2814 (blind face globally brighter) is judged like the others (2026-10-13). CPU only; the maps exist.
# Writes relative/<canonical name>.tsv and relative/summary.txt. Marker RELATIVE-EXIT in run_relative.log.
S=/home/tbienapfl/scroll-prizes; R=$S/runs/2026-10-13_agreement-0841; O=$R/relative; PY="nice -n 19 $S/villa/vesuvius/.venv/bin/python -I"
MA=$S/bin/model_agreement.py; C=/mnt/nvme2/scroll-prizes/controls; D=/mnt/nvme/scroll-prizes/data; mkdir -p $O; cd $R
for n in ag2814 w00; do name=c0841_${n}_66
  $PY $MA $C/$name.zarr maps_$name $name 1 $O/agree_${name}_d1.tsv --boxes boxes_$name.json --label $name --relative; done
$PY $MA $D/PHerc0343/control/control343_66.zarr $D/PHerc0343/ink/control/maps control343_66 1 $O/343_d+1.tsv \
  --boxes $S/runs/2026-10-12_inkfirst-343/letter_boxes.json --label 343 --relative
N=$S/runs/2026-10-12_agreement-null
for z in $N/PHerc*_null.zarr; do n=$(basename $z .zarr)
  $PY $MA $z $N/maps_$n $n 1 $O/agree_${n}_d1.tsv --window $(cat $N/$n.window) --label $n --relative; done
W=$S/runs/2026-10-12_deeplook-0813-w079
WIN=$($PY -c "
import csv; r = list(csv.DictReader(open('$S/runs/2026-10-12_model-agreement/w079_d1.tsv'), delimiter='\t'))
y0 = min(int(x['y']) for x in r); x0 = min(int(x['x']) for x in r); y1 = max(int(x['y']) + int(x['h']) for x in r); x1 = max(int(x['x']) + int(x['w']) for x in r)
print(y0, x0, y1 - y0, x1 - x0)")
$PY $MA $W/w079crop.zarr $W/maps w079crop 1 $O/w079_d1.tsv --window $WIN --label w079 --relative
$PY $R/summary.py $O > $O/summary.txt 2>&1; cat $O/summary.txt
echo "[$(date -Is)] RELATIVE-EXIT"
