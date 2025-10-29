#!/bin/bash
set -e

if [ -f .env.neo4j ]; then
    source .env.neo4j
    
    if [ -n "$NEO4J_INSTANCE_ID" ]; then
        echo "Terminating instance: $NEO4J_INSTANCE_ID"
        aws ec2 terminate-instances --instance-ids $NEO4J_INSTANCE_ID
        echo "Instance terminated. Waiting for termination..."
        aws ec2 wait instance-terminated --instance-ids $NEO4J_INSTANCE_ID
        echo "Done!"
    else
        echo "No instance ID found in .env.neo4j"
    fi
else
    echo "No .env.neo4j file found"
    echo "Provide instance ID manually:"
    echo "aws ec2 terminate-instances --instance-ids i-xxxxx"
fi

echo ""
echo "To delete security group:"
echo "aws ec2 delete-security-group --group-name neo4j-hackathon-sg"
