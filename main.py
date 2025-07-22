import asyncio
import logging
import uvicorn
import json
from langchain_core.messages import HumanMessage

from mcp.server import FastMCP
from nl2sql.src.workflow.manager import WorkflowManager
from nl2sql.src.workflow import config

# --- Configuration and Logging ---
log_level = config.LOG_LEVEL.lower()
logging.basicConfig(level=getattr(logging, config.LOG_LEVEL, logging.INFO))
logger = logging.getLogger(__name__)

# --- Workflow Initialization ---
app_config = {
    "FEYOD_DATABASE_URL": config.FEYOD_DATABASE_URL,
    "LLM_API_KEY": config.LLM_API_KEY,
}

try:
    # Instantiate the manager for raw data output
    workflow_manager = WorkflowManager(config=app_config, format_output=False)
    workflow = workflow_manager.get_graph()
    logger.info("WorkflowManager initialized for MCP server.")
except Exception as e:
    logger.exception("Fatal error during WorkflowManager initialization.")
    workflow = None

# --- MCP Server Setup ---
server = FastMCP("Feyod MCP Server", stateless_http=True)

@server.resource("file:///feyod.db")
async def get_schema() -> str:
    """
    Returns the schema of the Feyod (Feyenoord Open Data) database.
    """
    logger.info("Received schema request")
    if not workflow:
        return "Error: Workflow is not available."
    
    # We can invoke just the schema node, but it's simpler to run the full
    # workflow with a dummy question and extract the schema from the final state.
    # This ensures we use the exact same logic as the main tool.
    initial_state = {"messages": [HumanMessage(content="What is the schema?")]}
    final_state = await workflow.ainvoke(initial_state)
    return final_state.get("schema", "Error: Could not retrieve schema.")

@server.prompt()
def biggest_win(opponent: str) -> str:
    """Returns a question about the biggest Feyenoord win against a given opponent."""
    return f"Wat is de grootste overwinning van Feyenoord op {opponent}?"

@server.prompt()
def player_goals(player: str) -> str:
    """Returns a question about the number of goals a player has scored for Feyenoord."""
    return f"Hoeveel doelpunten heeft {player} gemaakt voor Feyenoord?"

@server.tool()
async def answer_feyenoord_question(natural_language_query: str):
    """
    Answers questions about Feyenoord matches, players, and opponents.
    Returns the raw JSON data from the database.
    """
    logger.info(f"Received query: {natural_language_query}")
    if not workflow:
        logger.error("Workflow not available, cannot process query.")
        return {
            "content": [
                {"type": "text", "text": json.dumps({"error": "Workflow is not initialized."})}
            ],
            "structuredContent": []
        }
    try:
        initial_state = {"messages": [HumanMessage(content=natural_language_query)]}
        final_state = await workflow.ainvoke(initial_state)
        last_message = final_state.get("messages", [])[-1]
        if last_message.name == "results":
            try:
                structured = json.loads(last_message.content)
                # Allow variable output: could be list, dict, etc.
            except Exception as e:
                logger.error(f"Error parsing results as JSON: {e}")
                structured = last_message.content
            return {
                "content": [
                    {"type": "text", "text": json.dumps(structured)}
                ],
                "structuredContent": structured
            }
        else:
            error_obj = {"error": "Could not retrieve results.", "final_message": str(last_message)}
            return {
                "content": [
                    {"type": "text", "text": json.dumps(error_obj)}
                ],
                "structuredContent": error_obj
            }
    except Exception as e:
        logger.error(f"Error processing query: {e}", exc_info=True)
        error_obj = {"error": f"An error occurred: {e}"}
        return {
            "content": [
                {"type": "text", "text": json.dumps(error_obj)}
            ],
            "structuredContent": error_obj
        }

async def main():
    """Sets up and runs the MCP server."""
    logger.info("Initializing Feyod MCP Server...")
    
    uvicorn_log_level = config.LOG_LEVEL.lower()
    server_config = uvicorn.Config(
        server.streamable_http_app(),
        host=config.HOST,
        port=8000,
        log_level=uvicorn_log_level,
    )
    uvicorn_server = uvicorn.Server(server_config)
    try:
        await uvicorn_server.serve()
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("Server is shutting down.")

if __name__ == "__main__":
    asyncio.run(main())
