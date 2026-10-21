#!/usr/bin/env bash
# Back up everything we made that cannot simply be downloaded again, on every disk, to Ted's private S3-compatible backup bucket
# with rclone (Ted 2026-10-21: "we need to backup the code and the data we can't just redownload regardless the disk it lives on").
# Usage: infra/backup/backup_r2.sh mac|box [--dry-run]      (--dry-run prints the size of each job's selection, uploads nothing)
#   box (run on the GPU box), two jobs, one per disk:
#     /mnt/nvme/scroll-prizes  -> r2:<bucket>/box    data/ (geometry, ink maps, scores, inputs' centre files, ink-first results,
#                                                     controls, training sets ...), runs/, work/ (every task's results)
#     /mnt/nvme2/scroll-prizes -> r2:<bucket>/box2   work/, data/, controls/ on the second disk
#     Private patterns (untracked, next to this script, one rclone pattern per line; lines starting with + or - are used as they are,
#     others are includes; they come FIRST, so they can keep or drop single paths): box_private_paths.txt (first disk),
#     box2_private_paths.txt (second disk).
#     Credentials from ~/.config/rclone/rclone.conf (remote "r2"); bucket name from $R2_BUCKET or ~/.config/rclone/r2_bucket.
#   mac (run on the Mac, repo root), two jobs:
#     the repo -> r2:<bucket>/mac                     memory/, notes/, data/ (not prior-art/, scratch/, aws-stage/), and the private
#                                                     folders kept out of git (infra/backup/private_paths.txt)
#     ../scroll-prize-private -> r2:<bucket>/mac-private-repo   every script and note from every machine, with its git history
#     Credentials from .secrets via infra/backup/r2_env.sh (never printed).
# Never backed up (all can be downloaded or rebuilt): .secrets, the public scans and other public inputs (data/*/source, CT crops),
# model files (checksums in the private config), upstream code (villa/, wt/, ext/, envs/), caches, scratch, tmp, the sites (built
# from the data), temporary CT chunk stores, and the search bands' renders (data/<scroll>/renders, rebuilt from the backed-up
# meshes: Ted 2026-10-21, a monthly budget; until there is a NAS). Every other render is backed up (Ted 10-21: "Keep all of the others").
# rclone sync with --backup-dir r2:<bucket>/_archive/<UTC stamp>/<dest>/: files changed or deleted locally are kept in R2.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)   # infra/backup on the Mac, ~/scroll-prizes/scripts on the box (its two lists live next to it)
HOST=${1:?mac|box}; DRY=${2:-}
RC=$(command -v rclone || echo ~/.local/bin/rclone); STAMP=$(date -u +%Y%m%d-%H%M)
TMPD=$(mktemp -d); trap 'rm -rf $TMPD' EXIT
COMMON='- .DS_Store
- **/.venv/**
- **/__pycache__/**
- **/ct_*.zarr/**
- **/ct-*.zarr/**'                                  # downloaded CT crops and temporary CT chunk stores
plist(){ [ -f "$1" ] && { grep -v '^#' "$1" || true; } | sed '/^$/d; /^[+-] /!s|^|+ |'; return 0; }   # a private list, + / - kept

if [ "$HOST" = mac ]; then
  cd "$HERE/../.."; source infra/backup/r2_env.sh; ROOT1=$PWD
  { echo "$COMMON"
    echo '- /data/prior-art/**'; echo '- /data/scratch/**'; echo '- /data/aws-stage/**'; echo '- /data/controls9um/stroke-score-src/**'
    echo '+ /memory/**'; echo '+ /notes/**'; echo '+ /data/**'
    if [ -f infra/backup/private_paths.txt ]; then { grep -v '^#' infra/backup/private_paths.txt || true; } | sed '/^$/d; s|^|+ |'; fi
    echo '- **'; } > $TMPD/f1
  printf '%s\n' '- .DS_Store' '+ **' > $TMPD/f2
  JOBS=("$ROOT1|mac|$TMPD/f1" "$(cd "$ROOT1/../scroll-prize-private" && pwd)|mac-private-repo|$TMPD/f2")
else
  R2_BUCKET=${R2_BUCKET:-$(cat ~/.config/rclone/r2_bucket 2>/dev/null)}; [ -n "$R2_BUCKET" ] || { echo 'no bucket name'; exit 2; }
  { plist $HERE/box_private_paths.txt; echo "$COMMON"
    echo '- /data/*/source/**'; echo '- /data/*/renders/**'                       # public inputs; renders (links to the 2nd disk)
    echo '- /data/*/geometry/*/flattened/*/model*/**'                              # the flattening models (re-created by a flatten)
    echo '- /data/*/inkfirst*/*.zarr/**'; echo '- /data/*/inkfirst*/**/mosaic.zarr/**'; echo '- /data/*/inkfirst*/**/q[0-3]/**'
    echo '+ /data/*/inputs/spiral-dataset/umbilicus*'; echo '+ /data/*/inputs/spiral-dataset/spiral-scroll.json'
    echo '+ /data/*/inputs/spiral-dataset/qa/**'; echo '- /data/*/inputs/**'            # inputs: only what we made (centre, QA)
    echo '- /work/tmp/**'                                                         # tmp
    echo '+ /data/**'; echo '+ /runs/**'; echo '+ /work/**'; echo '+ /backup/**'
    echo '- **'; } > $TMPD/f1
  { plist $HERE/box2_private_paths.txt; echo "$COMMON"
    echo '- /data/*/renders/**'; echo '- /data/controls-ct*/**'                     # renders; CT crops (re-downloadable)
    echo '- /work/tmp/**'; echo '- **/xscan_cache*/**'                             # temporary folders and caches
    echo '- /work/sharpen/*/**'                                                    # the sharpening test's filtered CT (a dead end)
    echo '+ /work/**'; echo '+ /data/**'; echo '+ /controls/**'
    echo '- **'; } > $TMPD/f2
  JOBS=("/mnt/nvme/scroll-prizes|box|$TMPD/f1" "/mnt/nvme2/scroll-prizes|box2|$TMPD/f2")
fi

worst=0
for job in "${JOBS[@]}"; do
  IFS='|' read -r ROOT DEST FILT <<< "$job"
  if [ "$DRY" = --dry-run ]; then
    echo "$DEST <- $ROOT: $($RC size "$ROOT" --filter-from "$FILT" 2>/dev/null | tr '\n' ' ')"
    $RC lsf -R --files-only --format sp --separator '|' --filter-from "$FILT" "$ROOT" 2>/dev/null |   # the 15 biggest folders, 3 levels
      awk -F'|' '{n=split($2,a,"/"); k=a[1]; for(i=2;i<=3&&i<n;i++) k=k"/"a[i]; s[k]+=$1} END {for (k in s) printf "%10.2f GiB  %s\n", s[k]/2^30, k}' |
      sort -rn | head -15 | sed 's/^/    /' || true                                 # head closes the pipe early: not an error
    continue
  fi
  OPTS=(--filter-from "$FILT" --backup-dir "r2:$R2_BUCKET/_archive/$STAMP/$DEST" --fast-list --transfers 8 --checkers 16 --stats 60s --stats-one-line)
  echo "[$(date -u +%FT%TZ)] backup $ROOT -> r2:$R2_BUCKET/$DEST"
  set +e +o pipefail
  $RC sync "$ROOT" "r2:$R2_BUCKET/$DEST" "${OPTS[@]}" --stats-log-level NOTICE 2>&1 | grep -vE "NOTICE: Config file" | tail -8
  rc=${PIPESTATUS[0]}; set -e -o pipefail; [ $rc -gt $worst ] && worst=$rc
  echo "[$(date -u +%FT%TZ)] r2 $DEST now: $($RC size "r2:$R2_BUCKET/$DEST" 2>/dev/null | tr '\n' ' ') (rc $rc)"
done
[ "$DRY" = --dry-run ] || echo "[$(date -u +%FT%TZ)] BACKUP-EXIT: $worst"
