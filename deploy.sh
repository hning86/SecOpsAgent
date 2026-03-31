#!/bin/bash

# Load environment variables from .env if it exists
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Check for required environment variables
if [ -z "$GOOGLE_CLOUD_PROJECT" ]; then
    echo "Error: GOOGLE_CLOUD_PROJECT is not set in .env"
    exit 1
fi

if [ -z "$GOOGLE_CLOUD_LOCATION" ]; then
    echo "Error: GOOGLE_CLOUD_LOCATION is not set in .env"
    exit 1
fi

echo "Deploying to Project: $GOOGLE_CLOUD_PROJECT at Location: $GOOGLE_CLOUD_LOCATION"

# Generate simplified requirements.txt from pyproject.toml
echo "Generating simplified requirements.txt..."
uv export --format requirements-txt --no-hashes --no-dev > requirements_simple.txt

# Deploy to Agent Engine
echo "Running ADK deployment..."

AGENT_ENGINE_ID="4419886110566514688"

declare -a DEPLOY_CMD
DEPLOY_CMD=("uv" "run" "adk" "deploy" "agent_engine" "security_agent" \
    "--project=$GOOGLE_CLOUD_PROJECT" \
    "--region=$GOOGLE_CLOUD_LOCATION" \
    "--adk_app_object=app" \
    "--requirements_file=requirements_simple.txt" \
    "--validate-agent-import" \
    "--otel_to_cloud" \
    "--agent_engine_id=$AGENT_ENGINE_ID")

echo "Updating existing Agent Engine ID: $AGENT_ENGINE_ID"

"${DEPLOY_CMD[@]}"

# Cleanup
echo "Cleaning up..."
rm requirements_simple.txt

echo "Deployment finished."
