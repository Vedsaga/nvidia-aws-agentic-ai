#!/bin/bash
set -e # Stop on error

echo "********************************************"
echo "*** RUNNING "GOLDEN WORKFLOW" FOR KUBECTL ***"
echo "********************************************"

# 1. Activate venv
echo "[1/7] Activating Python venv..."
source .venv/bin/activate

# 2. Load .env credentials
echo "[2/7] Loading .env credentials..."
if [ ! -f .env ]; then
    echo "ERROR: .env file not found."
    exit 1
fi
export $(grep -v '^#' .env | xargs)

# 3. Create 'hackathon' profile
echo "[3/7] Hard-setting AWS credentials to 'hackathon' profile..."
aws configure --profile hackathon set aws_access_key_id $AWS_ACCESS_KEY_ID
aws configure --profile hackathon set aws_secret_access_key $AWS_SECRET_ACCESS_KEY
aws configure --profile hackathon set aws_session_token $AWS_SESSION_TOKEN
aws configure --profile hackathon set region $AWS_REGION

# 4. Nuke old config
echo "[4/7] Cleaning stale kubectl config..."
rm -f ~/.kube/config

# 5. Re-authenticate kubectl
echo "[5/7] Re-authenticating kubectl with 'hackathon' profile..."
CLUSTER_NAME=$(aws eks list-clusters --query "clusters[0]" --output text)
aws eks update-kubeconfig --name $CLUSTER_NAME --region us-east-1 --profile hackathon

# 6. Fix PATH
echo "[6/7] Setting PATH for kubectl..."
export PATH=$PATH:$HOME/bin

# 7. Run kubectl!
echo "[7/7] Login successful! Watching pods in 'nim' namespace..."
echo "Press Ctrl+C to stop watching."
echo "---------------------------------------------------------"

kubectl get pods -n nim -w
