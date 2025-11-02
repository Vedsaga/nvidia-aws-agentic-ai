#!/bin/bash
set -e

source .env

CLUSTER_NAME=$(aws eks list-clusters --query "clusters[0]" --output text)
[ "$CLUSTER_NAME" = "None" ] && echo "ERROR: No cluster found" && exit 1

echo "Resuming cluster: $CLUSTER_NAME"
echo "Scaling to 2 nodes. This takes 8-12 minutes."

# Scale ALL nodegroups to 2
for ng in $(aws eks list-nodegroups --cluster-name $CLUSTER_NAME --query "nodegroups[]" --output text); do
    echo "Scaling nodegroup: $ng to 2..."
    aws eks update-nodegroup-config \
        --cluster-name $CLUSTER_NAME \
        --nodegroup-name $ng \
        --scaling-config minSize=2,maxSize=2,desiredSize=2
done

echo "✓ Nodes starting up..."
echo "Wait 8-12 minutes, then run: ./check-status.sh"