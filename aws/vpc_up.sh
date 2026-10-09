#!/usr/bin/env bash
# Create (or reuse) a dedicated VPC for the spot workers: 10.77.0.0/16, internet gateway, one public route table,
# and ONE public subnet in the given zone. Writes VPC_ID and SUBNET_IDS into aws/spot.env. Everything is tagged
# Project=<PROJECT_TAG>; aws/vpc_down.sh removes all of it.
# Usage: aws/vpc_up.sh [zone=us-east-1c]          (run again with another zone to add a second subnet)
source "$(dirname "$0")/lib.sh"
check_account
AZ=${1:-us-east-1c}; CIDR=10.77.0.0/16
TAGS="Tags=[{Key=Project,Value=$PROJECT_TAG},{Key=Name,Value=$PROJECT_TAG}]"
VPC=$(awsc ec2 describe-vpcs --filters "Name=tag:Project,Values=$PROJECT_TAG" --query 'Vpcs[0].VpcId' --output text)
if [ "$VPC" = "None" ]; then
  VPC=$(awsc ec2 create-vpc --cidr-block $CIDR --tag-specifications "ResourceType=vpc,$TAGS" --query Vpc.VpcId --output text)
  awsc ec2 wait vpc-available --vpc-ids "$VPC"
  awsc ec2 modify-vpc-attribute --vpc-id "$VPC" --enable-dns-hostnames '{"Value":true}'
  log "created VPC $VPC ($CIDR)"
else log "reusing VPC $VPC"; fi
IGW=$(awsc ec2 describe-internet-gateways --filters "Name=attachment.vpc-id,Values=$VPC" --query 'InternetGateways[0].InternetGatewayId' --output text)
if [ "$IGW" = "None" ]; then
  IGW=$(awsc ec2 create-internet-gateway --tag-specifications "ResourceType=internet-gateway,$TAGS" --query InternetGateway.InternetGatewayId --output text)
  awsc ec2 attach-internet-gateway --internet-gateway-id "$IGW" --vpc-id "$VPC"; log "attached internet gateway $IGW"
fi
RT=$(awsc ec2 describe-route-tables --filters "Name=vpc-id,Values=$VPC" "Name=tag:Project,Values=$PROJECT_TAG" --query 'RouteTables[0].RouteTableId' --output text)
if [ "$RT" = "None" ]; then
  RT=$(awsc ec2 create-route-table --vpc-id "$VPC" --tag-specifications "ResourceType=route-table,$TAGS" --query RouteTable.RouteTableId --output text)
  awsc ec2 create-route --route-table-id "$RT" --destination-cidr-block 0.0.0.0/0 --gateway-id "$IGW" >/dev/null; log "route table $RT -> $IGW"
fi
SUB=$(awsc ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC" "Name=availability-zone,Values=$AZ" --query 'Subnets[0].SubnetId' --output text)
if [ "$SUB" = "None" ]; then
  N=$(awsc ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC" --query 'length(Subnets)' --output text)
  SUB=$(awsc ec2 create-subnet --vpc-id "$VPC" --availability-zone "$AZ" --cidr-block "10.77.$(( N + 1 )).0/24" \
        --tag-specifications "ResourceType=subnet,Tags=[{Key=Project,Value=$PROJECT_TAG},{Key=Name,Value=$PROJECT_TAG-$AZ}]" --query Subnet.SubnetId --output text)
  awsc ec2 modify-subnet-attribute --subnet-id "$SUB" --map-public-ip-on-launch
  awsc ec2 associate-route-table --route-table-id "$RT" --subnet-id "$SUB" >/dev/null
  log "public subnet $SUB in $AZ"
fi
SUBS=$(awsc ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC" "Name=tag:Project,Values=$PROJECT_TAG" --query 'Subnets[].SubnetId' --output text | tr '\t' ' ')
set_env VPC_ID "$VPC"; set_env SUBNET_IDS "$SUBS"
log "aws/spot.env: VPC_ID=$VPC SUBNET_IDS=$SUBS"
