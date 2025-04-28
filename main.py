"""Main FastAPI application for the Feyod MCP server."""

import logging
import json # Import json for encoding results
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Literal, Dict, Any, Optional

import config
import query_processor # Import the new processor
from mcp_tools import MCP_TOOLS

# Configure logging using level from config
logging.basicConfig(level=config.LOG_LEVEL)
logger = logging.getLogger(__name__)

# Check if LangChain LLM is available by calling the getter
# This will trigger initialization if it hasn't happened yet.
if not query_processor.get_llm():
    logger.critical("LangChain LLM failed to initialize (called from main). Check LLM_API_KEY and provider settings.")
    # Decide if startup should halt. For now, log critical error.

app = FastAPI(
    title="Feyod MCP Server",
    description="MCP server for querying Feyenoord match data.",
    version="0.1.0",
)

# --- MCP Data Models (keep as they are) ---
class FunctionCall(BaseModel):
    name: str
    arguments: Dict[str, Any]

class ToolCall(BaseModel):
    id: str
    type: Literal["function"] = "function"
    function: FunctionCall

class Message(BaseModel):
    role: Literal["user", "model"]
    content: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None

class GenerateRequest(BaseModel):
    history: List[Message] = Field(..., description="The conversation history.")

class GenerateResponse(BaseModel):
    content: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None
    error: Optional[str] = None

# --- FastAPI Endpoints ---

@app.get("/")
async def read_root():
    """Root endpoint for basic server check."""
    return {"message": "Feyod MCP Server is running."}

@app.get("/v1/tools")
async def get_tools():
    """MCP endpoint to list available tools."""
    # These tools describe the *conceptual* functions the server offers.
    # The /generate endpoint implements the workflow using these concepts.
    return {"tools": MCP_TOOLS}

@app.post("/v1/generate", response_model=GenerateResponse)
async def generate_content(request: GenerateRequest):
    """
    MCP endpoint to generate content based on conversation history.
    Uses the query_processor module to handle the Text-to-SQL workflow.
    Returns raw JSON results string in the 'content' field on success,
    or an error message in the 'error' field.
    """
    if not request.history:
        raise HTTPException(status_code=400, detail="History cannot be empty")

    last_message = request.history[-1]
    if last_message.role != "user" or not last_message.content:
        raise HTTPException(status_code=400, detail="Last message must be from user with content")

    user_query = last_message.content
    logger.info(f"Received user query for /v1/generate: {user_query}")

    try:
        # Call the main workflow function from the query processor
        # result_data will be List[Dict] on success, str on error
        result_data = await query_processor.process_query_workflow(user_query)

        # Check if the result indicates an error occurred within the workflow
        if isinstance(result_data, str):
            # An error string was returned by the workflow
            logger.error(f"Workflow failed for query '{user_query}': {result_data}")
            return GenerateResponse(error=result_data)
        elif isinstance(result_data, list):
            # Success: results is a list of dictionaries
            logger.info(f"Successfully processed query '{user_query}'. Sending JSON results.")
            # Encode the list of results as a JSON string
            json_content = json.dumps(result_data)
            return GenerateResponse(content=json_content)
        else:
            # Should not happen based on process_query_workflow's return types
            logger.error(f"Unexpected return type from workflow for query '{user_query}': {type(result_data)}")
            return GenerateResponse(error="An unexpected internal server error occurred.")

    except Exception as e:
        # Catch any unexpected errors not handled by the workflow itself
        logger.exception(f"Unexpected error in /v1/generate endpoint for query '{user_query}': {e}")
        # Return a generic error in the MCP response format
        return GenerateResponse(error=f"An unexpected server error occurred: {e}")

if __name__ == "__main__":
    import uvicorn
    # Use PORT and LOG_LEVEL from config
    uvicorn.run("main:app", host="0.0.0.0", port=config.PORT, reload=True, log_level=config.LOG_LEVEL.lower())
