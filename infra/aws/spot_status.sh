#!/usr/bin/env bash
# List every Project-tagged instance in the region with state, type, AZ, age and the current spot price for its type/AZ.
source "$(dirname "$0")/lib.sh"
check_account
awsc ec2 describe-instances --filters "Name=tag:Project,Values=$PROJECT_TAG" \
  --query 'Reservations[].Instances[].[InstanceId,State.Name,InstanceType,Placement.AvailabilityZone,LaunchTime,PublicIpAddress]' --output text |
while read -r id st ty az lt ip; do
  p=$(awsc ec2 describe-spot-price-history --instance-types "$ty" --availability-zone "$az" --product-descriptions "Linux/UNIX" --max-items 1 --query 'SpotPriceHistory[0].SpotPrice' --output text 2>/dev/null | head -1)
  echo "$id  $st  $ty  $az  launched $lt  ip $ip  spot now \$$p/h"
done
