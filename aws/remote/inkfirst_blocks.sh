#!/usr/bin/env bash
# Ink first over a list of blocks of one scroll, on an AWS worker or the GPU box. For each block: fetch the CT and the
# surface-prediction block from the public bucket, cut patches along the sheets (CPU; PAR blocks at once), ink them
# (GPU; one block at a time, as soon as it is cut), stitch, keep a small summary (inkfirst_block_summary.py) and a glow
# figure, then delete the big inputs. Resumable: a block with DONE (or EMPTY) is skipped.
# Usage: inkfirst_blocks.sh <blocks.tsv> <CT zarr URL> <prediction zarr URL> <um> <models,> [stride=96] [size=256] [par=4]
# Env: MAX_QUEUED (cut blocks waiting for the GPU, default 2), NO_GLOW=1 (delete the CT and prediction blocks after
#      cutting; no per-block glow figure), SPLIT_ABOVE (ink mosaics of more patches in quarters; 1100 suits a 12 GB home GPU, 2500 an A10G/L4),
#      ROOT (/opt/scroll), PY, VILLA (villa checkout), BIN (scripts: ink343/, ink-first-src/, inkfirst_block_summary.py,
#      viz_glow.py), CKPT_DIR, WORK, RESULTS, CUDA_VISIBLE_DEVICES. Marker in RESULTS/progress.log: BLOCKS-EXIT.
set -uo pipefail
BL=$1; CT=$2; PRED=$3; UM=$4; MODELS=$5; STRIDE=${6:-96}; SIZE=${7:-256}; PAR=${8:-4}
ROOT=${ROOT:-/opt/scroll}; PY=${PY:-$ROOT/villa/vesuvius/.venv/bin/python}; VILLA=${VILLA:-$ROOT/villa}; BIN=${BIN:-$ROOT/bin}
W=${WORK:-$ROOT/work/inkfirst}; R=${RESULTS:-$ROOT/results/inkfirst}; mkdir -p $W $R
export CKPT_DIR=${CKPT_DIR:-$ROOT/ckpt343} PY N_LAYERS=66 NATIVE_UM=$UM VILLA_BATCH=${VILLA_BATCH:-8} TMPDIR=${TMPDIR:-$ROOT/tmp}
mkdir -p $TMPDIR; IF="env PYTHONPATH=$BIN/ink-first-src $PY -m ink_first.cli"
log(){ echo "[$(date -u +%FT%TZ)] $*" | tee -a $R/progress.log; }
[ -f $R/timings.tsv ] || printf 'id\tpatches\tfetch_s\tsample_s\tink_s\tsummary_s\n' > $R/timings.tsv

cut_block(){   # id z0 z1 y0 y1 x0 x1: fetch + sample, then SAMPLED (or EMPTY)
  local id=$1; shift; local B="$*"; local D=$W/$id O=$R/$id
  [ -f $O/DONE ] || [ -f $O/EMPTY ] || [ -f $D/SAMPLED ] && return 0
  # backpressure: the GPU inks one block at a time; don't let cut blocks pile up on disk (each mosaic is GBs)
  while [ "$(ls $W/*/SAMPLED 2>/dev/null | wc -l)" -ge "${MAX_QUEUED:-2}" ]; do sleep 15; done
  mkdir -p $D $O
  local t0=$(date +%s)
  $IF fetch --url $CT --out $D/ct.zarr --box $B --threads 16 > $O/fetch.log 2>&1 &&
  $IF fetch --url $PRED --out $D/pred.zarr --box $B --threads 16 >> $O/fetch.log 2>&1 || { log "$id fetch FAILED"; rm -rf $D; return 1; }
  local t1=$(date +%s)
  nice -n 5 $IF sample --ct $D/ct.zarr --pred $D/pred.zarr --box $B --out $D/s --stride $STRIDE --size $SIZE > $O/sample.log 2>&1
  local rc=$? t2=$(date +%s)
  echo "$(( t1 - t0 )) $(( t2 - t1 ))" > $D/cut_seconds
  if [ $rc -ne 0 ] || [ ! -f $D/s/patches.npz ]; then
    grep -q "no sheet-like" $O/sample.log && { touch $O/EMPTY; rm -rf $D; log "$id empty (no sheet-like surface points)"; return 0; }
    log "$id sample FAILED rc=$rc"; rm -rf $D; return 1
  fi
  [ "${NO_GLOW:-0}" = 1 ] && rm -rf $D/ct.zarr $D/pred.zarr        # only the mosaic is needed from here on
  touch $D/SAMPLED; log "$id cut: $(grep -oE '[0-9]+ sheet-like points' $O/sample.log) (fetch $(( t1 - t0 )) s, sample $(( t2 - t1 )) s)"
}

ink_block(){   # id: ink every model (quarters for big mosaics), summary, glow figure, clean up, DONE
  local id=$1 D=$W/$1 O=$R/$1 t0 t1 n zmid
  t0=$(date +%s); n=$($PY -c "import numpy as np; print(len(np.load('$D/s/patches.npz')['rowcol']))")
  if [ "$n" -gt "${SPLIT_ABOVE:-1100}" ] && [ ! -d $D/s/q0 ]; then $IF split $D/s > $O/split.log 2>&1; fi   # quarters only for very big mosaics
  for m in ${MODELS//,/ }; do
    [ -s $D/s/maps/mosaic__${m}__L66s25_reverse.tif ] && continue
    if [ -d $D/s/q0 ]; then
      for q in $D/s/q[0-3]; do
        [ -s $q/maps/mosaic__${m}__L66s25_reverse.tif ] || (cd $VILLA/vesuvius && bash $BIN/ink343/run_ink.sh $q/mosaic.zarr $m 0 $q/maps >> $O/ink_$m.log 2>&1)
      done
      $IF stitch $D/s --model $m >> $O/ink_$m.log 2>&1
    else
      (cd $VILLA/vesuvius && bash $BIN/ink343/run_ink.sh $D/s/mosaic.zarr $m 0 $D/s/maps > $O/ink_$m.log 2>&1)
    fi
    [ -s $D/s/maps/mosaic__${m}__L66s25_reverse.tif ] || { log "$id ink $m FAILED"; rm -rf $D; return 1; }
  done
  t1=$(date +%s)
  $PY -I $BIN/inkfirst_block_summary.py $D/s $O $id $MODELS > $O/summary.log 2>&1 || { log "$id summary FAILED"; rm -rf $D; return 1; }
  zmid=$($PY -c "import numpy as np; b = np.load('$D/s/patches.npz')['box']; print((int(b[0]) + int(b[1])) // 2)")
  m1=${MODELS%%,*}
  [ -d $D/ct.zarr ] && MPLBACKEND=Agg $PY -I $BIN/viz_glow.py --text $D/ct.zarr $D/s/patches.npz $D/s/maps/mosaic__${m1}__L66s25.tif $zmid --text-label "$id" \
     --title "$id: ink first ($m1), z $zmid" --out $O/glow.png > $O/glow.log 2>&1 || log "$id glow figure failed (not fatal)"
  read fs ss < $D/cut_seconds
  printf '%s\t%s\t%s\t%s\t%s\t%s\n' $id $n $fs $ss $(( t1 - t0 )) $(( $(date +%s) - t1 )) >> $R/timings.tsv
  rm -f $D/SAMPLED; [ "${KEEP_BLOCKS:-0}" = 1 ] || rm -rf $D
  touch $O/DONE; log "$id done: $n patches, ink $(( t1 - t0 )) s"
}

export -f cut_block log; export IF W R CT PRED STRIDE SIZE PY
# cutters: PAR blocks at a time, in the background
tail -n +2 $BL | cut -f1-7 | xargs -P $PAR -L 1 bash -c 'cut_block "$@"' _ > $R/cutters.log 2>&1 &
CUTTERS=$!
log "start: $(( $(wc -l < $BL) - 1 )) blocks, models $MODELS, stride $STRIDE, size $SIZE, $PAR cutters"
# inker: whatever is cut, one block at a time, until the cutters are done and nothing is left
while true; do
  next=$(for d in $W/*/SAMPLED; do [ -f "$d" ] && basename $(dirname $d); done | head -1)
  if [ -n "$next" ]; then
    ink_block $next || { mv $W/$next/SAMPLED $W/$next/INK-FAILED 2>/dev/null; }
  elif ! kill -0 $CUTTERS 2>/dev/null; then
    break
  else
    sleep 10
  fi
done
log "BLOCKS-EXIT: $(ls $R/*/DONE 2>/dev/null | wc -l) done, $(ls $R/*/EMPTY 2>/dev/null | wc -l) empty, $(ls $W/*/INK-FAILED 2>/dev/null | wc -l) failed"
