#!/usr/bin/env bash
# Simple prepare + pre-check for EKS deploys.
# Usage:
#   ./predeploy-prepare.sh [--region REGION] [--cluster NAME] [--namespace NAMESPACE] [--fix] [--auto]
# Flags:
#   --fix    : in pre-check, attempt to delete conflicting daemonsets
#   --auto   : automatically delete detected CFN stacks that look like stale EKS stacks and stale kubeconfig contexts
set -euo pipefail

REGION="${AWS_REGION:-}"
CLUSTER=""
NAMESPACE="kube-system"
FIX=0
AUTO=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --region) REGION="$2"; shift 2 ;;
    --cluster) CLUSTER="$2"; shift 2 ;;
    --namespace) NAMESPACE="$2"; shift 2 ;;
    --fix) FIX=1; shift ;;
    --auto) AUTO=1; shift ;;
    -h|--help) echo "Usage: $0 [--region REGION] [--cluster NAME] [--namespace NAMESPACE] [--fix] [--auto]"; exit 0 ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

if [ -z "$REGION" ]; then
  REGION=$(aws configure get region || true)
  if [ -z "$REGION" ]; then
    echo "AWS region not set. Provide --region or set AWS_REGION/AWS CLI default."
    exit 1
  fi
fi

# Check AWS credentials
echo "Checking AWS credentials..."
if ! aws sts get-caller-identity --region "$REGION" >/dev/null 2>&1; then
  echo "ERROR: AWS credentials not working in region $REGION. Export AWS_PROFILE or AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY."
  exit 1
fi
echo "AWS credentials OK (region $REGION)."

# List clusters
echo
echo "Listing EKS clusters in $REGION..."
CLUSTERS=$(aws eks list-clusters --region "$REGION" --query "clusters" --output text || true)

if [ -z "$CLUSTERS" ]; then
  echo "No EKS clusters found in $REGION."

  # detect possibly-stale CloudFormation stacks that likely reference EKS (names containing 'eks'/'Eks')
  echo
  echo "Looking for CloudFormation stacks with names containing 'eks' (possible stale stacks)..."
  STKS=$(aws cloudformation list-stacks \
    --stack-status-filter CREATE_IN_PROGRESS CREATE_FAILED ROLLBACK_IN_PROGRESS ROLLBACK_FAILED UPDATE_ROLLBACK_FAILED UPDATE_IN_PROGRESS \
    --region "$REGION" \
    --query "StackSummaries[?contains(StackName, \`eks\`) || contains(StackName, \`Eks\`) || contains(StackName, \`EKS\`)].StackName" \
    --output text || true)

  if [ -z "$STKS" ]; then
    echo "No suspicious CFN stacks found. You can proceed to create a cluster (cdk deploy)."
  else
    echo "Detected CloudFormation stacks that may be stale:"
    echo "$STKS"
    if [ "$AUTO" -eq 1 ]; then
      echo "AUTO mode: deleting these stacks..."
      for s in $STKS; do
        echo "Deleting stack: $s"
        aws cloudformation delete-stack --stack-name "$s" --region "$REGION"
      done
      echo "Requested deletion. Monitor with: aws cloudformation list-stacks --region $REGION"
    else
      echo "Run with --auto to delete these stacks automatically, or inspect and delete manually:"
      echo "  aws cloudformation delete-stack --stack-name STACKNAME --region $REGION"
      echo "After clearing stacks, re-run this script."
      exit 0
    fi
  fi
  # exit so user can wait for deletions to finish before continuing
  echo "No clusters present. Exiting so you can recreate the cluster (cdk deploy)."
  exit 0
fi

# If user provided a cluster name, prefer that
if [ -n "$CLUSTER" ]; then
  if ! echo "$CLUSTERS" | grep -qw "$CLUSTER"; then
    echo "Specified cluster '$CLUSTER' not found in region $REGION. Available clusters:"
    echo "$CLUSTERS"
    exit 1
  fi
  SELECTED_CLUSTER="$CLUSTER"
else
  # if single cluster, pick it; if multiple, pick first and show list
  COUNT=$(echo "$CLUSTERS" | wc -w)
  if [ "$COUNT" -eq 1 ]; then
    SELECTED_CLUSTER="$CLUSTERS"
  else
    echo "Multiple clusters found in $REGION:"
    echo "$CLUSTERS"
    echo "Pick one with --cluster NAME"
    exit 1
  fi
fi

echo
echo "Selected cluster: $SELECTED_CLUSTER"

# Clean stale kubectl contexts that point to dead endpoints
echo
echo "Cleaning stale kubectl contexts (contexts that cannot reach their API server)..."
CONTEXTS=$(kubectl config get-contexts -o name 2>/dev/null || true)
if [ -z "$CONTEXTS" ]; then
  echo "No kubectl contexts found."
else
  STALE=()
  for ctx in $CONTEXTS; do
    if ! kubectl --context "$ctx" cluster-info >/dev/null 2>&1; then
      STALE+=("$ctx")
    fi
  done
  if [ "${#STALE[@]}" -eq 0 ]; then
    echo "No stale contexts detected."
  else
    echo "Stale contexts: ${STALE[*]}"
    if [ "$AUTO" -eq 1 ]; then
      for ctx in "${STALE[@]}"; do
        cluster_name=$(kubectl config view -o "jsonpath={.contexts[?(@.name==\"$ctx\")].context.cluster}" 2>/dev/null || true)
        echo "Deleting context $ctx and cluster config $cluster_name"
        kubectl config delete-context "$ctx" || true
        if [ -n "$cluster_name" ]; then
          kubectl config delete-cluster "$cluster_name" || true
        fi
      done
    else
      echo "Run with --auto to remove these contexts automatically, or remove them manually:"
      for ctx in "${STALE[@]}"; do
        echo "  kubectl config delete-context $ctx"
      done
      echo "Re-run this script after cleaning contexts."
      exit 1
    fi
  fi
fi

# Refresh kubeconfig for the selected cluster
echo
echo "Updating kubeconfig for cluster $SELECTED_CLUSTER..."
aws eks update-kubeconfig --name "$SELECTED_CLUSTER" --region "$REGION"
echo "kubectl context is now: $(kubectl config current-context || true)"

# Run pre-deploy check (helm + daemonset)
echo
echo "Running pre-deploy check in namespace: $NAMESPACE"
echo "--- Helm releases in namespace $NAMESPACE ---"
helm list -n "$NAMESPACE" || true

echo
echo "--- Searching for daemonsets matching 'nvidia' or 'device-plugin' in $NAMESPACE ---"
DS=$(kubectl get daemonset -n "$NAMESPACE" --no-headers -o custom-columns=":metadata.name" 2>/dev/null | grep -E 'nvidia|device-plugin' || true)

if [ -z "$DS" ]; then
  echo "No matching daemonsets found."
else
  echo "Found daemonsets:"
  echo "$DS"
  if [ "$FIX" -eq 1 ]; then
    echo "Deleting found daemonsets..."
    while IFS= read -r dsname; do
      [ -z "$dsname" ] && continue
      echo "Deleting daemonset: $dsname"
      kubectl delete daemonset "$dsname" -n "$NAMESPACE" --ignore-not-found || true
      echo "Waiting for $dsname to be removed..."
      kubectl wait --for=delete daemonset/"$dsname" -n "$NAMESPACE" --timeout=120s || true
    done <<< "$DS"
    echo "Deletion attempts finished. Re-run this script to verify."
    exit 0
  else
    echo "If these are orphaned resources (Helm release missing) run again with --fix to delete them."
  fi
fi

echo
echo "Pre-check complete. If all good, you can now run your deploy script (e.g. ./deploy-model.sh)."