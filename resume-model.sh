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

# 4. Resume the cluster (scale nodes from 0 back to 2)
echo "Resuming EKS GPU node group (scaling nodes back to 2)..."
echo "This will take 5-10 minutes or more as new EC2 instances are launched and joined to the cluster."
# Scale the desired count back to 2, matching your original deployment intent.
# Again, min/max settings of the nodegroup itself are not altered by this command.
eksctl scale nodegroup \
  --cluster=$CLUSTER_NAME \
  --name=$NODEGROUP_NAME \
  --nodes=2
  # Removed --nodes-min and --nodes-max to keep original nodegroup settings intact

echo "EKS Node Group '$NODEGROUP_NAME' in cluster '$CLUSTER_NAME' is RESUMING. Scaling to 2 nodes."
echo "Wait ~5-10 minutes (or longer depending on instance availability) for the nodes to be ready and pods to start."
echo "You can check node status with: kubectl get nodes -w"
echo "You can check pod status with: kubectl get pods -n nim -w"