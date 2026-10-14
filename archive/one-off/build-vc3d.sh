#!/usr/bin/env bash
# Mirrors villa/volume-cartographer/build_from_src_debian.sh minus the apt/sudo steps; installs to $HOME/.local.
set -euo pipefail
cd ~/scroll-prizes
until grep -q 'CLONE-EXIT:' villa-clone.log 2>/dev/null; do sleep 15; done
until grep -q 'APT-DEPS-EXIT:' apt-vc3d-deps.log 2>/dev/null; do sleep 15; done
grep -q 'CLONE-EXIT: 0' villa-clone.log || { echo "clone failed"; exit 1; }
grep -q 'APT-DEPS-EXIT: 0' apt-vc3d-deps.log || { echo "apt deps failed"; exit 1; }
src=$HOME/scroll-prizes/villa/volume-cartographer
build=$src/build/from-source
prefix=$HOME/.local
echo "[$(date -Is)] configure"
cmake -S "$src" -B "$build" -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_COMPILER=gcc -DCMAKE_CXX_COMPILER=g++ -DCMAKE_Fortran_COMPILER=gfortran -DCMAKE_INSTALL_PREFIX="$prefix" -DBLA_VENDOR=OpenBLAS -DVC_BUILD_APPS=ON -DVC_BUILD_FLATBOI=ON -DVC_BUILD_PYTHON=OFF -DVC_TESTING=OFF
echo "[$(date -Is)] build with $(nproc) jobs"
cmake --build "$build" --parallel "$(nproc)"
echo "[$(date -Is)] install to $prefix"
cmake --install "$build" --component vc_runtime
for p in VC3D vc_grow_seg_from_seed flatboi vc_render_tifxyz; do [ -x "$prefix/bin/$p" ] && echo "ok: $p" || echo "MISSING: $p"; done
echo "BUILD-EXIT: 0"
