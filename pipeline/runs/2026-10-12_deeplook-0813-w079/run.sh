#!/bin/bash
# Deep look at Ted's pick PHerc0813 exp30k-z12000 w079, window 1 (Ted approved 2026-10-12 7:35 pm CT; home GPU 0, free):
# the upper-left cluster in reading orientation (render y 941 x 8060, 14 x 8 mm), the one spot of his six whose bright
# marks sit on one sheet only (neighbour_view.py). Crop of the 66-layer render with a 256 px margin, then all six models
# (Nieuwlaar's four + Reader v2 + d9v4C) at every depth d -15..+15 (bin/depth_sweep.sh), then the figures
# (bin/deep_look_view.py). Markers in run.log: CROP-DONE, SWEEP-EXIT, DEEPLOOK-EXIT.
S=~/scroll-prizes; R=$S/runs/2026-10-12_deeplook-0813-w079; PY=$S/villa/vesuvius/.venv/bin/python
P=/mnt/nvme/scroll-prizes/data/PHerc0813; GPU=GPU-2d9651e9-5a94-e0cb-6a99-9300d8056524
Y0=685; Y1=2020; X0=7804; X1=9811                               # window y 941-1795, x 8060-9555 plus 256 px (clipped)
mkdir -p $R
[ -d $R/w079crop.zarr/0 ] || $PY - <<EOF
import zarr, numpy as np
src = zarr.open('$P/renders/exp30k-z12000/w079.zarr', mode='r')['0']
a = np.asarray(src[:, $Y0:$Y1, $X0:$X1])
g = zarr.open_group('$R/w079crop.zarr', mode='w', zarr_format=2)
g.create_array('0', shape=a.shape, chunks=(66, 256, 256), dtype='u1', fill_value=0)[:] = a
print('crop', a.shape, 'nonzero', float((a > 0).mean()))
EOF
echo "[$(date -Is)] CROP-DONE y $Y0-$Y1 x $X0-$X1"
MODELS="dnative hybrid_3d2d-seed42 hybrid_3d2d-seed43 hecate readerv2 d9v4c" bash $S/bin/depth_sweep.sh $R/w079crop.zarr $R/maps $GPU -15 15 > $R/sweep.log 2>&1
echo "[$(date -Is)] SWEEP-EXIT: $(tail -1 $R/sweep.log)"
[ -f $S/bin/deep_look_view.py ] && nice -n 5 $PY $S/bin/deep_look_view.py $R/w079crop.zarr $R/maps $R/view --label "PHerc0813 w079 (Ted's pick, window 1)" \
  --um 9.362 > $R/view.log 2>&1
echo "[$(date -Is)] DEEPLOOK-EXIT"
