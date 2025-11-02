#!/bin/bash
set -e # Exit immediately if a command fails

echo "Pausing EKS GPU node to save costs..."
echo "This scales 'main-gpu-nodegroup' to 0 nodes."

# Assumes 'HackathonCluster' and 'main-gpu-nodegroup' are your cluster/nodegroup names
# (These names come from your 'eks_stack.py' file)
eksctl scale nodegroup \
  --cluster=HackathonCluster \
  --name=main-gpu-nodegroup \
  --nodes=0 \
  --nodes-min=0 \
  --nodes-max=1

echo "Model is PAUSED. Run resume-model.sh to restart."
