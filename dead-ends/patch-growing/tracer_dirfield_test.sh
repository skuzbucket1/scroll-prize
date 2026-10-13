#!/usr/bin/env bash
# After Fiber inference: re-test vc_grow_seg_from_seed WITH direction_fields (70 and 150 generations), then render+ink each patch.
set -uo pipefail; export PATH=$HOME/.local/bin:$PATH
D=/mnt/nvme/scroll-prizes/data/PHerc0191; F=$D/fiber/band8500-10500; G=$D/grow-test; mkdir -p $G/dirfield
until grep -q 'FIBER-EXIT' ~/scroll-prizes/fiber-band.log 2>/dev/null; do sleep 300; done
grep -q 'FIBER-EXIT: 0' ~/scroll-prizes/fiber-band.log || { echo "fiber inference failed"; echo "DIRTEST-EXIT: 90"; exit 1; }
cd ~/scroll-prizes/villa/vesuvius
# find the horizontal-direction group in the Fiber manifest (fallback: first group with 'dir' in its name or channels)
read ZARR SCALE <<<"$(python3 - "$F/fiber.lasagna.json" <<'PY'
import json, sys, os
m=json.load(open(sys.argv[1])); base=os.path.dirname(os.path.abspath(sys.argv[1])); groups=m.get("groups",{})
pick=None
for name,g in groups.items():
    if "horiz" in name.lower() or any("horiz" in str(c).lower() for c in g.get("channels",[])): pick=(name,g); break
if pick is None:
    for name,g in groups.items():
        if "dir" in name.lower() or any("dir" in str(c).lower() for c in g.get("channels",[])): pick=(name,g); break
if pick is None: pick=next(iter(groups.items()))
name,g=pick; z=g["zarr"]; z=z if os.path.isabs(z) else os.path.join(base,z)
import math; sd=g.get("scaledown",1); scale=int(round(math.log2(sd))) if sd>0 else 0
print(z, scale); print("groups:", {k:(v.get("zarr"),v.get("scaledown"),v.get("channels")) for k,v in groups.items()}, file=sys.stderr)
PY
)"
echo "direction field: $ZARR (scale $SCALE)"
SURF="https://vesuvius-challenge-open-data.s3.amazonaws.com/PHerc0191/representations/predictions/surfaces/20250821151635-surface-20260413222639-surface-m7-L0-th0.2.zarr"
for GEN in 70 150; do
  P=$G/dirfield/params_$GEN.json; python3 -c "import json; json.dump({'mode':'seed','cache_size':4000000000,'generations':$GEN,'thread_limit':4,'direction_fields':[{'zarr':'$ZARR','dir':'horizontal','scale':$SCALE}]}, open('$P','w'))"
  mkdir -p $G/dirfield/out_$GEN; t0=$(date +%s); vc_grow_seg_from_seed -v "$SURF" -t $G/dirfield/out_$GEN/ -p "$P" --seed 5259 2852 9404 > $G/dirfield/grow_$GEN.log 2>&1; rc=$?
  echo "[$(date -Is)] grow gen=$GEN rc=$rc in $(( $(date +%s)-t0 ))s: $(grep -E 'generated surface|discard' $G/dirfield/grow_$GEN.log | tail -1)"
  M=$(ls -d $G/dirfield/out_$GEN/auto_grown_* 2>/dev/null | tail -1); [ -n "$M" ] && ~/scroll-prizes/bin/patch_qa.sh "$M" "$G/dirfield/qa_$GEN" GPU-7937f33e-73c8-2a4f-d7c6-9c4c3c20c74f 2>&1 | grep -E 'geometry|selfcross|rendered|FAILED|PATCHQA'
done
echo "DIRTEST-EXIT: 0"
