#!/usr/bin/env bash
# Pull a preview TIFF from the GPU box and convert it to JPEG for viewing.
# Usage: scripts/pull_preview.sh <remote path under ~/scroll-prizes/> [local-name]
set -euo pipefail
remote=$1; name=${2:-$(basename "${remote%.tif}")}
dest_dir=/Users/tbienapfl/dev/vscode/scroll-prizes/data/results; mkdir -p "$dest_dir"
scp -q tbienapfl@192.168.1.61:"scroll-prizes/$remote" "$dest_dir/$name.tif"
sips -s format jpeg -s formatOptions 85 "$dest_dir/$name.tif" --out "$dest_dir/$name.jpg" >/dev/null
rm -f "$dest_dir/$name.tif"
echo "$dest_dir/$name.jpg $(sips -g pixelWidth -g pixelHeight "$dest_dir/$name.jpg" | awk '/pixel/{printf "%s ", $2}')"
