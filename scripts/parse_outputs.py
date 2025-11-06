import json
import sys
import os
import re

# --- INPUT FILES ---
# The CDK output JSON file is passed as the first argument
if len(sys.argv) < 2:
    print("Usage: python scripts/parse_outputs.py <cdk-outputs-backend.json>")
    sys.exit(1)

output_file = sys.argv[1]
env_file = ".env"

# Auto-generation markers
AUTO_START = "# AUTO-GENERATED START - DO NOT EDIT MANUALLY"
AUTO_END = "# AUTO-GENERATED END"

# --- READ CDK OUTPUTS ---
if not os.path.exists(output_file):
    print(f"ERROR: CDK output file not found: {output_file}")
    sys.exit(1)

with open(output_file, "r") as f:
    cdk_outputs = json.load(f)

# --- COLLECT AUTO-GENERATED VARIABLES ---
auto_vars = {}

# Serverless stack outputs
if "ServerlessStack" in cdk_outputs:
    stack_outputs = cdk_outputs["ServerlessStack"]

    mappings = {
        "ApiUrl": "APP_API_GATEWAY_URL",
        "KGBucket": "APP_KG_BUCKET",
        "RawBucket": "APP_RAW_BUCKET",
        "VerifiedBucket": "APP_VERIFIED_BUCKET",
        "JobsTable": "APP_JOBS_TABLE",
        "StateMachineArn": "APP_STATE_MACHINE_ARN",
        "SentencesTableNameOutput": "APP_SENTENCES_TABLE",
        "LLMCallLogTableOutput": "APP_LLM_CALL_LOG_TABLE",
    }

    for key, env_key in mappings.items():
        if key in stack_outputs:
            auto_vars[env_key] = stack_outputs[key]

# EKS stack outputs
if "EksStack" in cdk_outputs:
    stack_outputs = cdk_outputs["EksStack"]

    eks_mappings = {
        "GenerateEndpoint": "APP_GENERATE_ENDPOINT_URL",
        "EmbedEndpoint": "APP_EMBED_ENDPOINT_URL",
    }

    for key, env_key in eks_mappings.items():
        if key in stack_outputs:
            auto_vars[env_key] = stack_outputs[key]

# --- UPDATE .ENV FILE ---
if os.path.exists(env_file):
    with open(env_file, "r") as f:
        content = f.read()
    
    # Find auto-generated section
    start_pattern = re.escape(AUTO_START)
    end_pattern = re.escape(AUTO_END)
    
    # Generate new auto section
    auto_section = f"{AUTO_START}\n"
    for key, val in auto_vars.items():
        auto_section += f"{key}={val}\n"
    auto_section += AUTO_END
    
    # Replace or append auto section
    if AUTO_START in content and AUTO_END in content:
        # Replace existing section
        pattern = f"{start_pattern}.*?{end_pattern}"
        new_content = re.sub(pattern, auto_section, content, flags=re.DOTALL)
    else:
        # Append new section
        new_content = content.rstrip() + "\n\n" + auto_section + "\n"
    
    with open(env_file, "w") as f:
        f.write(new_content)
else:
    # Create new file with auto section only
    with open(env_file, "w") as f:
        f.write(f"{AUTO_START}\n")
        for key, val in auto_vars.items():
            f.write(f"{key}={val}\n")
        f.write(f"{AUTO_END}\n")

print(f"✅ Successfully updated {env_file}")
