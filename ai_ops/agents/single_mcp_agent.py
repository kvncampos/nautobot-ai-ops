"""
Single MCP Server AI Agent (Legacy/Development).

A conversational AI agent that connects to a single Nautobot MCP server via HTTP
and provides natural language access to Nautobot API and knowledge base tools.

This is a simpler implementation for development and testing with a single MCP server.
For production use with multiple MCP servers, see multi_mcp_agent.py.
"""

# import json
# import os
# from typing import Any, Dict, List, Optional

# from dotenv import load_dotenv
# from fastmcp import Client
# from langchain_core.messages import (
#     AIMessage,
#     BaseMessage,
#     HumanMessage,
#     SystemMessage,
# )
# from langchain_core.tools import tool
# from langgraph.graph import END, START, MessagesState, StateGraph
# from langgraph.prebuilt import ToolNode

# from ai_ops.helpers.get_azure_model import get_azure_model

# # Load environment variables
# load_dotenv()

# # Configuration
# # FastMCP streamable-http uses /mcp/ endpoint (with trailing slash)
# # Use Docker service name 'mcp' when running in containers
# MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://mcp:8000/mcp/")


# # ============================================================================
# # MCP HTTP Client
# # ============================================================================


# class MCPClient:
#     """Wrapper for FastMCP Client."""

#     def __init__(self, base_url: str = MCP_SERVER_URL):
#         """Initialize MCP Client with base URL."""
#         self.base_url = base_url
#         self.client = Client(base_url)
#         self._entered = False

#     async def __aenter__(self):
#         """Enter async context."""
#         await self.client.__aenter__()
#         self._entered = True
#         return self

#     async def __aexit__(self, exc_type, exc_val, exc_tb):
#         """Exit async context."""
#         await self.client.__aexit__(exc_type, exc_val, exc_tb)
#         self._entered = False

#     async def list_tools(self) -> List[Dict[str, Any]]:
#         """List all available MCP tools."""
#         try:
#             tools = await self.client.list_tools()
#             # Convert Tool objects to dicts
#             return [{"name": tool.name, "description": tool.description} for tool in tools]
#         except Exception:
#             return []

#     async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
#         """Call an MCP tool with the given arguments."""
#         try:
#             result = await self.client.call_tool(name, arguments)

#             # Parse the response content
#             if hasattr(result, "content") and isinstance(result.content, list):
#                 if len(result.content) > 0:
#                     text_content = (
#                         result.content[0].text if hasattr(result.content[0], "text") else str(result.content[0])
#                     )
#                     try:
#                         return json.loads(text_content)
#                     except json.JSONDecodeError:
#                         return {"result": text_content}
#             return {"result": str(result)}
#         except Exception as e:
#             return {"error": str(e)}

#     async def close(self):
#         """Close the client."""
#         if self._entered:
#             await self.client.__aexit__(None, None, None)
#             self._entered = False


# # Initialize global MCP client

# mcp_client = MCPClient()


# # ============================================================================
# # LangChain Tool Wrappers
# # ============================================================================


# @tool
# async def search_nautobot_endpoints(query: str, n_results: int = 5) -> str:
#     """Search for Nautobot API endpoints that match your intent.

#     Returns endpoint details including path, method, parameters, and response formats.

#     Args:
#         query: Natural language description of what API endpoint you're looking for
#         n_results: Number of results to return (default: 5)

#     Returns:
#         JSON string with matching endpoints
#     """
#     result = await mcp_client.call_tool(
#         "mcp_nautobot_openapi_api_request_schema",
#         {"query": query, "n_results": n_results},
#     )
#     return json.dumps(result, indent=2)


# @tool
# async def nautobot_api_request(
#     method: str,
#     path: str,
#     params: Optional[Dict[str, Any]] = None,
#     body: Optional[Dict[str, Any]] = None,
# ) -> str:
#     """
#     Execute direct HTTP requests to the Nautobot REST API.

#     ⚠️ CRITICAL WORKFLOW - FOLLOW THIS ORDER:
#     1. ALWAYS call search_nautobot_endpoints() FIRST to discover the correct endpoint
#     2. Review the schema response for exact parameter names and formats
#     3. THEN call this tool with the correct endpoint path and parameters

#     DO NOT guess endpoint paths or parameter names. Always verify with search_nautobot_endpoints first.

#     If you receive errors (404 Not Found or 400 Bad Request):
#     - STOP immediately
#     - Call search_nautobot_endpoints() to find the correct endpoint and parameters
#     - Review the schema carefully
#     - Retry with corrected information from the schema

#     Args:
#         method: HTTP method (GET, POST, PUT, PATCH, DELETE)
#         path: API endpoint path (e.g., '/api/plugins/circuit-costs/cost/')
#         params: Query parameters for GET requests (verify names from schema)
#         body: Request body for POST/PUT/PATCH requests

#     Returns:
#         JSON string with API response or detailed error guidance
#     """
#     result = await mcp_client.call_tool(
#         "mcp_nautobot_dynamic_api_request",
#         {"method": method, "path": path, "params": params, "body": body},
#     )

#     # Check for errors and provide helpful guidance
#     if isinstance(result, dict) and "error" in result:
#         error_msg = result.get("error", "")

#         # 400 Bad Request - invalid parameters
#         if "400" in str(error_msg) or "Bad Request" in str(error_msg):
#             guidance = {
#                 "error": error_msg,
#                 "error_type": "400 Bad Request - Invalid Query Parameters",
#                 "required_action": "⚠️ YOU MUST USE search_nautobot_endpoints() FIRST",
#                 "troubleshooting_steps": [
#                     "1. IMMEDIATELY call search_nautobot_endpoints with a query like 'circuit costs' or 'location filters'",
#                     "2. Review the schema response to find valid query parameter names",
#                     "3. Check date parameter formats - some endpoints use 'created_after/before', others use different names",
#                     "4. Verify filter field names match the schema exactly (case-sensitive)",
#                     "5. Try the API request again with corrected parameters from the schema",
#                 ],
#                 "example_workflow": "search_nautobot_endpoints('circuit costs date filters') → review schema → retry API call with correct params",
#             }
#             return json.dumps(guidance, indent=2)

#         # 404 Not Found - wrong endpoint
#         if "404" in str(error_msg) or "Not Found" in str(error_msg):
#             guidance = {
#                 "error": error_msg,
#                 "error_type": "404 Not Found - Endpoint Does Not Exist",
#                 "required_action": "⚠️ YOU MUST USE search_nautobot_endpoints() TO FIND THE CORRECT ENDPOINT",
#                 "troubleshooting_steps": [
#                     "1. IMMEDIATELY call search_nautobot_endpoints with keywords from your query (e.g., 'costs', 'circuits', 'devices')",
#                     "2. Review the schema results to find the correct endpoint path",
#                     "3. Use the exact path from the schema in your next API request",
#                 ],
#                 "example_workflow": "search_nautobot_endpoints('circuit costs') → review endpoint paths → retry with correct path",
#             }
#             return json.dumps(guidance, indent=2)

#     return json.dumps(result, indent=2)


# @tool
# async def refresh_endpoint_index() -> str:
#     """Manually refresh the OpenAPI endpoint index from the latest schema.

#     Use this when you need to update the available endpoint information.

#     Returns:
#         Confirmation message
#     """
#     result = await mcp_client.call_tool("mcp_refresh_endpoint_index", {})
#     return json.dumps(result, indent=2)


# # List of all tools
# tools = [
#     search_nautobot_endpoints,
#     nautobot_api_request,
#     refresh_endpoint_index,
# ]


# # ============================================================================
# # LangGraph Agent
# # ============================================================================


# def should_continue(state: MessagesState):
#     """Determine if we should continue to tools or end."""
#     messages = state["messages"]
#     last_message = messages[-1]

#     # If the LLM makes a tool call, go to tools node
#     if hasattr(last_message, "tool_calls") and last_message.tool_calls:
#         return "tools"
#     # Otherwise end
#     return END


# async def call_model(state: MessagesState) -> Dict[str, List[BaseMessage]]:
#     """Call the LLM with tools bound."""
#     messages = state["messages"]

#     # Load system prompt from external file
#     from ai_ops.prompts.system_prompt import get_system_prompt

#     system_message = SystemMessage(content=get_system_prompt())

#     # Prepend system message if not already present
#     if not any(isinstance(msg, SystemMessage) for msg in messages):
#         messages = [system_message] + messages

#     llm = get_azure_model()
#     llm_with_tools = llm.bind_tools(tools)

#     response = await llm_with_tools.ainvoke(messages)
#     return {"messages": [response]}


# def create_agent():
#     """Create and compile the LangGraph agent."""
#     # Create the graph
#     workflow = StateGraph(MessagesState)

#     # Add nodes
#     workflow.add_node("agent", call_model)
#     workflow.add_node("tools", ToolNode(tools))

#     # Add edges
#     workflow.add_edge(START, "agent")
#     workflow.add_conditional_edges("agent", should_continue)
#     workflow.add_edge("tools", "agent")

#     # Compile
#     return workflow.compile()


# # ============================================================================
# # Server Connection Utilities
# # ============================================================================


# async def process_message(user_input: str, messages: List[BaseMessage]) -> tuple[str, List[BaseMessage]]:
#     """Process a single user message and return the response.

#     Args:
#         user_input: The user's input message
#         messages: Current conversation history

#     Returns:
#         Tuple of (assistant_response, updated_messages)
#     """
#     # Add user message
#     messages.append(HumanMessage(content=user_input))

#     # Use context manager to properly handle client lifecycle per request
#     async with mcp_client:
#         try:
#             # Create agent
#             agent = create_agent()

#             # Invoke agent
#             response = await agent.ainvoke({"messages": messages})

#             # Update message history
#             messages = response["messages"]

#             # Get final response from AI
#             if messages and isinstance(messages[-1], AIMessage):
#                 return str(messages[-1].content), messages

#             return "No response generated", messages

#         except Exception as e:
#             return f"Error: {str(e)}", messages


# # ============================================================================
# # Main Entry Point
# # ============================================================================


# async def initialize_agent():
#     """Initialize the agent and MCP client."""
#     await mcp_client.__aenter__()
#     return create_agent()


# async def shutdown_agent():
#     """Shutdown the MCP client."""
#     await mcp_client.__aexit__(None, None, None)
