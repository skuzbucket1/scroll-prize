#!/usr/bin/env bash
# Terminate the recorded instance (default), or every instance tagged Project=<tag> in the region (--all).
# --cleanup also deletes the security group and key pair (and the local private key). Never touches untagged resources.
source "$(dirname "$0")/lib.sh"
check_account
ALL=0; CLEAN=0; for a in "$@"; do case $a in --all) ALL=1;; --cleanup) CLEAN=1;; esac; done
if [ $ALL -eq 1 ]; then
  IDS=$(awsc ec2 describe-instances --filters "Name=tag:Project,Values=$PROJECT_TAG" "Name=instance-state-name,Values=pending,running,stopping,stopped" --query 'Reservations[].Instances[].InstanceId' --output text)
else
  IDS=$(instance_id)
fi
if [ -n "$IDS" ] && [ "$IDS" != "None" ]; then
  KILL=""
  for i in $IDS; do
    tag=$(awsc ec2 describe-instances --instance-ids "$i" --query "Reservations[0].Instances[0].Tags[?Key=='Project'].Value | [0]" --output text 2>/dev/null || echo "")
    [ "$tag" = "$PROJECT_TAG" ] || { echo "REFUSED: $i is not tagged Project=$PROJECT_TAG" >&2; continue; }
    log "terminating $i"; awsc ec2 terminate-instances --instance-ids "$i" >/dev/null; KILL="$KILL $i"
  done
  [ -n "$KILL" ] && awsc ec2 wait instance-terminated --instance-ids $KILL && log "terminated:$KILL"
  if [ -f "$STATE/launched_at" ]; then
    h=$(python3 -c "import time; print(round((time.time()-$(cat "$STATE/launched_at"))/3600, 2))")
    log "ran ~${h} h; at the spot ceiling of \$$MAX_PRICE/h that is at most \$$(python3 -c "print(round($h*$MAX_PRICE, 2))") (actual spot price is lower)"
  fi
else
  log "no instance to terminate"
fi
LEFT=$(awsc ec2 describe-volumes --filters "Name=tag:Project,Values=$PROJECT_TAG" --query 'Volumes[].VolumeId' --output text)
[ -n "$LEFT" ] && log "note: tagged volumes still listed: $LEFT (delete-on-termination removes them within minutes)"
rm -f "$STATE/instance_id" "$STATE/instance_ip" "$STATE/launched_at" "$STATE/instance_type"
if [ $CLEAN -eq 1 ]; then
  SG=$(awsc ec2 describe-security-groups --filters Name=vpc-id,Values="$VPC_ID" Name=group-name,Values="$SG_NAME" "Name=tag:Project,Values=$PROJECT_TAG" --query 'SecurityGroups[0].GroupId' --output text)
  [ "$SG" != "None" ] && awsc ec2 delete-security-group --group-id "$SG" && log "deleted security group $SG"
  awsc ec2 delete-key-pair --key-name "$KEY_NAME" && rm -f "$SSH_KEY" && log "deleted key pair $KEY_NAME"
fi
