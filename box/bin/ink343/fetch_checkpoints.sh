#!/bin/bash
# fetch_checkpoints.sh - download the public checkpoints (and hecate.py) listed in models.tsv into CKPT_DIR and verify
# every file against its sha256. Anonymous HTTPS GET only; nothing is uploaded.
#
#   fetch_checkpoints.sh [MODELS_TSV] [CKPT_DIR]      (defaults: /opt/pherc0343/models.tsv, /opt/ckpt)
#
# dense_native-016000: the exact training checkpoint (sha256 aacf6cb8...) is not on a public server and not in this
# package. If a copy is already in CKPT_DIR it is verified and used. Otherwise the public release (safetensors weights
# + training config, both sha256-checked) is wrapped into a villa-loadable dense_native-016000.rebuilt.pth by
# rebuild_dense_native_pth.py.
set -euo pipefail
TSV=${1:-/opt/pherc0343/models.tsv}
CK=${2:-/opt/ckpt}
PY=${PY:-/opt/venv/bin/python}
HERE=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$CK"

get() {  # <url> <dest> <sha256>: resumable download, then a mandatory sha256 check
  local url=$1 dst=$2 sha=$3 t got
  if [[ -s $dst && $(sha256sum "$dst" | cut -d' ' -f1) == "$sha" ]]; then echo "ok (present)  $(basename "$dst")"; return 0; fi
  for t in 1 2 3 4 5; do
    curl -fL -sS --connect-timeout 30 --speed-limit 102400 --speed-time 60 -C - -o "$dst.part" "$url" && break
    echo "download attempt $t failed: $url"; sleep $((t * 10))
  done
  got=$(sha256sum "$dst.part" | cut -d' ' -f1)
  if [[ $got != "$sha" ]]; then echo "SHA256 MISMATCH for $url: $got != $sha"; rm -f "$dst.part"; return 1; fi
  mv -f "$dst.part" "$dst"; echo "ok (download) $(basename "$dst") $got"
}

declare -A F S U
while IFS=$'\t' read -r key kind file sha source url; do
  [[ $key == key || -z $key ]] && continue
  F[$key]=$file; S[$key]=$sha; U[$key]=$url
  [[ $source == url ]] || continue
  [[ $kind == rebuild ]] && continue            # only needed if the exact dense_native file is absent (below)
  get "$url" "$CK/$file" "$sha"
done < "$TSV"

# dense_native-016000
DN=$CK/${F[dnative]}
if [[ -s $DN && $(sha256sum "$DN" | cut -d' ' -f1) == "${S[dnative]}" ]]; then
  echo "ok (present)  ${F[dnative]} (exact training checkpoint)"
else
  echo "exact dense_native checkpoint not available; rebuilding it from the public release"
  get "${U[dnative_public_weights]}" "$CK/${F[dnative_public_weights]}" "${S[dnative_public_weights]}"
  get "${U[dnative_public_config]}" "$CK/${F[dnative_public_config]}" "${S[dnative_public_config]}"
  "$PY" "$HERE/rebuild_dense_native_pth.py" "$CK/${F[dnative_public_weights]}" "$CK/${F[dnative_public_config]}" \
      "$CK/dense_native-016000.rebuilt.pth"
  echo "run_ink.sh uses $CK/dense_native-016000.rebuilt.pth for dnative"
fi
sha256sum "$CK"/* > "$CK/SHA256SUMS.local" 2>/dev/null || true
echo "checkpoints in $CK"
