#!/usr/bin/env bash
# Request one spot instance, bootstrap it (villa vesuvius env, VC3D AppImage, ink checkpoints), wait until ready.
# Usage: aws/spot_up.sh            (state written to aws/state/: instance_id, instance_ip, launched_at)
source "$(dirname "$0")/lib.sh"
check_account
[ -n "$(instance_id)" ] && { echo "an instance is already recorded in aws/state ($(instance_id)); run aws/spot_down.sh first" >&2; exit 4; }

# key pair (ed25519), private key kept locally
if ! awsc ec2 describe-key-pairs --key-names "$KEY_NAME" >/dev/null 2>&1; then
  log "creating key pair $KEY_NAME"
  awsc ec2 create-key-pair --key-name "$KEY_NAME" --key-type ed25519 \
    --tag-specifications "ResourceType=key-pair,Tags=[{Key=Project,Value=$PROJECT_TAG}]" --query KeyMaterial --output text > "$SSH_KEY"
  chmod 600 "$SSH_KEY"
fi
[ -s "$SSH_KEY" ] || { echo "key pair $KEY_NAME exists in AWS but $SSH_KEY is missing locally; delete the key pair or restore the file" >&2; exit 5; }

# security group in VPC_ID: SSH from this Mac's current public IP only
VPC=$VPC_ID
awsc ec2 describe-vpcs --vpc-ids "$VPC" >/dev/null || { echo "VPC $VPC not found in $AWS_REGION" >&2; exit 6; }
SG=$(awsc ec2 describe-security-groups --filters Name=vpc-id,Values="$VPC" Name=group-name,Values="$SG_NAME" --query 'SecurityGroups[0].GroupId' --output text)
if [ "$SG" = "None" ]; then
  log "creating security group $SG_NAME"
  SG=$(awsc ec2 create-security-group --group-name "$SG_NAME" --description "scroll-prize spot: SSH from operator IP" --vpc-id "$VPC" \
       --tag-specifications "ResourceType=security-group,Tags=[{Key=Project,Value=$PROJECT_TAG}]" --query GroupId --output text)
fi
MYIP=$(curl -s https://checkip.amazonaws.com | tr -d '[:space:]')
awsc ec2 authorize-security-group-ingress --group-id "$SG" --protocol tcp --port 22 --cidr "$MYIP/32" >/dev/null 2>&1 || true
log "security group $SG allows SSH from $MYIP"

# AMI + root device
AMI=$(awsc ssm get-parameter --name "$AMI_SSM" --query Parameter.Value --output text)
ROOTDEV=$(awsc ec2 describe-images --image-ids "$AMI" --query 'Images[0].RootDeviceName' --output text)
log "AMI $AMI ($ROOTDEV) from $AMI_SSM"

# user-data
UD=$STATE/userdata.sh
sed -e "s|@MAX_MINUTES@|$(( MAX_HOURS * 60 ))|g" -e "s|@VILLA_COMMIT@|$VILLA_COMMIT|g" -e "s|@VC3D_RELEASE@|$VC3D_RELEASE|g" "$HERE/userdata.sh.tmpl" > "$UD"

NAME="$PROJECT_TAG-spot-$(date -u +%Y%m%d-%H%M%S)"
log "requesting $INSTANCE_TYPE spot (max \$$MAX_PRICE/h, hard limit ${MAX_HOURS}h)"
IID=""
for SUBNET in $SUBNET_IDS; do
  log "trying subnet $SUBNET"
  if IID=$(awsc ec2 run-instances --image-id "$AMI" --instance-type "$INSTANCE_TYPE" --key-name "$KEY_NAME" \
    --network-interfaces "[{\"DeviceIndex\":0,\"SubnetId\":\"$SUBNET\",\"Groups\":[\"$SG\"],\"AssociatePublicIpAddress\":true,\"DeleteOnTermination\":true}]" \
    --instance-market-options "{\"MarketType\":\"spot\",\"SpotOptions\":{\"MaxPrice\":\"$MAX_PRICE\",\"SpotInstanceType\":\"one-time\",\"InstanceInterruptionBehavior\":\"terminate\"}}" \
    --instance-initiated-shutdown-behavior terminate \
    --block-device-mappings "[{\"DeviceName\":\"$ROOTDEV\",\"Ebs\":{\"VolumeSize\":$VOLUME_GB,\"VolumeType\":\"gp3\",\"DeleteOnTermination\":true}}]" \
    --metadata-options HttpTokens=required \
    --user-data "file://$UD" \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Project,Value=$PROJECT_TAG},{Key=Name,Value=$NAME}]" "ResourceType=volume,Tags=[{Key=Project,Value=$PROJECT_TAG}]" \
    --query 'Instances[0].InstanceId' --output text 2> "$STATE/run-instances.err"); then
    break
  fi
  log "subnet $SUBNET failed: $(tail -1 "$STATE/run-instances.err")"; IID=""
done
[ -n "$IID" ] || { echo "spot request failed in every subnet (see aws/state/run-instances.err)" >&2; exit 7; }
echo "$IID" > "$STATE/instance_id"; date -u +%s > "$STATE/launched_at"; echo "$INSTANCE_TYPE" > "$STATE/instance_type"
log "instance $IID requested; waiting for running"
awsc ec2 wait instance-running --instance-ids "$IID"
IP=$(awsc ec2 describe-instances --instance-ids "$IID" --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)
echo "$IP" > "$STATE/instance_ip"; log "running at $IP"

log "waiting for SSH"
for _ in $(seq 1 40); do rssh true 2>/dev/null && break; sleep 10; done
log "waiting for bootstrap (uv env, VC3D AppImage, checkpoints; ~15-25 min)"
t0=$(date +%s)
while true; do
  st=$(rssh 'test -f /opt/scroll/BOOTSTRAP-DONE && echo done || (test -f /opt/scroll/BOOTSTRAP-FAILED && echo failed) || echo wait' 2>/dev/null || echo wait)
  [ "$st" = done ] && break
  [ "$st" = failed ] && { rssh 'tail -30 /var/log/scroll-bootstrap.log'; echo "BOOTSTRAP FAILED (instance left running for inspection; aws/spot_down.sh to terminate)" >&2; exit 7; }
  [ $(( $(date +%s) - t0 )) -gt 2700 ] && { echo "bootstrap timeout (45 min)" >&2; exit 8; }
  sleep 30
done
rssh 'cat /opt/scroll/bootstrap.times /opt/scroll/torch.txt; head -15 /opt/scroll/nvidia-smi.txt | grep -E "Driver|NVIDIA|MiB"'
log "READY: $IID $IP (bootstrap $(( ($(date +%s) - t0) / 60 )) min)"
