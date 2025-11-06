#!/usr/bin/env python3
import aws_cdk as cdk
import os

from nvidia_aws_agentic_ai.eks_stack import EksStack

# --- Get AWS Account/Region from .env file ---
# This ensures CDK deploys to the same place your CLI is configured for
env = cdk.Environment(
    account=os.environ.get("AWS_ACCOUNT_ID"), region=os.environ.get("AWS_REGION")
)
# ------------------------------------------------

app = cdk.App()

# EKS Cluster for model endpoints (uncomment when needed with NVIDIA credentials)
eks = EksStack(app, "EksStack", env=env)

# Event-driven architecture stacks will be added here

app.synth()
