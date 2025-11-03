#!/bin/bash

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

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

print_header "NIM POD LOGS MONITOR"

# Get running NIM pods dynamically
print_step "Discovering running NIM pods in 'nim' namespace..."

EMBEDDER_POD=$(kubectl get pods -n nim --no-headers 2>/dev/null | grep nim-embedder | grep Running | head -1 | awk '{print $1}')
GENERATOR_POD=$(kubectl get pods -n nim --no-headers 2>/dev/null | grep nim-generator | grep Running | head -1 | awk '{print $1}')

if [ -z "$EMBEDDER_POD" ] && [ -z "$GENERATOR_POD" ]; then
    print_error "No running NIM pods found in 'nim' namespace"
    print_info "Make sure your pods are deployed and running"
    exit 1
fi

echo ""
if [ -n "$EMBEDDER_POD" ]; then
    print_success "Found embedder pod: $EMBEDDER_POD"
fi

if [ -n "$GENERATOR_POD" ]; then
    print_success "Found generator pod: $GENERATOR_POD"
fi

print_info "Press Ctrl+C to stop monitoring"
echo -e "\n${BOLD}${CYAN}Live Logs:${NC}"
echo -e "${CYAN}────────────────────────────────────────${NC}\n"

# Tail logs in parallel with clear prefixes and colors
if [ -n "$EMBEDDER_POD" ]; then
    kubectl logs -n nim -f $EMBEDDER_POD 2>&1 | sed "s/^/$(echo -e ${GREEN})[EMBEDDER]$(echo -e ${NC}) /" &
fi

if [ -n "$GENERATOR_POD" ]; then
    kubectl logs -n nim -f $GENERATOR_POD 2>&1 | sed "s/^/$(echo -e ${BLUE})[GENERATOR]$(echo -e ${NC}) /" &
fi

# Trap Ctrl+C to clean up background jobs
trap "echo -e '\n${YELLOW}Stopping log monitoring...${NC}'; kill 0" SIGINT

# Wait for all background jobs
wait
