#!/usr/bin/env bash
# Remove the dedicated spot VPC and everything in it (security groups, subnets, route table, internet gateway).
# Refuses while any Project-tagged instance is still alive, and only touches a VPC tagged Project=<PROJECT_TAG>.
source "$(dirname "$0")/lib.sh"
check_account
VPC=$(awsc ec2 describe-vpcs --filters "Name=tag:Project,Values=$PROJECT_TAG" --query 'Vpcs[0].VpcId' --output text)
[ "$VPC" != "None" ] || { log "no Project-tagged VPC"; exit 0; }
LIVE=$(awsc ec2 describe-instances --filters "Name=vpc-id,Values=$VPC" "Name=instance-state-name,Values=pending,running,stopping,stopped,shutting-down" --query 'Reservations[].Instances[].InstanceId' --output text)
[ -z "$LIVE" ] || { echo "REFUSED: instances still in $VPC: $LIVE (aws/spot_down.sh --all first)" >&2; exit 4; }
for sg in $(awsc ec2 describe-security-groups --filters "Name=vpc-id,Values=$VPC" --query "SecurityGroups[?GroupName!='default'].GroupId" --output text); do awsc ec2 delete-security-group --group-id "$sg" && log "deleted SG $sg"; done
for s in $(awsc ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC" --query 'Subnets[].SubnetId' --output text); do awsc ec2 delete-subnet --subnet-id "$s" && log "deleted subnet $s"; done
for rt in $(awsc ec2 describe-route-tables --filters "Name=vpc-id,Values=$VPC" "Name=tag:Project,Values=$PROJECT_TAG" --query 'RouteTables[].RouteTableId' --output text); do awsc ec2 delete-route-table --route-table-id "$rt" && log "deleted route table $rt"; done
for igw in $(awsc ec2 describe-internet-gateways --filters "Name=attachment.vpc-id,Values=$VPC" --query 'InternetGateways[].InternetGatewayId' --output text); do
  awsc ec2 detach-internet-gateway --internet-gateway-id "$igw" --vpc-id "$VPC" && awsc ec2 delete-internet-gateway --internet-gateway-id "$igw" && log "deleted IGW $igw"; done
awsc ec2 delete-vpc --vpc-id "$VPC" && log "deleted VPC $VPC"
set_env VPC_ID ""; set_env SUBNET_IDS ""
