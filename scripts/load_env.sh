#!/bin/bash
# Safe .env loader that handles special characters

load_env() {
    local env_file="${1:-.env}"
    
    if [ ! -f "$env_file" ]; then
        echo "ERROR: $env_file file not found."
        return 1
    fi
    
    # Clear existing AWS credentials to avoid conflicts
    unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN
    
    # Use a safer method that handles special characters
    while IFS='=' read -r key value; do
        # Skip comments and empty lines
        [[ $key =~ ^[[:space:]]*# ]] && continue
        [[ -z $key ]] && continue
        
        # Remove leading/trailing whitespace
        key=$(echo "$key" | xargs)
        value=$(echo "$value" | xargs)
        
        # Export the variable (force override existing)
        export "$key=$value"
    done < "$env_file"
    
    echo "Environment variables loaded from $env_file"
}
# Call th
e function
load_env