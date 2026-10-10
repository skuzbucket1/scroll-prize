#!/usr/bin/env bash
# On a fleet worker: wait for the running run_batch.sh to finish, then run it again on the (updated) batch.tsv.
# Segments with a DONE marker are skipped, so this only adds the ones the first pass did not have.
while pgrep -f "/opt/scroll/bin/[r]un_batch.sh" > /dev/null; do sleep 15; done
exec bash /opt/scroll/bin/run_batch.sh
