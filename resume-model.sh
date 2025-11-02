#!/bin/bash
set -e # Exit immediately if a command fails

echo "Resuming EKS GPU node..."
echo "This scales 'main-gpu-nodegroup' to 1 node. Please wait ~5 minutes."

# Assumes 'HackathonCluster' and 'main-gpu-nodegroup' are your cluster/nodegroup names
eksctl scale nodegroup \
  --cluster=HackathonCluster \
  --name=main-gpu-nodegroup \
  --nodes=1 \
  --nodes-min=1 \
  --nodes-max=1

echo "Model is RESUMING. Wait ~5 minutes for the node to be ready and models to load."
