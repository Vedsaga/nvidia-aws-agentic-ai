#!/bin/bash
set -e

INSTANCE_TYPE="t3.micro"
AMI_ID=$(aws ec2 describe-images --owners amazon --filters "Name=name,Values=al2023-ami-2023.*-x86_64" "Name=state,Values=available" --query "Images | sort_by(@, &CreationDate) | [-1].ImageId" --output text)
KEY_NAME="${NEO4J_KEY_NAME:-}"
SECURITY_GROUP_NAME="neo4j-hackathon-sg"

echo "Creating security group..."
SG_ID=$(aws ec2 create-security-group \
    --group-name $SECURITY_GROUP_NAME \
    --description "Neo4j for hackathon - 6 users" \
    --query 'GroupId' --output text 2>/dev/null || \
    aws ec2 describe-security-groups --group-names $SECURITY_GROUP_NAME --query 'SecurityGroups[0].GroupId' --output text)

echo "Security Group: $SG_ID"

aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 7474 --cidr 0.0.0.0/0 2>/dev/null || true
aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 7687 --cidr 0.0.0.0/0 2>/dev/null || true
aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 22 --cidr 0.0.0.0/0 2>/dev/null || true

USER_DATA=$(cat <<'EOF'
#!/bin/bash
yum update -y
yum install -y docker
systemctl start docker
systemctl enable docker
usermod -a -G docker ec2-user

docker run -d \
  --name neo4j \
  --restart unless-stopped \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/hackathon2025 \
  -e NEO4J_dbms_memory_heap_initial__size=256m \
  -e NEO4J_dbms_memory_heap_max__size=512m \
  -e NEO4J_dbms_memory_pagecache_size=128m \
  -v neo4j_data:/data \
  neo4j:5.15-community

echo "Neo4j deployed successfully" > /home/ec2-user/neo4j-status.txt
EOF
)

echo "Launching EC2 instance..."
if [ -z "$KEY_NAME" ]; then
    INSTANCE_ID=$(aws ec2 run-instances \
        --image-id $AMI_ID \
        --instance-type $INSTANCE_TYPE \
        --security-group-ids $SG_ID \
        --user-data "$USER_DATA" \
        --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=neo4j-hackathon},{Key=Purpose,Value=hackathon}]" \
        --query 'Instances[0].InstanceId' \
        --output text)
else
    INSTANCE_ID=$(aws ec2 run-instances \
        --image-id $AMI_ID \
        --instance-type $INSTANCE_TYPE \
        --key-name $KEY_NAME \
        --security-group-ids $SG_ID \
        --user-data "$USER_DATA" \
        --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=neo4j-hackathon},{Key=Purpose,Value=hackathon}]" \
        --query 'Instances[0].InstanceId' \
        --output text)
fi

echo "Instance ID: $INSTANCE_ID"
echo "Waiting for instance to start..."

aws ec2 wait instance-running --instance-ids $INSTANCE_ID

PUBLIC_IP=$(aws ec2 describe-instances \
    --instance-ids $INSTANCE_ID \
    --query 'Reservations[0].Instances[0].PublicIpAddress' \
    --output text)

echo ""
echo "=========================================="
echo "Neo4j deployed successfully!"
echo "=========================================="
echo "Instance ID: $INSTANCE_ID"
echo "Public IP: $PUBLIC_IP"
echo ""
echo "Neo4j Browser: http://$PUBLIC_IP:7474"
echo "Bolt URL: bolt://$PUBLIC_IP:7687"
echo "Username: neo4j"
echo "Password: hackathon2025"
echo ""
echo "Wait 2-3 minutes for Neo4j to fully start"
echo ""
echo "To terminate: aws ec2 terminate-instances --instance-ids $INSTANCE_ID"
echo "=========================================="

cat > .env.neo4j <<EOL
NEO4J_URI=bolt://$PUBLIC_IP:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=hackathon2025
NEO4J_INSTANCE_ID=$INSTANCE_ID
EOL

echo "Credentials saved to .env.neo4j"
