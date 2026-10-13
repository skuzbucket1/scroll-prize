#!/usr/bin/env bash
# Ink-first sweep of PHerc0175A on AWS (Ted approved 2026-10-12: Reader v2 only, ~$20): N on-demand workers, each a
# g5.4xlarge (A10G 24 GB, 16 vCPU) or, when g5 has no capacity, a g6.4xlarge (L4 24 GB, 16 vCPU; Ted OK'd it), each
# running inkfirst_blocks.sh on every N-th block. Small results come home every 10 min; a worker is terminated as soon as
# its blocks are done; a trap fetches and terminates every worker on any exit. Each instance also has a hard
# auto-shutdown after FLEET_MAX_HOURS. Usage: experiments/ink-first/aws/inkfirst_sweep.sh <blocks.tsv> [workers=4] [models=readerv2] [par=4]
# Results: data/PHerc0175A/runs-aws/<date>_inkfirst-sweep/w<i>/ (progress.log, timings.tsv, <block>/summary.npz, galleries)
export INSTANCE_TYPES="g5.4xlarge g6.4xlarge" MARKET=${MARKET:-spot-then-ondemand} FLEET_MAX_HOURS=${FLEET_MAX_HOURS:-6} RETRY_MINUTES=${RETRY_MINUTES:-30}
AWS=$(cd "$(dirname "$0")/../../../infra/aws" && pwd)   # the shared AWS scripts (lib.sh, spot_*.sh) and state
ST=$AWS/state/inkfirst-sweep; export ISTATE=$ST/main
source "$AWS/lib.sh"
set +e
BL=$1; N=${2:-4}; MODELS=${3:-readerv2}; PAR=${4:-4}
U=https://vesuvius-challenge-open-data.s3.amazonaws.com/PHerc0175A
CT=$U/volumes/20250521115057-8.640um-1.2m-116keV-masked.zarr
PRED=$U/representations/predictions/surfaces/20250521115057-surface-20260413222639-surface-m7-L0-th0.2.zarr
OUT=$ROOT/data/PHerc0175A/runs-aws/$(date -u +%Y-%m-%d)_inkfirst-sweep; mkdir -p "$OUT"; cp "$BL" "$OUT/blocks.tsv"
check_account
price(){ case $(cat "$ST/w$1/instance_type" 2>/dev/null) in g6.4xlarge) echo 1.323;; *) echo 1.624;; esac; }
fetch(){ ( export ISTATE=$ST/w$1; [ -n "$(instance_ip)" ] && rsync_from /opt/scroll/results/inkfirst/ "$OUT/w$1/" < /dev/null 2>/dev/null ) || true; }
down(){ fetch $1; ( export ISTATE=$ST/w$1 ONDEMAND_PRICE=$(price $1); bash "$HERE/spot_down.sh" < /dev/null >> "$OUT/w$1/down.log" 2>&1 ); touch "$OUT/w$1/TERMINATED"; }
kill_tree(){ local c; for c in $(pgrep -P "$1"); do kill_tree "$c"; kill -TERM "$c" 2>/dev/null; done; }
teardown(){ trap - EXIT; kill_tree $$; sleep 2; log "teardown: fetching and terminating every worker"
  for i in $(seq 0 $((N - 1))); do [ -f "$OUT/w$i/TERMINATED" ] || down $i & done; wait
  # safety net: any Project-tagged instance still alive (e.g. launched just before its id was written) is terminated too
  ( export ISTATE=$ST/main; bash "$HERE/spot_down.sh" --all < /dev/null >> "$OUT/down-all.log" 2>&1 )
  bash "$HERE/spot_status.sh" < /dev/null 2>&1 | grep -v terminated | tail -5; grep -h "that is about" "$OUT"/w*/down.log; }
trap teardown EXIT

launch(){   # worker i: launch, push, start its blocks (fully detached on the instance)
  local i=$1 D=$OUT/w$i t; mkdir -p "$D" "$ST/w$i"
  (head -1 "$BL"; tail -n +2 "$BL" | awk -v n=$N -v i=$i '(NR - 1) % n == i') > "$D/blocks.tsv"
  # work + temp on the instance-store NVMe (/opt/dlami/nvme on the DLAMI, ~520 GB on g5/g6.4xlarge; far faster than gp3)
  printf '#!/bin/bash\nmkdir -p /opt/dlami/nvme/inkfirst/work /opt/dlami/nvme/inkfirst/tmp && cd /opt/scroll && WORK=/opt/dlami/nvme/inkfirst/work TMPDIR=/opt/dlami/nvme/inkfirst/tmp NO_GLOW=1 MAX_QUEUED=3 SPLIT_ABOVE=2500 bash /opt/scroll/bin/inkfirst_blocks.sh /opt/scroll/jobs/blocks.tsv %s %s 8.64 %s 96 256 %s\n' \
    "$CT" "$PRED" "$MODELS" "$PAR" > "$D/start.sh"
  ( export ISTATE=$ST/w$i
    bash "$HERE/spot_up.sh" > "$D/up.log" 2>&1 < /dev/null || exit 1
    t=$(cat "$ISTATE/instance_type"); case $t in g5.4xlarge|g6.4xlarge) ;; *) echo "REFUSED $t" >> "$D/up.log"; exit 2;; esac
    bash "$HERE/spot_push.sh" > "$D/push.log" 2>&1 < /dev/null
    rssh 'mkdir -p /opt/scroll/bin/ink-first-src /opt/scroll/jobs /opt/scroll/results/inkfirst' < /dev/null
    rsync_to "$ROOT/experiments/ink-first/tool/src/" /opt/scroll/bin/ink-first-src/ < /dev/null
    rsync_to "$ROOT/experiments/ink-first/inkfirst_block_summary.py" /opt/scroll/bin/ < /dev/null
    rsync_to "$ROOT/experiments/ink-first/viz_glow.py" /opt/scroll/bin/ < /dev/null
    rsync_to "$ROOT/experiments/ink-first/aws/inkfirst_blocks.sh" /opt/scroll/bin/ < /dev/null
    rsync_to "$D/blocks.tsv" /opt/scroll/jobs/blocks.tsv < /dev/null
    rsync_to "$D/start.sh" /opt/scroll/jobs/start.sh < /dev/null
    rssh 'setsid bash /opt/scroll/jobs/start.sh > /opt/scroll/results/inkfirst/run.log 2>&1 < /dev/null &' < /dev/null )
  case $? in
    0) touch "$D/STARTED"; log "w$i: started on $(cat "$ST/w$i/instance_type") with $(( $(wc -l < "$D/blocks.tsv") - 1 )) blocks";;
    1) log "w$i: no instance ($(tail -1 "$D/up.log"))"; touch "$D/NO-INSTANCE";;
    *) log "w$i: refused type, terminating"; down $i;;
  esac
}

T0=$(date +%s)
for i in $(seq 0 $((N - 1))); do launch $i & sleep 5; done; wait
log "launch phase done: $(ls "$OUT"/w*/STARTED 2>/dev/null | wc -l) of $N workers running"
last_fetch=$(date +%s)
while true; do
  live=0
  for i in $(seq 0 $((N - 1))); do
    [ -f "$OUT/w$i/STARTED" ] && [ ! -f "$OUT/w$i/TERMINATED" ] || continue
    live=$((live + 1))
    p=$( export ISTATE=$ST/w$i; rssh 'tail -1 /opt/scroll/results/inkfirst/progress.log 2>/dev/null; ls -d /opt/scroll/results/inkfirst/*/DONE 2>/dev/null | wc -l' < /dev/null 2>/dev/null | tr '\n' ' ')
    if echo "$p" | grep -q BLOCKS-EXIT; then log "w$i: finished ($p)"; down $i; else log "w$i: $p"; fi
  done
  [ $live -eq 0 ] && break
  if [ $(( $(date +%s) - last_fetch )) -ge 600 ]; then
    for i in $(seq 0 $((N - 1))); do [ -f "$OUT/w$i/STARTED" ] && [ ! -f "$OUT/w$i/TERMINATED" ] && fetch $i & done; wait; last_fetch=$(date +%s)
  fi
  [ $(( $(date +%s) - T0 )) -gt $(( FLEET_MAX_HOURS * 3600 - 900 )) ] && { log "close to the hard limit: stopping"; break; }
  sleep 120
done
log "sweep finished in $(( ($(date +%s) - T0) / 60 )) min; $(ls -d "$OUT"/w*/*/DONE 2>/dev/null | wc -l) blocks done"
