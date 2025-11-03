#!/bin/bash
set -e

# Colors
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

# --- MAIN SCRIPT ---

print_header "AWS S3 BUCKET INSPECTOR"

# 1. Load .env
print_step "[1/5] Loading environment variables..."
if [ ! -f .env ]; then
    print_error ".env file not found."
    exit 1
fi
export $(grep -v '^#' .env | xargs)
print_success "Environment variables loaded."

# 2. Configure AWS CLI profile
print_step "[2/5] Configuring AWS CLI profile..."
aws configure set aws_access_key_id "$AWS_ACCESS_KEY_ID"
aws configure set aws_secret_access_key "$AWS_SECRET_ACCESS_KEY"
if [ -n "$AWS_SESSION_TOKEN" ]; then
    aws configure set aws_session_token "$AWS_SESSION_TOKEN"
fi
aws configure set region "$AWS_REGION"
print_success "AWS CLI configured for region $AWS_REGION."

# 3. List all buckets
print_step "[3/5] Listing all S3 buckets..."
BUCKETS=$(aws s3api list-buckets --query "Buckets[].Name" --output text)
if [ -z "$BUCKETS" ]; then
    print_error "No S3 buckets found in this account."
    exit 1
fi
echo -e "${BOLD}${BLUE}Available Buckets:${NC}"
i=1
for b in $BUCKETS; do
    echo -e "  [$i] $b"
    i=$((i+1))
done

echo ""
read -p "Enter bucket number to explore: " choice
SELECTED_BUCKET=$(echo $BUCKETS | cut -d' ' -f$choice)

if [ -z "$SELECTED_BUCKET" ]; then
    print_error "Invalid selection."
    exit 1
fi

print_success "Selected bucket: ${SELECTED_BUCKET}"

# 4. Explore bucket contents
while true; do
    print_step "[4/5] Listing objects in s3://${SELECTED_BUCKET}"
    read -p "Enter prefix/folder path (leave blank for root): " PREFIX
    if [ -z "$PREFIX" ]; then
        PREFIX_ARG=""
    else
        PREFIX_ARG="--prefix $PREFIX"
    fi

    echo ""
    print_info "Fetching object list..."
    aws s3 ls "s3://${SELECTED_BUCKET}/${PREFIX}" --recursive | awk '{print $4}' | while read -r file; do
        if [[ "$file" == */ ]]; then
            echo -e "📁 ${CYAN}$file${NC}"
        else
            echo -e "📄 ${GREEN}$file${NC}"
        fi
    done

    echo ""
    read -p "Enter full file key to download (or press Enter to skip): " FILE_KEY

    if [ -n "$FILE_KEY" ]; then
        DEST_DIR="./downloads/${SELECTED_BUCKET}"
        mkdir -p "$DEST_DIR"
        print_info "Downloading s3://${SELECTED_BUCKET}/${FILE_KEY}..."
        aws s3 cp "s3://${SELECTED_BUCKET}/${FILE_KEY}" "$DEST_DIR/"
        print_success "Downloaded to ${DEST_DIR}/$(basename "$FILE_KEY")"
    fi

    echo ""
    read -p "Do you want to explore again in this bucket? (y/n): " again
    if [[ "$again" != "y" && "$again" != "Y" ]]; then
        break
    fi
done

print_success "Session complete!"
echo ""
echo -e "✅ ${BOLD}You explored:${NC} s3://${SELECTED_BUCKET}"
echo -e "📂 ${BOLD}Downloads saved in:${NC} ./downloads/${SELECTED_BUCKET}/"
echo ""
