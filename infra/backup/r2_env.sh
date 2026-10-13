# Source this to point rclone at Ted's private backup bucket (S3-compatible object storage). Reads the labelled lines of .secrets
# ("access key", "secret access key", "s3 endpoint for bucket"); never prints them. Remote name: r2, bucket: $R2_BUCKET.
_sec=${SECRETS_FILE:-$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/../.." && pwd)/.secrets}
_get() { awk -v k="$1" '{ if (match($0, /^[^:]+:/)) { lab=substr($0,1,RLENGTH-1); gsub(/^[ \t]+|[ \t]+$/,"",lab); if (tolower(lab)==k) { v=substr($0,RLENGTH+1); gsub(/^[ \t]+|[ \t]+$/,"",v); print v; exit } } }' "$_sec"; }
_ep=$(_get "s3 endpoint for bucket")
export RCLONE_CONFIG_R2_TYPE=s3 RCLONE_CONFIG_R2_PROVIDER=Cloudflare RCLONE_CONFIG_R2_NO_CHECK_BUCKET=true
export RCLONE_CONFIG_R2_ACCESS_KEY_ID=$(_get "access key") RCLONE_CONFIG_R2_SECRET_ACCESS_KEY=$(_get "secret access key")
export RCLONE_CONFIG_R2_ENDPOINT=$(printf '%s' "$_ep" | sed -E 's|^(https://[^/]+).*|\1|') R2_BUCKET=$(printf '%s' "$_ep" | sed -E 's|^https://[^/]+/?||; s|/.*||')
unset _sec _ep; unset -f _get
