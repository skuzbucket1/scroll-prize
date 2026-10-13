#!/bin/bash
# fetch.sh - the extra ink_9um checkpoints for the ink9-swap test (2026-10-13), from the public HF model repo
# scrollprize/ink_9um (revision 7109667e), each checked against the sha256 HF lists for it; plus Erwin Nieuwlaar's
# published soup42_last4.safetensors (HF Nieuwlaar/ink9um-dense-native, weights/), only to check that our seed-42 soup
# is bit-identical to his. Anonymous HTTPS GET only. Writes ~/scroll-prizes/checkpoints/ink_9um_extra/; log fetch.log.
set -uo pipefail
E=$HOME/scroll-prizes/checkpoints/ink_9um_extra; mkdir -p "$E"
REV=7109667e2607db1b90c37c8b09cb876ea7fe7bb1
get() {  # <url> <dest> <sha256>
  local url=$1 dst=$2 sha=$3 t got
  if [[ -s $dst && $(sha256sum "$dst" | cut -d' ' -f1) == "$sha" ]]; then echo "ok (present)  $dst"; return 0; fi
  mkdir -p "$(dirname "$dst")"
  for t in 1 2 3 4 5; do
    nice -n 19 curl -fL -sS --connect-timeout 30 --speed-limit 102400 --speed-time 60 -C - -o "$dst.part" "$url" && break
    echo "download attempt $t failed: $url"; sleep $((t * 10))
  done
  got=$(sha256sum "$dst.part" | cut -d' ' -f1)
  [[ $got == "$sha" ]] || { echo "SHA256 MISMATCH $url: $got != $sha"; rm -f "$dst.part"; return 1; }
  mv -f "$dst.part" "$dst"; echo "ok (download) $dst $(stat -c %s "$dst") bytes"
}
B=https://huggingface.co/scrollprize/ink_9um/resolve/$REV
rc=0
while read -r f sha; do
  get "$B/$f" "$E/$f" "$sha" || rc=1
done <<'LIST'
hybrid_3d2d-seed42/step-050000.pth c16c75db4c6ea75b929c4db82437098d0a4ca0f3779c77e3aabc228f52ea2238
hybrid_3d2d-seed42/step-060000.pth 63cad1fb689a575662b6cc367635ec968ec488b219af12aff0497781488070ab
hybrid_3d2d-seed43/step-040000.pth e0b9ec7e5e9cb7caf6c9689bd35159285bb82c629f63e5ec83cb220e8d659978
hybrid_3d2d-seed43/step-050000.pth c3c55191dad99849696c980aa7abaf6305514a91d6b8ba898e1e0dbb50eb3ea4
hybrid_3d2d-seed43/step-060000.pth bf229faf754da3f1fc3026a3f9a9649341aeb3feb7bc89099cad31c55525d270
LIST
get https://huggingface.co/Nieuwlaar/ink9um-dense-native/resolve/main/weights/soup42_last4.safetensors \
    "$E/nieuwlaar/soup42_last4.safetensors" ab3f1bdefa53733f4d4c46da6c7713c142bc8c703df5098fe8641757d764849c || rc=1
# the three we already have (in checkpoints/ink_9um/), checked against the same HF list, read only
O=$HOME/scroll-prizes/checkpoints/ink_9um
while read -r f sha; do
  got=$(nice -n 19 sha256sum "$O/$f" | cut -d' ' -f1)
  [[ $got == "$sha" ]] && echo "ok (existing) $O/$f" || { echo "EXISTING MISMATCH $O/$f: $got != $sha"; rc=1; }
done <<'LIST'
hybrid_3d2d-seed42/step-040000.pth f1e2101df567a431d3f39d17503316483084bace64cba55ef9671e5ea24ea76a
hybrid_3d2d-seed42/step-075000.pth e635558ae6a1a807a7e5ec1e83adfd45bc3c0ac53883ea43f1d4e085d62a9cab
hybrid_3d2d-seed43/step-075000.pth 2aeaa85a35ef28d7bc7bf3e848c4a6a91385e9132710927fdba41133c4ecb28f
LIST
echo "[$(date -Is)] FETCH-EXIT: $rc"
