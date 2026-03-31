import os
from dotenv import load_dotenv
from google.adk.agents import Agent

# Load environment variables from .env file
load_dotenv()
from google.adk.apps import App
from google.adk.models.google_llm import Gemini
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from google.adk.tools.google_search_tool import GoogleSearchTool
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams
from google.adk.agents import Agent
from google.adk.agents.readonly_context import ReadonlyContext
from google.genai import Client, types
import google.auth
import google.auth.transport.requests
import time
import threading
from typing import Dict, Optional


# Custom Gemini subclass to enable Vertex AI
class VertexGemini(Gemini):
    _cached_client: Client | None = None

    @property
    def api_client(self) -> Client:
        if self._cached_client is None:
            # vertexai=True enables Vertex AI backend
            # project and location are picked up from env vars if not provided
            self._cached_client = Client(
                vertexai=True,
                project=os.environ.get('GOOGLE_CLOUD_PROJECT'),
                location=os.environ.get('GOOGLE_CLOUD_LOCATION', 'us-central1'),
                http_options=types.HttpOptions(
                    headers=self._tracking_headers(),
                    retry_options=self.retry_options,
                    base_url=self.base_url,
                )
            )
        return self._cached_client

import subprocess

# Token Cache state
_token_cache: Optional[str] = None
_token_expiry: float = 0
_token_lock = threading.Lock()

def _get_token_via_google_auth() -> Optional[str]:
    """Attempts to fetch token via google-auth library (Standard for Cloud Run / ADC)."""
    try:
        print("--- Attempting to fetch token via google-auth ---")
        credentials, project = google.auth.default()
        auth_request = google.auth.transport.requests.Request()
        credentials.refresh(auth_request)
        return credentials.token
    except Exception as e:
        print(f"--- google-auth failed: {e} ---")
        return None

def _get_token_via_gcloud_cli() -> Optional[str]:
    """Attempts to fetch token via gcloud CLI (Local Dev fallback)."""
    try:
        print("--- Attempting to fetch token via gcloud CLI ---")
        return subprocess.check_output(
            ["gcloud", "auth", "print-access-token"], 
            stderr=subprocess.DEVNULL
        ).decode("utf-8").strip()
    except Exception as e:
        print(f"--- gcloud CLI failed: {e} ---")
        return None

# Helper to fetch access token (works for local dev and Cloud Run)
def get_access_token():
    global _token_cache, _token_expiry
    
    # 10 minutes buffer (ensures at least 50 mins reuse for 1hr token)
    buffer = 600
    now = time.time()
    
    with _token_lock:
        if _token_cache and now < (_token_expiry - buffer):
            print("--- Using Cached Access Token ---")
            return _token_cache
            
        # Try Method 1: google-auth
        token = _get_token_via_google_auth()
        
        # Try Method 2: gcloud CLI fallback
        if not token:
            token = _get_token_via_gcloud_cli()
            
        if token:
            _token_cache = token
            _token_expiry = now + 3600 # Default lifetime
            return _token_cache
            
        return None

# Header provider to fetch gcloud access token on demand
def get_auth_headers(context: ReadonlyContext) -> Dict[str, str]:
    token = get_access_token()
    return {"Authorization": f"Bearer {token}"} if token else {}

def chronicle_tool_filter(tool, context=None):
    # Only allow list, get, search, and summarize methods
    name = tool.name.lower()
    return any(p in name for p in ["list", "get", "search", "summarize"])

mcp_toolset = McpToolset(
    connection_params=StreamableHTTPConnectionParams(
        url="https://chronicle.us.rep.googleapis.com/mcp",
    ),
    header_provider=get_auth_headers,
    tool_name_prefix="chronicle_",
    tool_filter=chronicle_tool_filter
)

# Compute MCP Toolset
compute_mcp_toolset = McpToolset(
    connection_params=StreamableHTTPConnectionParams(
        url="https://compute.googleapis.com/mcp",
    ),
    header_provider=get_auth_headers,
    tool_name_prefix="compute_"
)

# Define the agent with Vertex AI model
hello_agent = Agent(
    name="security_agent",
    model=VertexGemini(model='gemini-2.5-flash'),
    instruction="""You are a helpful assistant specialize in Security Operations.
    You have access to Chronicle MCP tools (prefixed with 'chronicle_') and GoogleSearchTool for answering information security related questions. Use the following default values if the specific Chronicle MCP tool requires them:
     - GCP Project ID: secops-dev-488519 
     - Cusotmer ID: b6e0c367-ceca-43e9-861b-39b7079b13ba
     - Region: US
    """,
    tools=[
        mcp_toolset, 
        # compute_mcp_toolset
        GoogleSearchTool(bypass_multi_tools_limit=True)
        ]
)

# Wrap in an App
app = App(
    name="security_agent",
    root_agent=hello_agent
)
