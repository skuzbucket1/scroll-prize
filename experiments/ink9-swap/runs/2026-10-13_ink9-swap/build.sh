#!/bin/bash
# build.sh - the two checkpoint soups and the load check for the ink9-swap test (2026-10-13). CPU only (no GPU visible),
# nice 19, one step at a time. Marker BUILD-EXIT in build.log.
S=/home/tbienapfl/scroll-prizes; R=$S/runs/2026-10-13_ink9-swap; O=$S/checkpoints/ink_9um; E=$S/checkpoints/ink_9um_extra
export CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=2 MKL_NUM_THREADS=2
PY="nice -n 19 $S/villa/vesuvius/.venv/bin/python -I"; mkdir -p $E/soups; rc=0
echo "[$(date -Is)] soup42_last4"
$PY $R/make_soup.py $E/soups/soup42_last4.pth $O/hybrid_3d2d-seed42/step-040000.pth $E/hybrid_3d2d-seed42/step-050000.pth \
  $E/hybrid_3d2d-seed42/step-060000.pth $O/hybrid_3d2d-seed42/step-075000.pth --check $E/nieuwlaar/soup42_last4.safetensors || rc=1
echo "[$(date -Is)] soup43_last4"
$PY $R/make_soup.py $E/soups/soup43_last4.pth $E/hybrid_3d2d-seed43/step-040000.pth $E/hybrid_3d2d-seed43/step-050000.pth \
  $E/hybrid_3d2d-seed43/step-060000.pth $O/hybrid_3d2d-seed43/step-075000.pth || rc=1
echo "[$(date -Is)] verify"
$PY $R/verify_ckpts.py $R/verify.json $O/hybrid_3d2d-seed42/step-075000.pth \
  a_s42_75k=$O/hybrid_3d2d-seed42/step-075000.pth b_s43_60k=$E/hybrid_3d2d-seed43/step-060000.pth \
  c_soup42=$E/soups/soup42_last4.pth d_soup43=$E/soups/soup43_last4.pth e_s43_75k=$O/hybrid_3d2d-seed43/step-075000.pth || rc=1
ls -la $E/soups
echo "[$(date -Is)] BUILD-EXIT: $rc"
