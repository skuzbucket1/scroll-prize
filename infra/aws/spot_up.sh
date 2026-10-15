#!/usr/bin/env bash
# Request one instance (spot, on-demand, or spot first then on-demand: MARKET), bootstrap it (villa vesuvius env, VC3D AppImage, ink checkpoints), wait until ready.
# Usage: infra/aws/spot_up.sh            (state written to infra/aws/state/: instance_id, instance_ip, launched_at)
source "$(dirname "$0")/lib.sh"
check_account
require_net
[ -n "$(instance_id)" ] && { echo "an instance is already recorded in infra/aws/state ($(instance_id)); run infra/aws/spot_down.sh first" >&2; exit 4; }

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
UD=$ISTATE/userdata.sh
sed -e "s|@MAX_MINUTES@|$(( ${FLEET_MAX_HOURS:-$MAX_HOURS} * 60 ))|g" -e "s|@VILLA_COMMIT@|$VILLA_COMMIT|g" -e "s|@VC3D_RELEASE@|$VC3D_RELEASE|g" "$HERE/userdata.sh.tmpl" > "$UD"

NAME="$PROJECT_TAG-${WORKER_NAME:-spot}-$(date -u +%Y%m%d-%H%M%S)"
# MARKET: spot (ceiling MAX_PRICE) | ondemand | spot-then-ondemand: every type on spot first, cheapest zone first, and only
# where its spot price is at most SPOT_MAX_FRACTION (default 0.6) of the on-demand price (that is also the bid ceiling;
# 2026-10-13 the first zone tried gave g5.4xlarge spot at $1.48 against $1.62 on-demand), then the same list on-demand.
# spot-fraction: spot only, with the same fraction ceiling (the caller falls back to on-demand itself, e.g. after waiting
# RETRY_MINUTES for spot capacity). An interrupted spot instance is terminated, not resumed.
case ${MARKET:-spot} in spot|spot-fraction) MARKETS=spot;; ondemand) MARKETS=ondemand;; spot-then-ondemand) MARKETS="spot ondemand";;
  *) echo "MARKET must be spot, ondemand or spot-then-ondemand (got $MARKET)" >&2; exit 2;; esac
log "requesting ${MARKETS// / then } (types: ${INSTANCE_TYPES:-$INSTANCE_TYPE}; hard limit ${FLEET_MAX_HOURS:-$MAX_HOURS}h)"
ondemand_price(){ case $1 in g5.4xlarge) echo 1.624;; g6.4xlarge) echo 1.323;; g5.2xlarge) echo 1.212;; g6.2xlarge) echo 0.9776;;
  g5.xlarge) echo 1.006;; g6.xlarge) echo 0.8048;; g4dn.2xlarge) echo 0.752;; g4dn.xlarge) echo 0.526;; *) echo "";; esac; }   # us-east-1 Linux
SUBNET_AZ=$(awsc ec2 describe-subnets --subnet-ids $SUBNET_IDS --query 'Subnets[].[SubnetId,AvailabilityZone]' --output text || true)
market_opts(){ MARKET_OPTS=(); SUBS=$SUBNET_IDS
  [ $MK = ondemand ] && return
  local cap="" od p
  if [ "${MARKET:-spot}" = spot ]; then cap=$MAX_PRICE
  else od=$(ondemand_price $INSTANCE_TYPE)
    if [ -n "$od" ]; then
      cap=$(python3 -c "print(round($od * ${SPOT_MAX_FRACTION:-0.6}, 4))")
      SUBS=$(while read -r s az; do
          [ -n "$az" ] || continue
          p=$(awsc ec2 describe-spot-price-history --instance-types $INSTANCE_TYPE --availability-zone $az --product-descriptions Linux/UNIX \
              --max-items 1 --query 'SpotPriceHistory[0].SpotPrice' --output text 2>/dev/null | head -1 || true)
          if [[ "$p" =~ ^[0-9.]+$ ]] && python3 -c "import sys; sys.exit(0 if $p <= $cap else 1)"; then echo "$p $s"; fi
        done <<< "$SUBNET_AZ" | sort -n | awk '{print $2}' || true)
      log "spot $INSTANCE_TYPE: ceiling \$$cap/h (${SPOT_MAX_FRACTION:-0.6} x on-demand \$$od); $(echo $SUBS | wc -w | tr -d ' ') zone(s) under it, cheapest first"
    fi
  fi
  [ -n "$cap" ] && cap="\"MaxPrice\":\"$cap\","
  MARKET_OPTS=(--instance-market-options "{\"MarketType\":\"spot\",\"SpotOptions\":{$cap\"SpotInstanceType\":\"one-time\",\"InstanceInterruptionBehavior\":\"terminate\"}}"); }
IID=""; TYPES=${INSTANCE_TYPES:-$INSTANCE_TYPE}; DEADLINE=$(( $(date +%s) + ${RETRY_MINUTES:-0} * 60 ))
while [ -z "$IID" ]; do
for MK in $MARKETS; do
for INSTANCE_TYPE in $TYPES; do
market_opts
for SUBNET in $SUBS; do
  log "trying $INSTANCE_TYPE $MK in subnet $SUBNET"
  if IID=$(awsc ec2 run-instances --image-id "$AMI" --instance-type "$INSTANCE_TYPE" --key-name "$KEY_NAME" \
    --network-interfaces "[{\"DeviceIndex\":0,\"SubnetId\":\"$SUBNET\",\"Groups\":[\"$SG\"],\"AssociatePublicIpAddress\":true,\"DeleteOnTermination\":true}]" \
    "${MARKET_OPTS[@]}" \
    --instance-initiated-shutdown-behavior terminate \
    --block-device-mappings "[{\"DeviceName\":\"$ROOTDEV\",\"Ebs\":{\"VolumeSize\":$VOLUME_GB,\"VolumeType\":\"gp3\",\"DeleteOnTermination\":true}}]" \
    --metadata-options HttpTokens=required \
    --user-data "file://$UD" \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Project,Value=$PROJECT_TAG},{Key=Name,Value=$NAME}]" "ResourceType=volume,Tags=[{Key=Project,Value=$PROJECT_TAG}]" \
    --query 'Instances[0].InstanceId' --output text 2> "$ISTATE/run-instances.err"); then
    break 3
  fi
  log "  no: $(tail -1 "$ISTATE/run-instances.err" | grep -oE '\((InsufficientInstanceCapacity|SpotMaxPriceTooLow|MaxSpotInstanceCountExceeded|[A-Za-z]+)\)' | head -1)"; IID=""
done
done
done
[ -n "$IID" ] && break
[ "$(date +%s)" -lt "$DEADLINE" ] || break
log "no capacity in any type/subnet; retrying in 2 min (until $(date -u -d @$DEADLINE +%H:%M 2>/dev/null || date -u -r $DEADLINE +%H:%M) UTC)"; sleep 120
done
[ -n "$IID" ] || { echo "request failed for every market/type/subnet (see infra/aws/state/run-instances.err)" >&2; exit 7; }
log "got $INSTANCE_TYPE $MK in $SUBNET"
echo "$IID" > "$ISTATE/instance_id"; date -u +%s > "$ISTATE/launched_at"; echo "$INSTANCE_TYPE" > "$ISTATE/instance_type"; echo "$MK" > "$ISTATE/market"
log "instance $IID requested; waiting for running"
awsc ec2 wait instance-running --instance-ids "$IID"
if [ $MK = spot ]; then   # the spot price at launch, for the cost line in spot_down.sh
  AZ=$(awsc ec2 describe-instances --instance-ids "$IID" --query 'Reservations[0].Instances[0].Placement.AvailabilityZone' --output text)
  SP=$(awsc ec2 describe-spot-price-history --instance-types "$INSTANCE_TYPE" --availability-zone "$AZ" --product-descriptions "Linux/UNIX" \
       --max-items 1 --query 'SpotPriceHistory[0].SpotPrice' --output text 2>/dev/null | head -1)
  [[ "$SP" =~ ^[0-9.]+$ ]] && echo "$SP" > "$ISTATE/price" && log "spot in $AZ at \$$SP/h"
fi
IP=$(awsc ec2 describe-instances --instance-ids "$IID" --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)
if [[ "$IP" == 100.* ]] && [ "${IP_RETRY:-0}" -lt 4 ]; then   # 2026-10-13: the Mac routes 100.0.0.0/8 into the Tailscale tailnet
  log "public IP $IP is in 100.0.0.0/8, which this Mac sends into the tailnet (no SSH): terminating it and retrying"
  awsc ec2 terminate-instances --instance-ids "$IID" > /dev/null
  rm -f "$ISTATE/instance_id" "$ISTATE/instance_ip" "$ISTATE/launched_at" "$ISTATE/instance_type" "$ISTATE/market" "$ISTATE/price"
  IP_RETRY=$(( ${IP_RETRY:-0} + 1 )) exec bash "$0" "$@"
fi
echo "$IP" > "$ISTATE/instance_ip"; log "running at $IP"

log "waiting for SSH"
for _ in $(seq 1 40); do rssh true 2>/dev/null && break; sleep 10; done
log "waiting for bootstrap (uv env, VC3D AppImage, checkpoints; ~2-5 min)"
t0=$(date +%s)
while true; do
  st=$(rssh 'test -f /opt/scroll/BOOTSTRAP-DONE && echo done || (test -f /opt/scroll/BOOTSTRAP-FAILED && echo failed) || echo wait' 2>/dev/null || echo wait)
  [ "$st" = done ] && break
  [ "$st" = failed ] && { rssh 'tail -30 /var/log/scroll-bootstrap.log'; echo "BOOTSTRAP FAILED (instance left running for inspection; infra/aws/spot_down.sh to terminate)" >&2; exit 7; }
  [ $(( $(date +%s) - t0 )) -gt 2700 ] && { echo "bootstrap timeout (45 min)" >&2; exit 8; }
  sleep 30
done
rssh 'cat /opt/scroll/bootstrap.times /opt/scroll/torch.txt; head -15 /opt/scroll/nvidia-smi.txt | grep -E "Driver|NVIDIA|MiB"'
log "READY: $IID $IP (bootstrap $(( ($(date +%s) - t0) / 60 )) min)"
