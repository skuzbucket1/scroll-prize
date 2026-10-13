#!/usr/bin/env bash
# Re-rank (bin/stroke_rank.sh, incremental) whenever new ink maps land; stop once the ink jobs have ended.
S=~/scroll-prizes; O=/mnt/nvme/scroll-prizes/data/strokes; M=/mnt/nvme/scroll-prizes/data/PHerc0191/ink-triage/maps
while true; do
  if [ ! -f $O/ranking.tsv ] || [ -n "$(find $M -maxdepth 1 -newer $O/ranking.tsv -name '*' -type f | head -n 1)" ]; then
    $S/bin/stroke_rank.sh $M > $O/rank-last.log 2>&1
    echo "[$(date -Is)] $(head -c 0 /dev/null)$(grep -c . $O/ranking.tsv) lines; top 0191: $(grep -v control $O/ranking.tsv | sed -n 2p | cut -f1-5,7-9)"
  fi
  if ! pgrep -f ensemble_windings.sh > /dev/null && ! pgrep -f ink_triage.sh > /dev/null; then
    $S/bin/stroke_rank.sh $M > $O/rank-last.log 2>&1; echo "STROKEWATCH-EXIT: 0"; exit 0
  fi
  sleep 600
done
