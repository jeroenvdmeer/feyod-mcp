import asyncio
import logging
import uvicorn

from mcp.server import FastMCP

import config
import query_processor
import database

logging.basicConfig(level=config.LOG_LEVEL)
logger = logging.getLogger(__name__)
server = FastMCP("Feyod MCP Server", stateless_http=True)


@server.resource("file:///feyod.db")
async def get_schema() -> str:
    """
    Returns the schema of the Feyod (Feyenoord Open Data) database.
    Use this information to ask better questions that are easier to answer.
    """
    logger.info("Received schema request")
    return await database.get_schema_description()


@server.prompt()
def biggest_win(opponent: str) -> str:
    """Returns a question about the biggest Feyenoord win against a given opponent."""
    return f"Wat is de grootste overwinning van Feyenoord op {opponent}?"


@server.prompt()
def player_goals(player: str) -> str:
    """Returns a question about the number of goals a player has scored for Feyenoord."""
    return f"Hoeveel doelpunten heeft {player} gemaakt voor Feyenoord?"


@server.tool()
async def answer_feyenoord_question(natural_language_query: str) -> str:
    """
    Answers questions about Feyenoord matches, players, and opponents.
    """
    logger.info(f"Received query: {natural_language_query}")
    try:
        result = await query_processor.process_query_workflow(natural_language_query)
        # Ensure result is a string for consistent return type
        return str(result)
    except Exception as e:
        logger.error(f"Error processing query: {e}", exc_info=True)
        return f"An error occurred while processing your question: {e}"


async def main():
    """Sets up and runs the MCP server."""
    logger.info("Initializing Feyod MCP Server...")
    server_config = uvicorn.Config(
        server.streamable_http_app(),
        host=config.HOST,
        port=8000,
        log_level=config.LOG_LEVEL.lower(),
    )
    uvicorn_server = uvicorn.Server(server_config)
    try:
        await uvicorn_server.serve()
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("Server is shutting down.")


if __name__ == "__main__":
    asyncio.run(main())
