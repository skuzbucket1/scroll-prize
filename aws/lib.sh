# Shared helpers for the aws/ scripts (sourced, not executed).
set -euo pipefail
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd); ROOT=$(cd "$HERE/.." && pwd)
[ -f "$HERE/spot.env" ] || { echo "aws/spot.env missing: copy aws/spot.env.example and set AWS_PROFILE and EXPECTED_ACCOUNT_ID" >&2; exit 2; }
# shellcheck disable=SC1091
source "$HERE/spot.env"
[ -n "${AWS_PROFILE:-}" ] || { echo "AWS_PROFILE is empty in aws/spot.env (no default on purpose)" >&2; exit 2; }
[ -n "${EXPECTED_ACCOUNT_ID:-}" ] || { echo "EXPECTED_ACCOUNT_ID is empty in aws/spot.env" >&2; exit 2; }
[ -n "${VPC_ID:-}" ] && [ -n "${SUBNET_IDS:-}" ] || { echo "VPC_ID and SUBNET_IDS must be set in aws/spot.env" >&2; exit 2; }
export AWS_PAGER=""
STATE=$HERE/state; mkdir -p "$STATE"; chmod 700 "$STATE"
SSH_KEY=$STATE/$KEY_NAME.pem
log(){ echo "[$(date -u +%H:%M:%S)] $*" >&2; }
awsc(){ aws --profile "$AWS_PROFILE" --region "$AWS_REGION" "$@"; }
check_account(){
  local acct; acct=$(awsc sts get-caller-identity --query Account --output text) || { echo "cannot authenticate with profile $AWS_PROFILE" >&2; exit 3; }
  [ "$acct" = "$EXPECTED_ACCOUNT_ID" ] || { echo "REFUSED: profile $AWS_PROFILE is account $acct, expected $EXPECTED_ACCOUNT_ID" >&2; exit 3; }
}
instance_id(){ cat "$STATE/instance_id" 2>/dev/null || true; }
instance_ip(){ cat "$STATE/instance_ip" 2>/dev/null || true; }
SSH_OPTS=(-i "$SSH_KEY" -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile="$STATE/known_hosts" -o ConnectTimeout=15 -o ServerAliveInterval=30 -o BatchMode=yes)
rssh(){ ssh "${SSH_OPTS[@]}" "ubuntu@$(instance_ip)" "$@"; }
rsync_to(){ rsync -a -e "ssh ${SSH_OPTS[*]}" "$1" "ubuntu@$(instance_ip):$2"; }
rsync_from(){ rsync -a -e "ssh ${SSH_OPTS[*]}" "${@:3}" "ubuntu@$(instance_ip):$1" "$2"; }
