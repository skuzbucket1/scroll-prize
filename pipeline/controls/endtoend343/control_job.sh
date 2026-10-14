#!/bin/bash
# End-to-end positive control (Ted 2026-10-13 ~8:30 pm CT: "add it on aws"): our own geometry recipe, exactly as on
# our search bands, on a scroll with known letters, then: which of OUR windings pass through the known
# letters in 3D (letters_on_windings.py), and do the letters show in OUR read of those windings (letters_eval.py)?
# Scroll parameters from the environment: SC, VN (volume), SN (m7 surface zarr), LN (Lasagna dir), UM, NZ NY NX, plus
# LETTERS (letters3d.npz from letters_to_3d.py) and READ_MODELS. Fixed order, resumable; marker CONTROL-EXIT.
# Usage: control_job.sh <z0> <z1> <fit-id>
set -uo pipefail
Z0=$1; Z1=$2; FIT=$3; : ${SC:?} ${VN:?} ${SN:?} ${LN:?} ${UM:?} ${NZ:?} ${NY:?} ${NX:?} ${LETTERS:?}; READ_MODELS=${READ_MODELS:-readerv2,d9v4c}
P=/opt/scroll/results/geometry; mkdir -p $P
log(){ echo "[$(date -u +%FT%TZ)] $*" | tee -a $P/progress.log; }
BOOT=$(date -d "$(head -1 /opt/scroll/bootstrap.times | awk '{print $3}')" +%s); MAXH=${MAX_HOURS:-12}
DEADLINE=$(( BOOT + MAXH * 3600 - 30 * 60 ))
left(){ echo $(( (DEADLINE - $(date +%s)) / 60 )); }
need(){ [ $(left) -ge $1 ] || { log "STOP before $2: $(left) min left, $1 needed"; finish 2; }; }
finish(){ log "CONTROL-EXIT: $1"; exit $1; }
export PATH=$HOME/.local/bin:$PATH

# 1. the box's layout, scratch on the instance-store NVMe
W=/opt/dlami/nvme/scroll; mkdir -p $W/{data,cache,scratch,tmp,bin}
sudo mkdir -p /mnt/nvme && sudo ln -sfn $W /mnt/nvme/scroll-prizes
ln -sfn /mnt/nvme/scroll-prizes ~/scroll-prizes; ln -sfn /opt/scroll/villa $W/villa
cp /opt/scroll/geom/bin/* $W/bin/ && chmod +x $W/bin/*.sh
for d in work cache tmp; do mkdir -p /opt/dlami/nvme/$d; [ -L /opt/scroll/$d ] || { rm -rf /opt/scroll/$d; ln -s /opt/dlami/nvme/$d /opt/scroll/$d; }; done
mkdir -p ~/.VC3D /opt/dlami/nvme/remote_cache
[ -L ~/.VC3D/remote_cache ] || { rm -rf ~/.VC3D/remote_cache; ln -s /opt/dlami/nvme/remote_cache ~/.VC3D/remote_cache; }
D=/mnt/nvme/scroll-prizes/data/$SC; SRC=$D/source; S=$D/inputs/spiral-dataset; G=$D/geometry/$FIT; mkdir -p $SRC $S/qa $G
log "start $SC $FIT z $Z0-$Z1; $(left) min to the deadline; GPU $(nvidia-smi --query-gpu=name --format=csv,noheader)"

# 2. spiral-fitting env
if [ ! -f /opt/scroll/spiral-env.ok ]; then
  (cd ~/scroll-prizes/villa/spiral-fitting && uv sync > $P/uv-spiral.log 2>&1 && uv run --no-sync python -c "import torch; assert torch.cuda.is_available()") \
    && touch /opt/scroll/spiral-env.ok || { log "spiral-fitting env FAILED (uv-spiral.log)"; finish 1; }
  log "spiral-fitting env ok"
fi

# 3. inputs, in-region (through the VPC's S3 gateway endpoint)
B=s3://vesuvius-challenge-open-data/$SC
aws configure set default.s3.max_concurrent_requests 64
cpq(){ aws s3 cp --no-sign-request --only-show-errors "$@"; }
if [ ! -f $SRC/inputs.ok ]; then
  V=$SRC/volume/$VN
  for f in .zattrs .zgroup metadata.json 0/.zarray 1/.zarray; do cpq $B/volumes/$VN/$f $V/$f; done
  for l in 2 3 4 5; do cpq --recursive $B/volumes/$VN/$l/ $V/$l/; done
  M=$SRC/surface-m7/$SN
  for f in .zattrs .zgroup 0/.zarray 1/.zarray; do cpq $B/representations/predictions/surfaces/$SN/$f $M/$f; done
  for r in $(seq $(( Z0 / 192 > 0 ? Z0 / 192 - 1 : 0 )) $(( (Z1 - 1) / 192 + 1 ))); do cpq --recursive $B/representations/predictions/surfaces/$SN/0/$r/ $M/0/$r/; done
  L=$SRC/lasagna/$LN; cpq $B/representations/predictions/lasagna/$LN/$SC.lasagna.json $L/$SC.lasagna.json
  for k in nx ny grad_mag; do Z=${SC}_$k.ome.zarr
    for f in .zattrs .zgroup 0/.zarray 1/.zarray 2/.zarray 3/.zarray 4/.zarray; do cpq $B/representations/predictions/lasagna/$LN/$Z/$f $L/$Z/$f 2>/dev/null; done
    for l in 2 3 4; do cpq --recursive $B/representations/predictions/lasagna/$LN/$Z/$l/ $L/$Z/$l/; done
  done
  touch $SRC/inputs.ok; log "inputs: $(du -sh $SRC | cut -f1)"
fi

# 3b. umbilicus over the band (+-256 slices), same command as at home, in the background while the tracks use the GPU
NG=$SRC/normal-grids; U0=$(( Z0 > 256 ? Z0 - 256 : 0 )); U1=$(( Z1 + 256 < NZ ? Z1 + 256 : NZ ))
if [ ! -s $S/umbilicus_raw.json ] && [ ! -f $P/umb.started ]; then
  aws s3 cp --no-sign-request --only-show-errors --recursive $B/representations/predictions/surfaces/${SN%.zarr}.normal-grids/ $NG/
  touch $P/umb.started; log "umbilicus started, slices $U0-$U1"
  ( QT_QPA_PLATFORM=offscreen /opt/scroll/vc3d/AppRun vc_gen_umbilicus -i $NG -o $S/umbilicus_raw.tmp.json \
      --csv $S/umbilicus_estimates.csv --slices $U0:$U1:16 --repeats 5 --threads 12 --seed 1 --volume $SRC/volume/$VN \
      --voxelsize-um $UM --volume-width $NX --volume-height $NY --volume-slices $NZ > $P/umbilicus.log 2>&1 \
    && mv $S/umbilicus_raw.tmp.json $S/umbilicus_raw.json \
    && python3 -I ~/scroll-prizes/bin/smooth_umbilicus.py $S/umbilicus_raw.json $S/umbilicus.json >> $P/umbilicus.log 2>&1 \
    && echo ok > $P/umb.done || echo failed > $P/umb.done ) &
fi

# 4. tracks over the band (the organisers' PHerc0813 extraction parameters)
T=$SRC/tracks/$FIT/tracks; DBM=$T/${SC}_${SN%%-surface-*}_surface_m7_L0_th0.2.dbm; mkdir -p $T
if [ ! -f $T/tracks.ok ]; then
  need 300 tracks
  cd ~/scroll-prizes/villa/spiral-fitting
  sed -e 's/^downsample_factor = .*/downsample_factor = 2/' -e 's/^z_chunk_depth_h = .*/z_chunk_depth_h = 2/' \
      -e 's/^z_chunk_stride_h = .*/z_chunk_stride_h = 8/' -e 's/^yx_chunk_thickness_v = .*/yx_chunk_thickness_v = 4/' \
      -e 's/^yx_stride_v = .*/yx_stride_v = 16/' extract_surface_tracks.py > extract_surface_tracks_0813params.py
  t0=$(date +%s)
  uv run --no-sync python extract_surface_tracks_0813params.py --predictions $SRC/surface-m7/$SN/0 --out $DBM \
    --z-min $Z0 --z-max $Z1 --backend gpu --gpus 0 > $P/tracks.log 2>&1 || { log "tracks FAILED (tracks.log)"; finish 1; }
  log "tracks done in $(( ($(date +%s) - t0) / 60 )) min: $(du -sh $T | cut -f1)"
  uv run --no-sync python build_track_crossings.py $DBM --z-min $Z0 --z-max $Z1 > $P/crossings.log 2>&1 \
    && log "crossings sidecar built" || log "crossings sidecar not built (optional)"
  touch $T/tracks.ok
fi

# 5. dataset (waits for the umbilicus)
until [ -s $S/umbilicus_raw.json ] && [ -s $S/umbilicus.json ]; do
  [ "$(cat $P/umb.done 2>/dev/null)" = failed ] && { log "umbilicus FAILED (umbilicus.log)"; finish 1; }
  need 240 assemble; sleep 60
done
if ! grep -q "ASSEMBLE-EXIT: 0" $P/assemble.log 2>/dev/null; then
  need 240 assemble
  bash ~/scroll-prizes/bin/assemble_spiral_dataset.sh $SC $(( (Z0 + Z1) / 2 )) false false $UM > $P/assemble.log 2>&1
  grep -q "ASSEMBLE-EXIT: 0" $P/assemble.log || { log "assemble FAILED (assemble.log)"; finish 1; }
  log "dataset assembled"
fi

# 6. fit (exp-30k)
if ! grep -q "FIT-EXIT: 0" $P/fit.log 2>/dev/null; then
  need 210 fit
  bash ~/scroll-prizes/bin/fit_band.sh $SC $FIT 0 $Z0 $Z1 30000 > $P/fit.log 2>&1
  grep -q "FIT-EXIT: 0" $P/fit.log || { log "fit FAILED (fit.log)"; finish 1; }
  log "fit: $(grep satisfied $P/fit.log | tail -1)"
fi

# 7. snap (the non-spliced meshes only: the spliced ones are not flattened downstream)
if ! grep -q "SNAP-EXIT: 0" $P/snap.log 2>/dev/null; then
  need 30 snap
  SNAP_PROCS=4 SNAP_SKIP_SPLICED=1 bash ~/scroll-prizes/bin/snap_band.sh $SC $FIT $Z0 $Z1 > $P/snap.log 2>&1
  grep -q "SNAP-EXIT: 0" $P/snap.log || { log "snap FAILED (snap.log)"; finish 1; }
  log "snap: $(grep -E 'windings|frac' $P/snap.log | tail -1)"
fi

# 8. flatten the windings with >= 50 % on the sheet (lower than the bands' 70 %, so a letter winding is not lost to the filter)
L=$P/flatten_list.txt
python3 -I - $G/snapped/snap_report.tsv $G/snapped > $L <<'PY'
import csv, os, sys
rows = [r for r in csv.DictReader(open(sys.argv[1]), delimiter='\t')
        if 'spliced' not in r['winding'] and float(r['frac_with_sheet']) >= 0.5 and os.path.isdir(os.path.join(sys.argv[2], r['winding']))]
rows.sort(key=lambda r: -int(r['n_valid']) * float(r['frac_with_sheet']))
for r in rows:
    print(r['winding'].split('_')[0], os.path.join(sys.argv[2], r['winding']))
PY
log "flatten $(grep -c . $L) windings (>= 50 % on the sheet; the search bands keep >= 70 %: the eval reports each letter winding's share)"
flat(){ local w=$1 src=$2 o=$G/flattened/$1; [ -f $o/tifxyz/flatten.tifxyz/x.tif ] && return 0
  [ $(left) -ge 60 ] || return 0
  bash ~/scroll-prizes/bin/flatten_winding.sh $src $o 0 > /dev/null 2>&1 || true; }
export -f flat left; export G DEADLINE
t0=$(date +%s); xargs -P 3 -L 1 bash -c 'flat "$0" "$1"' < $L
n=$(ls -d $G/flattened/*/tifxyz/flatten.tifxyz 2>/dev/null | wc -l); log "flattened $n windings in $(( ($(date +%s) - t0) / 60 )) min"

# 9. which of our flattened windings pass through the known letters (normal offset <= 4 voxels)?
PY=/opt/scroll/villa/vesuvius/.venv/bin/python
$PY -I /opt/scroll/geom/letters_on_windings.py $LETTERS $G/flattened $P/letters_hits.tsv > $P/letters_hits.log 2>&1
log "letters on our windings: $(head -4 $P/letters_hits.tsv | tail -3 | tr '\t\n' ' |')"
# 10. read the (up to 4) windings that carry the most letter samples, at d 0 and +1
U=https://vesuvius-challenge-open-data.s3.us-east-1.amazonaws.com/$SC/volumes/$VN
mkdir -p /opt/scroll/jobs; : > /opt/scroll/jobs/batch.tsv
tail -n +2 $P/letters_hits.tsv | awk -F'\t' '$2 >= 50' | head -4 | while IFS=$'\t' read -r w n rest; do
  printf '%s_%s\t%s\t%s\t%s\t%s\t0,1\n' $FIT $w $G/flattened/$w/tifxyz/flatten.tifxyz $U $UM $READ_MODELS >> /opt/scroll/jobs/batch.tsv; done
log "read $(grep -c . /opt/scroll/jobs/batch.tsv) windings ($READ_MODELS, d 0 and +1)"
KEEP_RENDERS=1 GROUP_IDX=0 bash /opt/scroll/bin/run_batch.sh > $P/batch.log 2>&1
# 11. do the letters show in our read? (reading vs other face, at the letters vs elsewhere; image with the letter positions)
$PY -I /opt/scroll/geom/letters_eval.py $LETTERS $G/flattened /opt/scroll/results $FIT $READ_MODELS $P/eval > $P/eval.log 2>&1
log "eval: $(tail -6 $P/eval.log | tr '\n' '|')"
finish 0
