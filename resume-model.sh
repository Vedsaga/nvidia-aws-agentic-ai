#!/bin/bash
set -e # Exit immediately if a command fails

# 1. Load the new 8-hour credentials
if [ ! -f .env ]; then
    echo "ERROR: .env file not found."
    exit 1
fi
export $(grep -v '^#' .env | xargs)

# 2. Find the *real* cluster name
echo "Finding EKS cluster..."
CLUSTER_NAME=$(aws eks list-clusters --query "clusters[0]" --output text)
if [ "$CLUSTER_NAME" == "None" ]; then
    echo "ERROR: No EKS cluster found. Have you run ./deploy-model.sh yet?"
    exit 1
fi
echo "Found cluster: $CLUSTER_NAME"

# 3. Find the *real* nodegroup name (the new, smart step)
echo "Finding EKS nodegroup..."
NODEGROUP_NAME=$(aws eks list-nodegroups --cluster-name $CLUSTER_NAME --query "nodegroups[0]" --output text)
if [ "$NODEGROUP_NAME" == "None" ]; then
    echo "ERROR: No nodegroup found in cluster $CLUSTER_NAME."
    exit 1
fi
echo "Found nodegroup: $NODEGROUP_NAME"

# 4. Resume the cluster (scale node from 0 to 1)
echo "Resuming EKS GPU node (scaling to 1)..."
echo "This will take 5-10 minutes."
eksctl scale nodegroup \
  --cluster=$CLUSTER_NAME \
  --name=$NODEGROUP_NAME \
  --nodes=1 \
  --nodes-min=1 \
  --nodes-max=1

echo "Model is RESUMING. Wait ~5-10 minutes for the node to be ready."
echo "You can check status with: kubectl get pods -n nim -w"
