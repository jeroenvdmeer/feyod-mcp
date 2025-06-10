from mcp.server.fastmcp import FastMCP
import uvicorn
import logging
import config
import query_processor
import database

# Configure logging using level from config
logging.basicConfig(level=config.LOG_LEVEL)
logger = logging.getLogger(__name__)

# Create the MCP server instance
mcp = FastMCP("Feyod MCP Server", stateless_http=True)


@mcp.resource("file:///feyod.db")
async def get_schema() -> str:
    """Returns the schema of the Feyod (Feyenoord Open Data)
    database, including example rows from each table. Use this
    information to ask better questions that are easier to
    be answered by the tool."""

    logger.info(f"Received schema request")
    return await database.get_schema_description()


@mcp.prompt()
def wins_against_opponent(opponent: str) -> str:
    """Returns a question about the number of wins Feyenoord has against a given opponent."""
    return f"Hoe vaak heeft Feyenoord gewonnen van {opponent}?"


@mcp.prompt()
def two_players_scored_in_match(player1: str, player2: str) -> str:
    """Returns a question about the number of matches in which two players both scored."""
    return f"Hoe vaak heeft hebben {player1} en {player2} tegelijk in een wedstrijd gescoord?"


@mcp.prompt()
def biggest_win(opponent: str) -> str:
    """Returns a question about the biggest win Feyenoord has against a given opponent."""
    return f"Wat is de grootste overwinning van Feyenoord op {opponent}?"


@mcp.tool()
async def answer_feyenoord_question(natural_language_query: str) -> dict:
    """Answers questions about Feyenoord. Questions can be asked in natural language,
    text, and can be about matches (lineups, results, goals, cards, etc.), players,
    and opponents."""

    logger.info(f"Received question: {natural_language_query}")
    result = await query_processor.process_query_workflow(natural_language_query)

    if isinstance(result, list):
        return result
    else:
        raise Exception("Tool execution failed or returned unexpected data.")


if __name__ == "__main__":
    uvicorn.run(
        mcp.streamable_http_app,
        host="0.0.0.0",
        port=8000,
        log_level=config.LOG_LEVEL.lower(),
    )
