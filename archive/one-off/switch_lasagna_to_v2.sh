#!/usr/bin/env bash
# Retire the v1 lasagna mirrors once v2 is downloading, and repoint the assembly waiter + volume auto-resume at the v2 logs.
set -u
D=/mnt/nvme/scroll-prizes/data/PHerc0191
for st in nx ny grad_mag; do grep -q '^== level 2' "$D/mirror-lasagna-v2-PHerc0191_$st.log" 2>/dev/null || { echo "v2-$st not downloading yet — aborting switch"; exit 1; }; done
pkill -f 'mirror_s3.py.*lasagna' ; sleep 2; echo "v1 lasagna mirrors stopped ($(pgrep -fc 'mirror_s3.py.*lasagna') left)"
find "$D/lasagna" -name '*.part' -delete 2>/dev/null; echo "stale v1 .part files removed"
# assembly waiter → v2 logs
pkill -f assemble_pherc0191.sh; sleep 1
sed -i 's|mirror-lasagna-PHerc0191_\$st.log|mirror-lasagna-v2-PHerc0191_$st.log|' ~/scroll-prizes/bin/assemble_pherc0191.sh
grep -n 'mirror-lasagna' ~/scroll-prizes/bin/assemble_pherc0191.sh | head -2
setsid -f bash -c '~/scroll-prizes/bin/assemble_pherc0191.sh' > ~/scroll-prizes/assemble-pherc0191.log 2>&1; echo "assembly waiter relaunched (→ v2 logs)"
# the pilot waiter watches assemble-pherc0191.log, which we just truncated/relaunched → still valid (it greps for ASSEMBLE-EXIT)
# volume auto-resume → v2 logs
pkill -f resume_volume_after_lasagna.sh; sleep 1
sed -i 's|mirror-lasagna-PHerc0191_\$st.log|mirror-lasagna-v2-PHerc0191_$st.log|' ~/scroll-prizes/bin/resume_volume_after_lasagna.sh
setsid -f bash -c '~/scroll-prizes/bin/resume_volume_after_lasagna.sh' > ~/scroll-prizes/resume-volume.log 2>&1; echo "volume auto-resume relaunched (→ v2 logs)"
echo "SWITCH-OK $(date -Is)"
