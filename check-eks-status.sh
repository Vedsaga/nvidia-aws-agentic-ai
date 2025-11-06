#!/bin/bash
set -e

# Colors for better visibility
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Helper functions
print_header() {
    echo -e "\n${BOLD}${BLUE}========================================${NC}"
    echo -e "${BOLD}${BLUE}$1${NC}"
    echo -e "${BOLD}${BLUE}========================================${NC}\n"
}

print_step() {
    echo -e "${CYAN}▶ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# Main script
print_header "NIM DEPLOYMENT MONITOR - Enhanced Edition"

# 1. Activate venv
print_step "[1/9] Activating Python virtual environment..."
if [ -d ".venv" ]; then
    source .venv/bin/activate
    print_success "Virtual environment activated"
else
    print_error "Virtual environment not found at .venv/"
    exit 1
fi

# 2. Load .env credentials
print_step "[2/9] Loading environment credentials..."
source scripts/load_env.sh
load_env
print_success "Credentials loaded from .env"

# 3. Configure AWS profile
print_step "[3/9] Configuring AWS 'hackathon' profile..."
aws configure --profile hackathon set aws_access_key_id $AWS_ACCESS_KEY_ID
aws configure --profile hackathon set aws_secret_access_key $AWS_SECRET_ACCESS_KEY
aws configure --profile hackathon set aws_session_token $AWS_SESSION_TOKEN
aws configure --profile hackathon set region $AWS_REGION
print_success "AWS profile configured"

# 4. Clean kubectl config
print_step "[4/9] Cleaning stale kubectl configuration..."
rm -f ~/.kube/config
print_success "Old config removed"

# 5. Authenticate kubectl
print_step "[5/9] Authenticating kubectl with EKS cluster..."
CLUSTER_NAME=$(aws eks list-clusters --profile hackathon --query "clusters[0]" --output text 2>/dev/null)
if [ -z "$CLUSTER_NAME" ] || [ "$CLUSTER_NAME" = "None" ]; then
    print_error "No EKS cluster found in your AWS account"
    exit 1
fi
print_info "Found cluster: $CLUSTER_NAME"
aws eks update-kubeconfig --name $CLUSTER_NAME --region $AWS_REGION --profile hackathon >/dev/null 2>&1
print_success "kubectl authenticated successfully"

# 6. Verify kubectl connectivity
print_step "[6/9] Verifying cluster connectivity..."
if kubectl cluster-info >/dev/null 2>&1; then
    print_success "Cluster is reachable"
else
    print_error "Cannot connect to cluster"
    exit 1
fi

# 7. Check cluster resources
print_step "[7/9] Checking cluster resources..."
echo ""
echo -e "${BOLD}Node Status:${NC}"
kubectl get nodes -o custom-columns=NAME:.metadata.name,STATUS:.status.conditions[-1].type,ROLE:.metadata.labels."node\.kubernetes\.io/instance-type",AGE:.metadata.creationTimestamp --no-headers | while read line; do
    if [[ $line == *"Ready"* ]]; then
        echo -e "  ${GREEN}✓${NC} $line"
    else
        echo -e "  ${RED}✗${NC} $line"
    fi
done

echo ""
echo -e "${BOLD}GPU Availability:${NC}"
kubectl get nodes -o json | jq -r '.items[] | "\(.metadata.name): \(.status.allocatable."nvidia.com/gpu" // "0") GPUs"' | while read line; do
    if [[ $line == *": 0 "* ]] || [[ $line == *'null'* ]]; then
        echo -e "  ${RED}✗${NC} $line"
    else
        echo -e "  ${GREEN}✓${NC} $line"
    fi
done

# 8. Check NIM namespace and deployments
print_step "[8/9] Checking NIM deployments in 'nim' namespace..."
echo ""

if ! kubectl get namespace nim >/dev/null 2>&1; then
    print_warning "Namespace 'nim' does not exist yet"
else
    print_success "Namespace 'nim' exists"

    echo ""
    echo -e "${BOLD}Deployment Status:${NC}"
    kubectl get deployments -n nim -o custom-columns=NAME:.metadata.name,READY:.status.readyReplicas,DESIRED:.spec.replicas,AGE:.metadata.creationTimestamp --no-headers 2>/dev/null | while read name ready desired age; do
        if [ "$ready" = "$desired" ] && [ "$ready" != "<none>" ]; then
            echo -e "  ${GREEN}✓${NC} $name: $ready/$desired replicas ready"
        elif [ "$ready" = "<none>" ]; then
            echo -e "  ${YELLOW}⏳${NC} $name: 0/$desired replicas ready (starting up)"
        else
            echo -e "  ${YELLOW}⏳${NC} $name: $ready/$desired replicas ready"
        fi
    done

    echo ""
    echo -e "${BOLD}Pod Status:${NC}"
    kubectl get pods -n nim -o custom-columns=NAME:.metadata.name,STATUS:.status.phase,READY:.status.conditions[?\(@.type==\'Ready\'\)].status,RESTARTS:.status.containerStatuses[0].restartCount,NODE:.spec.nodeName --no-headers 2>/dev/null | while read name status ready restarts node; do
        if [ "$status" = "Running" ] && [ "$ready" = "True" ]; then
            echo -e "  ${GREEN}✓${NC} $name: Running and Ready (restarts: $restarts) on $node"
        elif [ "$status" = "Running" ]; then
            echo -e "  ${YELLOW}⏳${NC} $name: Running but not Ready yet (restarts: $restarts) on $node"
        elif [ "$status" = "Pending" ]; then
            echo -e "  ${YELLOW}⏳${NC} $name: Pending (waiting to schedule)"
        else
            echo -e "  ${RED}✗${NC} $name: $status (restarts: $restarts)"
        fi
    done

    echo ""
    echo -e "${BOLD}Service Endpoints:${NC}"
    kubectl get svc -n nim -o custom-columns=NAME:.metadata.name,TYPE:.spec.type,EXTERNAL-IP:.status.loadBalancer.ingress[0].hostname,PORT:.spec.ports[0].port --no-headers 2>/dev/null | while read name type external port; do
        if [ "$external" != "<none>" ] && [ ! -z "$external" ]; then
            echo -e "  ${GREEN}✓${NC} $name ($type): http://$external:$port"
        else
            echo -e "  ${YELLOW}⏳${NC} $name ($type): Waiting for external IP..."
        fi
    done

    echo ""
    echo -e "${BOLD}Recent Events (last 5):${NC}"
    kubectl get events -n nim --sort-by='.lastTimestamp' | tail -6 | tail -5 | while read line; do
        if [[ $line == *"Error"* ]] || [[ $line == *"Failed"* ]] || [[ $line == *"Evicted"* ]]; then
            echo -e "  ${RED}!${NC} $line"
        elif [[ $line == *"Warning"* ]]; then
            echo -e "  ${YELLOW}⚠${NC} $line"
        else
            echo -e "  ${BLUE}•${NC} $line"
        fi
    done
fi

# 9. Interactive monitoring
print_step "[9/9] Starting live pod monitoring..."
print_info "Press Ctrl+C to exit"
print_info "Tip: Run 'kubectl logs -n nim <pod-name> -f' to see detailed logs"
echo ""
echo -e "${BOLD}${CYAN}Live Pod Status:${NC}"
echo -e "${CYAN}────────────────────────────────────────${NC}"

# Enhanced watch with color-coded status
kubectl get pods -n nim -w -o custom-columns=NAME:.metadata.name,STATUS:.status.phase,READY:.status.conditions[?\(@.type==\'Ready\'\)].status,RESTARTS:.status.containerStatuses[0].restartCount,AGE:.metadata.creationTimestamp 2>/dev/null | while read name status ready restarts age; do
    timestamp=$(date '+%H:%M:%S')
    if [ "$name" = "NAME" ]; then
        echo -e "${BOLD}$timestamp | $name\t\t\t$status\t$ready\t$restarts\t$age${NC}"
        continue
    fi

    if [ "$status" = "Running" ] && [ "$ready" = "True" ]; then
        echo -e "${GREEN}$timestamp | ✓ $name: Running and Ready (restarts: $restarts)${NC}"
    elif [ "$status" = "Running" ]; then
        echo -e "${YELLOW}$timestamp | ⏳ $name: Running, waiting for readiness... (restarts: $restarts)${NC}"
    elif [ "$status" = "Pending" ]; then
        echo -e "${YELLOW}$timestamp | ⏳ $name: Pending (scheduling or pulling image)${NC}"
    elif [ "$status" = "ContainerCreating" ]; then
        echo -e "${YELLOW}$timestamp | ⏳ $name: Creating container...${NC}"
    else
        echo -e "${RED}$timestamp | ✗ $name: $status${NC}"
    fi
done
