#!/usr/bin/env bash
# Phase 1: assemble the PHerc0191 spiral dataset once inputs land — umbilicus from the published normal grids, resident pools from the lasagna stores.
set -uo pipefail
D=/mnt/nvme/scroll-prizes/data/PHerc0191; S=$D/spiral-dataset; VOL=$D/volumes/20250821151635-9.362um-1.2m-113keV-masked.zarr
export PATH=$HOME/.local/bin:$PATH
wait_marker() { until grep -qE "$2" "$1" 2>/dev/null; do sleep 60; done; }
wait_marker "$D/mirror-normalgrids.log" 'MIRROR-EXIT: 0'
for st in nx ny grad_mag; do wait_marker "$D/mirror-lasagna-v2-PHerc0191_$st.log" 'MIRROR-EXIT: 0'; done
wait_marker "$D/mirror-volume.log" '^== level 1'     # CT level 2 fully mirrored (needed for --ct masking of the pools)
echo "[$(date -Is)] inputs ready"
if [ ! -s "$S/umbilicus.json" ]; then
  echo "[$(date -Is)] vc_gen_umbilicus (every 16th slice, 3 repeats, seeded)"; t0=$(date +%s)
  vc_gen_umbilicus -i "$D/normal-grids" -o "$S/umbilicus.json" --csv "$S/umbilicus_estimates.csv" --slices 0:18977:16 --repeats 5 --threads 4 --seed 1 \
    --volume "$VOL" --voxelsize-um 9.362 --volume-width 8387 --volume-height 8387 --volume-slices 18977 2>&1 | tail -5
  echo "umbilicus: $(python3 -c "import json; d=json.load(open('$S/umbilicus.json')); print(len(d.get('control_points',[])), 'control points')" 2>&1) in $(( $(date +%s)-t0 ))s"
fi
echo "[$(date -Is)] pack_resident_pools (normals + grad_mag, group 2 = 4x, CT-masked at group 2)"; t0=$(date +%s)
cd ~/scroll-prizes/villa/spiral-fitting && ~/.local/bin/uv run python pack_resident_pools.py "$S/lasagna_inputs" --what normals,grad_mag --normal-group 2 --ct "$VOL" --ct-group 2 --io-threads 16 --verify 2000 2>&1 | tail -8
echo "packed in $(( $(date +%s)-t0 ))s; sidecars: $(ls -d $S/lasagna_inputs/*respool* $D/lasagna/*/*respool* 2>/dev/null | xargs -rn1 basename | tr '\n' ' ')"
ok=1; [ -s "$S/umbilicus.json" ] && ls -d $S/lasagna_inputs/*respool_g2_pair >/dev/null 2>&1 && ok=0
du -sh $S/lasagna_inputs/ $D/lasagna/ 2>/dev/null | tr '\n' ' '; echo; echo "ASSEMBLE-EXIT: $ok"
