# SecOps Agent

SecOps Agent is a Security Operations Assistant built with the Google Agent Development Kit (ADK). It is designed to assist security analysts by interacting with Google SecOps (Chronicle) through the Model Context Protocol (MCP) and performing Google Searches for external threat intelligence.

The agent leverages **Vertex AI Gemini 2.5 Flash** for fast, robust reasoning and dynamically handles authentication for GCP and Chronicle MCP environments.

## Features

- **Vertex AI Powered**: Uses a custom `VertexGemini` client to route requests through Google Cloud Vertex AI infrastructure.
- **Chronicle MCP Integration**: Natively connects to the Chronicle MCP server (`https://chronicle.us.rep.googleapis.com/mcp`) to perform searches, listing, and summary operations.
- **Google Search Integration**: Capable of querying the public web for emerging threat information or general security operations knowledge.
- **Dynamic Authentication**: Automatically fetches and caches access tokens using default Google credentials (`google-auth`) or the local `gcloud` CLI for seamless development and deployment.
- **Cloud Run / Agent Engine Ready**: Includes a deployment script to bundle and deploy the application to Vertex AI Agent Engine.

## MCP Server Authentication

The SecOps Agent integrates with the Chronicle MCP Server using the HTTP-based Model Context Protocol. To ensure secure communication, the `McpToolset` dynamically injects an OAuth 2.0 Bearer token into the `Authorization` header of each request.

The authentication flow utilizes a tiered strategy:
1. **Cloud Run / Agent Engine (Production)**: Attempts to fetch credentials seamlessly via `google.auth.default()`, retrieving standard Google Cloud application default credentials.
2. **Local Development (Fallback)**: If the standard library fails, falls back to shelling out and executing `gcloud auth print-access-token` to acquire the active user's credentials.

The token is cached locally to minimize latency during repeated tool executions, ensuring that requests to `https://chronicle.us.rep.googleapis.com/mcp` are authenticated cleanly and efficiently without needing human intervention.

### Token Caching & Expiration

To balance performance and reliability, the access token caching logic uses a proactive refresh strategy:
- **1-Hour Lifespan**: Fresh tokens fetched via Google Cloud services are assumed to have the standard 3600-second (1 hour) validity window.
- **10-Minute Buffer**: The cache enforces a 600-second buffer before validating reuse. If a cached token is within 10 minutes of expiring, it is preemptively refreshed instead of reused. This ensures that any token passed to the underlying MCP tools has a generous margin for time-consuming model inferences and network requests, avoiding unanticipated `401 Unauthorized` errors caused by tokens expiring mid-flight.

## Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) for package management.
- Google Cloud CLI (`gcloud`) configured with appropriate permissions.
- Access to a Google Cloud Project with Vertex AI enabled (Note: the agent code currently defaults to a specific internal project ID).

## Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone git@github.com:hning86/SecOpsAgent.git
   cd SecOpsAgent
   ```

2. **Install dependencies using `uv`:**
   ```bash
   uv sync
   ```

3. **Configure Environment:**
   Ensure you have configured your default active project and are authenticated.
   ```bash
   gcloud auth application-default login
   gcloud config set project <YOUR_GCP_PROJECT_ID>
   ```

## Local Development

You can test the agent locally using the provided `client.py` runner script which executes an asynchronous, in-memory chat session.

```bash
uv run python client.py
```

This will run predefined user queries against the SecOps Agent and stream back the assistant's responses.

## Deployment

The project contains a `deploy.sh` script to configure and deploy the agent to Google Cloud Agent Engine. It relies on the environment variables defined in a `.env` file.

1. Create a `.env` file in the root directory:
   ```env
   GOOGLE_CLOUD_PROJECT=<YOUR_GCP_PROJECT_ID>
   GOOGLE_CLOUD_LOCATION=us-central1
   ```

2. Run the deployment script:
   ```bash
   ./deploy.sh
   ```
   *Note: This script uses `uv export` to generate a simplified `requirements_simple.txt` and uses the ADK CLI to push the agent to the remote Agent Engine.*

## Project Structure

- `security_agent/agent.py`: Agent configuration, Toolset integration (Chronicle MCP, Google Search), and Vertex AI Model setup.
- `client.py`: Local command-line runner using ADK's `InMemorySessionService`.
- `deploy.sh`: Deployment script for Vertex AI Agent Engine.
- `pyproject.toml`: Python dependencies and project configuration managed by `uv`.
