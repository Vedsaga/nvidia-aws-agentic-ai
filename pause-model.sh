#!/bin/bash
set -e # Exit immediately if a command fails

# 1. Load credentials
if [ ! -f .env ]; then
    echo "ERROR: .env file not found."
    exit 1
fi
export $(grep -v '^#' .env | xargs)

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

# 4. Pause the cluster (scale node from 1 to 0)
echo "Pausing EKS GPU node (scaling to 0) to save costs..."
eksctl scale nodegroup \
  --cluster=$CLUSTER_NAME \
  --name=$NODEGROUP_NAME \
  --nodes=0 \
  --nodes-min=0 \
  --nodes-max=1

echo "Model is PAUSED."
