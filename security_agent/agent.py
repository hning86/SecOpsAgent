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
from google.genai import Client, types
from security_agent.auth import token_manager


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



def chronicle_tool_filter(tool, context=None):
    # Only allow list, get, search, and summarize methods
    name = tool.name.lower()
    return any(p in name for p in ["list", "get", "search", "summarize"])

mcp_toolset = McpToolset(
    connection_params=StreamableHTTPConnectionParams(
        url="https://chronicle.us.rep.googleapis.com/mcp",
    ),
    header_provider=token_manager.get_auth_headers,
    tool_name_prefix="chronicle_",
    tool_filter=chronicle_tool_filter
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
        GoogleSearchTool(bypass_multi_tools_limit=True)
        ]
)

# Wrap in an App
app = App(
    name="security_agent",
    root_agent=hello_agent
)
