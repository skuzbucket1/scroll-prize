#!/usr/bin/env bash
# Keep the box's AWS control checkout (~/scroll-prize-control -> /mnt/nvme/scroll-prizes/control) in step with the Mac
# (run on the Mac, repo root, after pushing): git pull there, then the git-excluded pieces the launchers need (private
# launcher folders and centre files). Never copies instance state (whoever launched a run keeps managing it) and never
# launches anything. spot.env and the instances' SSH key were copied once (2026-10-15); re-copy them only if they change.
# Usage: bash infra/box/sync_control.sh
set -euo pipefail
cd "$(dirname "$0")/../.."; B=${BOX:-tbienapfl@100.74.214.106}; C=/mnt/nvme/scroll-prizes/control
ssh -o BatchMode=yes $B "cd $C && git pull -q --ff-only && git log --oneline -1"
for d in experiments/scroll-0175a data/results/0175A-centre; do
  [ -d "$d" ] && rsync -a --exclude 'runs/' "$d/" "$B:$C/$d/"
done
scp -q .git/info/exclude $B:$C/.git/info/exclude
ssh -o BatchMode=yes $B "cd $C && git status --short | head -5"
echo "control checkout in step"
