#!/usr/bin/env bash
# End-to-end positive control on PHerc. 343 (Ted 2026-10-13 ~8:30 pm CT: "add it on aws"; ~$8): our own geometry
# recipe on z 9,300-11,300 around Erwin Nieuwlaar's 18 letters, then which of our windings carry the letters and whether
# they show in our read (control_job.sh). One worker, spot first (cheapest zone, <= 0.6 x on-demand), else on-demand;
# tag Project=scroll-prize-ctl; hard limit 7 h. Every 5 min: progress; at CONTROL-EXIT: fetch (logs, letter hits, eval, the
# read windings' maps and previews, our geometry without the inputs), terminate. A trap does the same on any exit.
# Results: data/PHerc0343/runs-aws/2026-10-13_control/. Usage: nohup caffeinate -i bash pipeline/controls/endtoend343/launch_aws.sh > data/PHerc0343/runs-aws/control.log 2>&1 &
export INSTANCE_TYPES="g5.4xlarge g6.4xlarge" MARKET=spot-then-ondemand PROJECT_TAG=scroll-prize-ctl FLEET_MAX_HOURS=7 RETRY_MINUTES=30
AWS=$(cd "$(dirname "$0")/../../../infra/aws" && pwd); G2=$(cd "$(dirname "$0")" && pwd); X=$G2
ST=$AWS/state/control-343; export ISTATE=$ST/w; mkdir -p $ST/w
source "$AWS/lib.sh"
set +e
OUT=$ROOT/data/PHerc0343/runs-aws/2026-10-13_control; mkdir -p "$OUT"
LET=$OUT/letters3d.npz; [ -s $LET ] || scp -q -o BatchMode=yes "$BOX:scroll-prizes/runs/2026-10-12_inkfirst-343/letters3d.npz" $LET < /dev/null
[ -s $LET ] || { log "no letters3d.npz"; exit 2; }
ENVS="SC=PHerc0343 VN=20250521140437-8.640um-1.2m-116keV-masked.zarr SN=20250521140437-surface-20260413222639-surface-m7-L0-th0.2.zarr LN=20250521140437-lasagna-20260419180421 UM=8.64 NZ=17998 NY=8595 NX=8595 LETTERS=/opt/scroll/geom/letters3d.npz READ_MODELS=readerv2,d9v4c"
check_account
fetch(){ [ -n "$(instance_ip)" ] || return 0
  rsync_from /opt/scroll/results/ "$OUT/results/" --exclude '*.zarr' < /dev/null 2>/dev/null
  rsync_from /opt/dlami/nvme/scroll/data/PHerc0343/ "$OUT/data/" --exclude 'source/' --exclude 'tracks/' --exclude '*.pt' --exclude '*.pth' \
    --exclude '*.ckpt' --exclude '*respool*' --exclude 'lasagna_inputs/' < /dev/null 2>/dev/null; }
light(){ [ -n "$(instance_ip)" ] && rsync_from /opt/scroll/results/geometry/ "$OUT/results/geometry/" < /dev/null 2>/dev/null; }
down(){ fetch; ( export ONDEMAND_PRICE=$(case $(cat $ISTATE/instance_type 2>/dev/null) in g6.4xlarge) echo 1.323;; *) echo 1.624;; esac); bash "$HERE/spot_down.sh" < /dev/null >> "$OUT/down.log" 2>&1 )
  touch "$OUT/TERMINATED"; log "terminated: $(grep -h 'that is about' "$OUT/down.log" | tail -1)"; }
teardown(){ trap - EXIT; log "teardown"; [ -f "$OUT/TERMINATED" ] || [ ! -s "$ISTATE/instance_id" ] || down
  ( export ISTATE=$ST/main; mkdir -p $ST/main; bash "$HERE/spot_down.sh" --all < /dev/null >> "$OUT/down-all.log" 2>&1 ); }
trap teardown EXIT
log "control 343: launching one worker"
WORKER_NAME=ctl-343 bash "$HERE/spot_up.sh" > "$OUT/up.log" 2>&1 < /dev/null || { log "launch FAILED (up.log)"; exit 1; }
FLATTEN=1 bash "$HERE/spot_push.sh" > "$OUT/push.log" 2>&1 < /dev/null
rssh 'mkdir -p /opt/scroll/geom/bin /opt/scroll/results/geometry' < /dev/null
for f in assemble_spiral_dataset.sh smooth_umbilicus.py fit_band.sh snap_band.sh snap_meshes_nieuwlaar.py LICENSE-snap_meshes_nieuwlaar \
         flatten_winding.sh ray_peaks.py mesh_in_mask.py; do rsync_to "$ROOT/pipeline/geometry/$f" /opt/scroll/geom/bin/ < /dev/null; done
for f in "$G2/control_job.sh" "$X/letters_on_windings.py" "$X/letters_eval.py" "$LET"; do rsync_to "$f" /opt/scroll/geom/ < /dev/null; done
rssh "export $ENVS MAX_HOURS=$FLEET_MAX_HOURS; setsid nohup bash /opt/scroll/geom/control_job.sh 9300 11300 exp30k-z9300 > /opt/scroll/results/geometry/job.log 2>&1 < /dev/null &" < /dev/null
log "started on $(cat $ISTATE/instance_type) $(cat $ISTATE/market 2>/dev/null)"
while :; do
  sleep 300
  p=$(rssh "tail -1 /opt/scroll/results/geometry/progress.log 2>/dev/null; grep -h PROGRESS /opt/dlami/nvme/scroll/data/PHerc0343/geometry/*/fit-full.log 2>/dev/null | tail -1 | cut -c1-70" < /dev/null | LC_ALL=C tr '\n' ' ')
  if [ -z "$p" ]; then s=$(awsc ec2 describe-instances --instance-ids "$(cat $ISTATE/instance_id)" --query 'Reservations[0].Instances[0].State.Name' --output text 2>/dev/null)
    case $s in shutting-down|terminated) log "instance $s: LOST"; touch "$OUT/LOST"; break;; esac; fi
  log "$p"; light
  echo "$p" | grep -q "CONTROL-EXIT" && { down; break; }
done
log "control finished"
