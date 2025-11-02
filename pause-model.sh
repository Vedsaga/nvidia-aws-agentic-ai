#!/bin/bash
set -e

source .env

CLUSTER_NAME=$(aws eks list-clusters --query "clusters[0]" --output text)
[ "$CLUSTER_NAME" = "None" ] && echo "ERROR: No cluster found" && exit 1

echo "⚠ Pausing cluster: $CLUSTER_NAME"
echo "This will scale BOTH nodes to 0 to save costs (~$1/hr)"

# Scale ALL nodegroups to 0
for ng in $(aws eks list-nodegroups --cluster-name $CLUSTER_NAME --query "nodegroups[]" --output text); do
    echo "Scaling nodegroup: $ng to 0..."
    aws eks update-nodegroup-config \
        --cluster-name $CLUSTER_NAME \
        --nodegroup-name $ng \
        --scaling-config minSize=0,maxSize=2,desiredSize=0
done

echo "✓ Cluster paused. Nodes scaling down (2-3 minutes)."
echo "Cost: ~$0.10/hr (EKS control plane only)"