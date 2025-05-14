[![MseeP.ai Security Assessment Badge](https://mseep.net/pr/jeroenvdmeer-feyod-mcp-badge.png)](https://mseep.ai/app/jeroenvdmeer-feyod-mcp)

# Feyod MCP Server

FastAPI-based Model Context Protocol (MCP) server for querying Feyenoord football match data using natural language.

## Overview

This MCP server provides a natural language interface to query Feyod: Feyenoord Open Data. The underlying database is maintained in the [feyod GitHub repository](https://github.com/jeroenvdmeer/feyod). You will need to obtain the latest SQL file from that repository to set up the required database.

This server uses LangChain to:
1.  Convert natural language questions into SQL queries (optionally leveraging few-shot examples for better accuracy).
2.  Validate the generated SQL.
3.  Attempt to fix invalid SQL using an LLM.
4.  Execute the valid SQL against a SQLite database.
5.  Return the raw query results.

LLM and embedding models are dynamically loaded based on configuration using a provider factory (`llm_factory.py`), allowing easy switching between providers like OpenAI, Google, etc.

## Setup

1.  **Clone repositories:**
    ```bash
    # Clone this repo for the MCP server
    git clone https://github.com/jeroenvdmeer/feyod-mcp.git

    # Clone the Feyod database
    git clone https://github.com/jeroenvdmeer/feyod.git

    # Change directory into the MCP server
    cd feyod-mcp
    ```
2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv .venv
    # Windows
    .\.venv\Scripts\activate
    # macOS/Linux
    source .venv/bin/activate
    ```
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Set up the database:**
    ```bash
    # Change directory to the feyod directory with the SQL file
    cd ../feyod

    # Build the SQLite database using the SQL statements
    sqlite3 feyod.db < feyod.sql
    ```

## Configuration

Create a `.env` file in the `mcp` directory with the following variables:

```dotenv
# .env

# Path to the SQLite database file (relative to mcp folder or absolute)
DATABASE_PATH="../feyod/feyod.db"

# Port for the FastAPI server
PORT=8000

# Logging level (e.g., DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=INFO

# --- LLM Configuration ---

# Specify the provider (e.g., openai, google). See llm_factory.py for supported providers.
# Ensure corresponding langchain package is installed (e.g., langchain-openai, langchain-google-genai)
LLM_PROVIDER="google"

# Your API key for the chosen provider. The specific variable name might differ per provider.
# Common keys used (check llm_factory.py):
LLM_API_KEY="YOUR_API_KEY_HERE"

# Specify the model name compatible with the provider
# (e.g., o4-mini, gemini-2.5-flash-preview-04-17)
LLM_MODEL="gemini-2.5-flash-preview-04-17"

# --- Example Loading Configuration (Optional) ---

# Determines where few-shot examples are loaded from. This allows you to provide the MCP server with examples of natural language text into SQL queries.
# Options:
#   - "local": Use the hardcoded examples list in examples.py (default).
#   - "mongodb": Load examples from a MongoDB-compatible server (local or cloud).
#
# If using "mongodb", set these in your .env:
EXAMPLE_SOURCE="mongodb"
# Example connection strings:
#   Local MongoDB:
#   EXAMPLE_DB_CONNECTION_STRING="mongodb://localhost:27017/feyenoord_data"
#   MongoDB Atlas:
#   EXAMPLE_DB_CONNECTION_STRING="mongodb+srv://<user>:<password>@<cluster-url>/feyenoord_data?retryWrites=true&w=majority"
EXAMPLE_DB_NAME="feyenoord_data"
EXAMPLE_DB_COLLECTION="examples"
```

**Important:**
*   Replace placeholder API key with your actual key.
*   Ensure the `LLM_PROVIDER` matches one defined in `llm_factory.py`.
*   Install the necessary LangChain integration package for your chosen provider (e.g., `pip install langchain-google-genai`).
*   If using `EXAMPLE_SOURCE="mongodb"`, configure MongoDB settings as before.

## Adding New LLM Providers

To add support for a new provider:

1.  **Install Package:** Install the required LangChain integration package (e.g., `pip install langchain-anthropic`).
2.  **Update Factory:** Edit `llm_factory.py`:
    *   Import the necessary `Chat...` and `...Embeddings` classes.
    *   Add a new entry to the `PROVIDER_REGISTRY` dictionary, specifying the classes, the expected config variable for the API key (`api_key_config`), and any default arguments (`llm_args`, `embeddings_args`).
    *   Update the `_get_api_key`, `get_llm`, and `get_embeddings` functions if the new provider requires specific logic for API key handling or constructor arguments.
3.  **Update `.env` / README:** Add the necessary API key to your `.env` file.

## Running the Server

Once set up and configured, run the following command from the `mcp` directory:

```bash
python main.py
```

The server will start, typically on `http://localhost:8000` (or the port specified in `.env`).

## API Endpoints

*   **`GET /`**: Basic health check.
*   **`GET /v1/tools`**: Returns the conceptual tools definition (as required by MCP).
*   **`POST /v1/generate`**: The main MCP endpoint.
    *   **Request Body:**
        ```json
        {
            "history": [
                {
                    "role": "user",
                    "content": "Hoe vaak heeft Santiago Giménez gescoord tegen Ajax?"
                }
            ]
        }
        ```
    *   **Success Response (200 OK):**
        ```json
        {
            "content": "[{\"COUNT(*)\": 5}]",
            "tool_calls": null,
            "error": null
        }
        ```
    *   **Error Response (200 OK with error field):**
        ```json
        {
            "error": "Error message describing the failure (e.g., LLM unavailable, DB error, invalid SQL after fix attempts)."
        }
        ```

## Dependencies

*   Python 3.10+
*   See `requirements.txt` for specific package dependencies.
*   Provider-specific packages (e.g., `langchain-openai`, `langchain-google-genai`).

## Disclaimer

This initiative is not affiliated with Feyenoord Rotterdam N.V. and therefore not an official Feyenoord product. The data provided through this server is unofficial and might be incorrect.