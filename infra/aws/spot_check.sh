#!/usr/bin/env bash
# Read-only readiness check (creates nothing): account, VPC/subnets, internet routes, quota, AMI, current spot prices.
source "$(dirname "$0")/lib.sh"
check_account; log "account $EXPECTED_ACCOUNT_ID via profile $AWS_PROFILE: OK"
awsc ec2 describe-vpcs --vpc-ids "$VPC_ID" --query 'Vpcs[0].[VpcId,CidrBlock]' --output text
for s in $SUBNET_IDS; do
  az=$(awsc ec2 describe-subnets --subnet-ids "$s" --query 'Subnets[0].AvailabilityZone' --output text)
  gw=$(awsc ec2 describe-route-tables --filters Name=association.subnet-id,Values="$s" --query "RouteTables[0].Routes[?DestinationCidrBlock=='0.0.0.0/0'].GatewayId | [0]" --output text)
  p=$(awsc ec2 describe-spot-price-history --instance-types "$INSTANCE_TYPE" --availability-zone "$az" --product-descriptions "Linux/UNIX" --max-items 1 --query 'SpotPriceHistory[0].SpotPrice' --output text | head -1)
  echo "subnet $s  $az  default route -> $gw  $INSTANCE_TYPE spot now \$$p/h"
done
awsc service-quotas get-service-quota --service-code ec2 --quota-code L-3819A6DF --query 'Quota.[QuotaName,Value]' --output text
echo "AMI $(awsc ssm get-parameter --name "$AMI_SSM" --query Parameter.Value --output text)"
