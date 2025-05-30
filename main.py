"""Main FastAPI application for the Feyod MCP server."""

from mcp.server.fastmcp import FastMCP
import logging
import config
import query_processor
import uvicorn # Import uvicorn

# Configure logging using level from config
logging.basicConfig(level=config.LOG_LEVEL)
logger = logging.getLogger(__name__)

# Create the MCP server instance
mcp = FastMCP("Feyod MCP Server", stateless_http=True)

@mcp.tool(
    name="query_feyod_database",
    description="Converts a natural language query about Feyenoord matches into a SQL query, executes it, and returns the SQL query and its result."
)
async def query_feyod_database(natural_language_query: str) -> dict:
    """MCP tool: Query Feyenoord database using natural language."""
    logger.info(f"Received MCP tool call: {natural_language_query}")
    result = await query_processor.process_query_workflow(natural_language_query)
    if isinstance(result, dict) and "sql_query" in result and "query_result" in result:
        return result
    elif isinstance(result, list):
        # If only query_result is returned, return with empty sql_query
        return {"sql_query": "", "query_result": result}
    else:
        raise Exception("Tool execution failed or returned unexpected data.")

if __name__ == "__main__":
    uvicorn.run(
        mcp.streamable_http_app,
        host="0.0.0.0",
        port=8000,
        log_level=config.LOG_LEVEL.lower()
    )
