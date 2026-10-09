#!/usr/bin/env bash
# After a fleet run with FETCH_MAPS=1: copy each segment's ink maps to the GPU box, run the stroke score there
# (bin/stroke_score.py, four models, every depth the segment has) and cross-check the AWS seed-42 maps against the box's
# own seed-42 maps of the same winding where they exist. Box output: data/strokes/aws/<w>/ and data/PHerc0191/aws-maps/<w>/.
# Usage: aws/fleet_score.sh            (all segments under data/aws-results/fleet/*/)
set -uo pipefail
HERE=$(cd "$(dirname "$0")" && pwd); ROOT=$(cd "$HERE/.." && pwd)
BOX=${BOX:-tbienapfl@100.74.214.106}; D=/mnt/nvme/scroll-prizes/data/PHerc0191; O=/mnt/nvme/scroll-prizes/data/strokes/aws
for md in "$ROOT"/data/aws-results/fleet/*/exp30k_snapped_w*/maps; do
  [ -d "$md" ] || continue
  name=$(basename "$(dirname "$md")"); w=${name##*_}
  ssh -o BatchMode=yes $BOX "mkdir -p $D/aws-maps/$w $O/$w"
  rsync -a -e "ssh -o BatchMode=yes" "$md/" "$BOX:$D/aws-maps/$w/" || { echo "$w: copy failed"; continue; }
  ssh -o BatchMode=yes $BOX "bash -s" <<SH
cd ~/scroll-prizes/villa/vesuvius
Z=$D/render66/${name}_66.zarr; M=$D/aws-maps/$w
for d in 0 1; do
  nice -n 19 .venv/bin/python ~/scroll-prizes/bin/stroke_score.py --surface \$Z --maps \$M --name ${name}_66 --out $O/$w \
    --um 9.362 --depth \$d --crops 3 2>&1 | python3 -c 'import sys, json
l = sys.stdin.read().split("} {", 1)
if len(l) < 2: print("$w d'\$d' failed:", l[0][-300:]); sys.exit()
s = json.loads("{" + l[1].rsplit("}", 1)[0] + "}"); r, b = s["reading"], s["blind"]
print("$w d%+d four-model area_R %.4f  R-B %+.4f  window %.4f/%.4f" % ('\$d', r["stroke_frac"], r["stroke_frac"] - b["stroke_frac"], r["window"].get("max", 0), b["window"].get("max", 0)))'
done
.venv/bin/python - <<'PY'
import os, numpy as np, tifffile
for s in (25, 26):
    for rev in ('_reverse', ''):
        f = 'exp30k_snapped_${w}_66__hybrid_3d2d-seed42__L66s%d%s.tif' % (s, rev)
        a, b = os.path.join('$D/aws-maps/$w', f), os.path.join('$D/ink-triage/maps', f)
        if not (os.path.isfile(a) and os.path.isfile(b)):
            continue
        x, y = tifffile.imread(a).astype(np.float32), tifffile.imread(b).astype(np.float32)
        if x.shape != y.shape:
            print('$w', f[-22:], 'shape', x.shape, y.shape); continue
        m = (x > 0) | (y > 0)
        print('$w s42 d%+d%s AWS vs box: r %.5f, max |diff| %d, identical %.1f %%' % (s - 25, rev or ' fwd', np.corrcoef(x[m], y[m])[0, 1],
              np.abs(x - y).max(), 100 * (x == y).mean()))
PY
SH
done
