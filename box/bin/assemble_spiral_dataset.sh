#!/usr/bin/env bash
# Research plan Phase B2: assemble a scroll's spiral-fit dataset (data/<scroll>/inputs/spiral-dataset/) from the inputs mirrored
# into data/<scroll>/source/: links to the tracks and Lasagna stores, spiral-scroll.json, an umbilicus from the published normal
# grids (vc_gen_umbilicus, every 16th slice, 5 seeded repeats, then smooth_umbilicus.py, as for PHerc0191), a ray audit of the
# umbilicus on one CT slice with a preview image, and the resident pools (normals + grad_mag, group 2, CT-masked at group 2).
# Usage: assemble_spiral_dataset.sh <scroll> <audit z> [left_handed=false] [z_top_to_bottom=false] [um=9.362]
# Marker: ASSEMBLE-EXIT (0 when the umbilicus and the resident pools exist).
set -uo pipefail
SC=$1; ZA=$2; LH=${3:-false}; ZTB=${4:-false}; UM=${5:-9.362}
D=/mnt/nvme/scroll-prizes/data/$SC; SRC=$D/source; S=$D/inputs/spiral-dataset; B=~/scroll-prizes/bin
PYV=~/scroll-prizes/villa/vesuvius/.venv/bin/python; export PATH=$HOME/.local/bin:$PATH
VOL=$(ls -d $SRC/volume/*.zarr | head -1); LA=$(ls -d $SRC/lasagna/*/ | head -1); TR=$(ls -d $SRC/tracks/*/tracks | head -1)
read NZ NY NX <<< "$(python3 -c "import json; print(*json.load(open('$VOL/0/.zarray'))['shape'])")"
echo "[$(date -Is)] $SC: volume $NZ x $NY x $NX, lasagna $LA, tracks $TR"
mkdir -p $S/tracks $S/lasagna_inputs $S/qa
for f in $TR/*; do ln -sfn $f $S/tracks/; done
for k in nx ny grad_mag; do ln -sfn ${LA%/}/${SC}_$k.ome.zarr $S/lasagna_inputs/; done
DBM=$(cd $S/tracks && ls *.dbm | head -1)
cat > $S/spiral-scroll.json <<EOF
{
  "schema_version": 1,
  "name": "$SC",
  "voxel_size_um": $UM,
  "z_direction_is_top_to_bottom": $ZTB,
  "left_handed_coordinates": $LH,
  "normal_zarr_group": "2",
  "lasagna_scale": 4,
  "paths": {
    "tracks_dbm": "tracks/$DBM",
    "normal_x": "lasagna_inputs/${SC}_nx.ome.zarr",
    "normal_y": "lasagna_inputs/${SC}_ny.ome.zarr",
    "gradient_magnitude": "lasagna_inputs/${SC}_grad_mag.ome.zarr"
  }
}
EOF
if [ ! -s $S/umbilicus_raw.json ]; then
  echo "[$(date -Is)] vc_gen_umbilicus (every 16th slice, 5 repeats, seed 1)"; t0=$(date +%s)
  nice -n 5 vc_gen_umbilicus -i $SRC/normal-grids -o $S/umbilicus_raw.json --csv $S/umbilicus_estimates.csv --slices 0:$NZ:16 \
    --repeats 5 --threads 4 --seed 1 --volume $VOL --voxelsize-um $UM --volume-width $NX --volume-height $NY --volume-slices $NZ 2>&1 | tail -3
  echo "[$(date -Is)] umbilicus done in $(( $(date +%s)-t0 ))s"
fi
python3 -I $B/smooth_umbilicus.py $S/umbilicus_raw.json $S/umbilicus.json || { echo "ASSEMBLE-EXIT: 1"; exit 1; }
echo "[$(date -Is)] ray audit at z $ZA (level 2) with the smoothed umbilicus"
$PYV -I $B/ray_peaks.py $VOL $ZA --level 2 --rays 12 --umbilicus $S/umbilicus.json 2>&1 | tail -15
$PYV -I - "$VOL" "$S" "$ZA" "$UM" <<'PY'
import json, sys, numpy as np, zarr
from PIL import Image
V, S, z, um = sys.argv[1], sys.argv[2], int(sys.argv[3]), float(sys.argv[4])
img = np.asarray(zarr.open(V, mode="r")["2"][z // 4]).astype(np.float32)
def at(f):
    c = sorted(json.load(open(f))["control_points"], key=lambda p: p["z"]); zs = [p["z"] for p in c]
    return np.interp(z, zs, [p["x"] for p in c]) / 4, np.interp(z, zs, [p["y"] for p in c]) / 4
cx, cy = at(f"{S}/umbilicus.json"); rx, ry = at(f"{S}/umbilicus_raw.json")
lo, hi = np.percentile(img[img > 0], [1, 99.5]); out = np.clip((img - lo) / (hi - lo), 0, 1) * 255
def cross(x, y, v, r=40, t=3):
    x, y = int(round(x)), int(round(y)); out[max(0, y - t):y + t, max(0, x - r):x + r] = v; out[max(0, y - r):y + r, max(0, x - t):x + t] = v
cross(cx, cy, 255); cross(rx, ry, 0, r=25, t=2)
yy, xx = np.ogrid[:out.shape[0], :out.shape[1]]; out[np.abs(np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) - 1500 / um / 4) < 1.5] = 255
Image.fromarray(out[::2, ::2].astype(np.uint8)).save(f"{S}/qa/umbilicus_z{z}.png")
print(f"preview {S}/qa/umbilicus_z{z}.png: smoothed (white) ({cx*4:.0f},{cy*4:.0f}), raw (black) ({rx*4:.0f},{ry*4:.0f}) full-res")
PY
echo "[$(date -Is)] pack_resident_pools (normals + grad_mag, group 2 = 4x, CT-masked at group 2)"; t0=$(date +%s)
cd ~/scroll-prizes/villa/spiral-fitting && nice -n 5 ~/.local/bin/uv run python pack_resident_pools.py "$S/lasagna_inputs" --what normals,grad_mag \
  --normal-group 2 --ct "$VOL" --ct-group 2 --io-threads 16 --verify 2000 2>&1 | tail -8
echo "packed in $(( $(date +%s)-t0 ))s; sidecars: $(ls -d $S/lasagna_inputs/*respool* 2>/dev/null | xargs -rn1 basename | tr '\n' ' ')"
ok=1; [ -s $S/umbilicus.json ] && ls -d $S/lasagna_inputs/*respool_g2_pair >/dev/null 2>&1 && ok=0
echo "ASSEMBLE-EXIT: $ok"
