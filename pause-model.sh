#!/bin/bash
set -e # Exit immediately if a command fails

# 1. Load credentials
source scripts/load_env.sh
load_env

# 2. Find the *real* cluster name
echo "Finding EKS cluster..."
CLUSTER_NAME=$(aws eks list-clusters --query "clusters[0]" --output text)
if [ "$CLUSTER_NAME" == "None" ]; then
    echo "ERROR: No EKS cluster found."
    exit 1
fi
echo "Found cluster: $CLUSTER_NAME"

# 3. Find the *real* nodegroup name
echo "Finding EKS nodegroup..."
NODEGROUP_NAME=$(aws eks list-nodegroups --cluster-name $CLUSTER_NAME --query "nodegroups[0]" --output text)
if [ "$NODEGROUP_NAME" == "None" ]; then
    echo "ERROR: No nodegroup found in cluster $CLUSTER_NAME."
    exit 1
fi
echo "Found nodegroup: $NODEGROUP_NAME"

# 4. Pause the cluster (scale nodes from 2 to 0)
echo "Pausing EKS GPU node group (scaling nodes to 0) to save costs..."
# Scale the desired count to 0. The actual min/max settings of the nodegroup remain unchanged in EKS.
# This command only changes the desired count for the moment.
eksctl scale nodegroup \
  --cluster=$CLUSTER_NAME \
  --name=$NODEGROUP_NAME \
  --nodes=0
  # Removed --nodes-min and --nodes-max to keep original nodegroup settings intact

echo "EKS Node Group '$NODEGROUP_NAME' in cluster '$CLUSTER_NAME' is PAUSED (0 nodes). Pods will be terminated."