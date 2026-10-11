#!/usr/bin/env bash
# Back up the critical set to Ted's private S3-compatible backup bucket with rclone. Usage: scripts/backup_r2.sh mac|box [--dry-run]
#   mac (run on the Mac, repo root): memory/, data/<scroll>/reviews, data/<scroll>/runs-aws, data/aws-results, data/controls9um,
#       data/catalog, data/results, data/ref. Credentials from .secrets via scripts/r2_env.sh (never printed).
#   box (run on the GPU box, from /mnt/nvme/scroll-prizes): data/<scroll>/geometry (fits, snapped and flattened meshes),
#       the spiral-dataset umbilicus/scroll files, data/<scroll>/scores, runs/, and the ink maps + ensemble images of the windings
#       listed in backup/windings_of_interest.tsv. Credentials from ~/.config/rclone/rclone.conf (remote "r2"); bucket name from $R2_BUCKET or ~/.config/rclone/r2_bucket.
# Never backed up: .secrets, scan data and other public inputs, renders, resident pools, caches (all re-creatable).
# rclone sync with --backup-dir r2:<bucket>/_archive/<UTC stamp>/<host>/: files changed or deleted locally are kept in R2.
set -euo pipefail
HOST=${1:?mac|box}; DRY=${2:-}
RC=$(command -v rclone || echo ~/.local/bin/rclone); STAMP=$(date -u +%Y%m%d-%H%M)
F=$(mktemp); trap 'rm -f $F' EXIT
if [ "$HOST" = mac ]; then
  cd "$(dirname "$0")/.."; source scripts/r2_env.sh; ROOT=$PWD
  cat > $F <<'X'
- /data/controls9um/stroke-score-src/**
- .DS_Store
+ /memory/**
+ /data/*/reviews/**
+ /data/*/runs-aws/**
+ /data/aws-results/**
+ /data/controls9um/**
+ /data/catalog/**
+ /data/results/**
+ /data/ref/**
- **
X
else
  ROOT=/mnt/nvme/scroll-prizes; R2_BUCKET=${R2_BUCKET:-$(cat ~/.config/rclone/r2_bucket 2>/dev/null)}; [ -n "$R2_BUCKET" ] || { echo 'no bucket name'; exit 2; }; cd $ROOT
  { echo "- /data/*/geometry/*/flattened/*/model*/**"
    echo "+ /data/*/geometry/**"
    echo "+ /data/*/inputs/spiral-dataset/umbilicus*"; echo "+ /data/*/inputs/spiral-dataset/spiral-scroll.json"; echo "+ /data/*/inputs/spiral-dataset/qa/**"
    echo "+ /data/*/scores/**"; echo "+ /runs/**"
    grep -v '^#' $ROOT/backup/windings_of_interest.tsv | while IFS=$'\t' read -r sc fit w why; do
      [ -n "$w" ] || continue
      echo "+ /data/$sc/ink/$fit/maps/${w}__*"; echo "+ /data/$sc/ink/$fit/ens3/$w/**"; echo "+ /data/$sc/ink/$fit/ens4/$w/**"
    done
    echo "- **"; } > $F
fi
OPTS=(--filter-from "$F" --backup-dir "r2:$R2_BUCKET/_archive/$STAMP/$HOST" --fast-list --transfers 8 --checkers 16 --stats 60s --stats-one-line)
[ "$DRY" = --dry-run ] && { $RC size "$ROOT" --filter-from "$F" 2>/dev/null; exit 0; }
echo "[$(date -u +%FT%TZ)] backup $HOST -> r2:$R2_BUCKET/$HOST"
$RC sync "$ROOT" "r2:$R2_BUCKET/$HOST" "${OPTS[@]}" -v 2>&1 | grep -vE "NOTICE: Config file" | grep -E "Transferred|Errors|ERROR|Checks|Elapsed" | tail -5
echo "[$(date -u +%FT%TZ)] BACKUP-EXIT: ${PIPESTATUS[0]}"
