#!/usr/bin/env bash
# One-screen status of the PHerc0191 campaign on this box.
cd ~/scroll-prizes; D=/mnt/nvme/scroll-prizes/data/PHerc0191
echo "== mirrors"; printf '  %-14s %s\n' volume "$(grep -E 'files .* MB/s|^done|MIRROR-EXIT' $D/mirror-volume.log 2>/dev/null | tail -1 | cut -c1-100) [$(ps -o stat= -p $(pgrep -f 'mirror_s3.py.*volumes/' | head -1) 2>/dev/null || echo 'no process')]"
for st in nx ny grad_mag; do printf '  %-14s %s\n' "lasagna-$st" "$(grep -E 'files/s|^done|MIRROR-EXIT' $D/mirror-lasagna-v2-PHerc0191_$st.log 2>/dev/null | tail -1 | cut -c1-100)"; done
printf '  %-14s %s\n' normal-grids "$(grep -E '^done|MIRROR-EXIT' $D/mirror-normalgrids.log 2>/dev/null | tail -1 | cut -c1-80)"; printf '  %-14s %s\n' tracks "$(du -sh $D/spiral 2>/dev/null | cut -f1) $(grep -h TRACKS-EXIT $D/tracks-download.log 2>/dev/null)"
echo "== chain"; for f in assemble-pherc0191 pilot-fit resume-volume; do printf '  %-14s %s\n' "$f" "$(tail -1 $f.log 2>/dev/null | cut -c1-110)"; done
echo "== waiters/jobs"; pgrep -fa 'assemble_pherc|pilot_fit|resume_volume|fit_spiral|mirror_s3|wget' | grep -vE 'pgrep|bash -c' | cut -c1-100 | sed 's/^/  /'
echo "== disk/gpu"; df -h / /mnt/nvme | awk 'NR>1{print "  "$6": "$4" free ("$5")"}'; echo "  gpu: $(nvidia-smi --query-gpu=index,memory.used,utilization.gpu --format=csv,noheader | tr '\n' ';')"
echo "  ollama: $(systemctl is-active ollama-gpu0 ollama-gpu2 ollama-dualgpu 2>/dev/null | tr '\n' ' ')(stopped for testing phase — restart when done)"
echo "NOTE: GPU 1 (GTX 1660 SUPER) is NOT usable for any of this work - use GPUs 0/2/3 only"
