# Feyod MCP Server

FastAPI-based Model Context Protocol (MCP) server for querying Feyenoord football match data using natural language.

## Overview

This MCP server provides a natural language interface to query Feyod: Feyenoord Open Data. The underlying database schema is maintained in the [feyod GitHub repository](https://github.com/jeroenvdmeer/feyod). You will need to obtain the latest SQL schema from that repository to set up the required database.

This server uses LangChain to:
1.  Convert natural language questions into SQL queries (leveraging few-shot examples for better accuracy).
2.  Validate the generated SQL.
3.  Attempt to fix invalid SQL using an LLM.
4.  Execute the valid SQL against a SQLite database.
5.  Return the raw query results.

## Setup

1.  **Clone the repository:**
    ```bash
    # If this mcp folder is the root
    git clone <your-repo-url>
    cd feyod-mcp # Or your chosen repo name

    # If cloning the parent feyod repository (recommended for access to the SQL schema)
    git clone https://github.com/jeroenvdmeer/feyod.git
    cd feyod/mcp
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
    *   Clone the latest version of the Feyod database from the [feyod GitHub repository](https://github.com/jeroenvdmeer/feyod).
    *   You need a SQLite client to create the database file (e.g., `feyod.db`) from the `.sql` file.
    *   Example using the `sqlite3` command-line tool:
        ```bash
        sqlite3 feyod.db < feyod.sql
        ```
    *   Make sure the `DATABASE_PATH` in your `.env` file points to the created `.db` file.

## Configuration

Create a `.env` file in the `mcp` directory with the following variables:

```dotenv
# .env

# Path to the SQLite database file (relative to mcp folder or absolute)
DATABASE_PATH="./feyod.db"

# Port for the FastAPI server
PORT=8000

# Logging level (e.g., DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=INFO

# --- LLM Configuration ---

# Specify the provider (e.g., openai, anthropic, google)
# Ensure corresponding langchain package is installed (e.g., langchain-openai)
LLM_PROVIDER="openai"

# Your API key for the chosen provider
LLM_API_KEY="YOUR_API_KEY_HERE" # <-- IMPORTANT: Replace with your actual key

# Specify the model name compatible with the provider
# (e.g., gpt-4o)
LLM_MODEL="gpt-4o"

# --- Example Loading Configuration (Optional) ---

# Determines where few-shot examples are loaded from. This allows you to provide the MCP server with examples of natural language text into SQL queries.
# Options:
#   - "local": Use the hardcoded examples list in examples.py (default).
#   - "mongodb": Load examples from an Azure Cosmos DB for MongoDB instance.
# If using "mongodb", the following variables are required:
EXAMPLE_SOURCE="local"

# Required if EXAMPLE_SOURCE="mongodb"
EXAMPLE_DB_CONNECTION_STRING="YOUR_MONGODB_CONNECTION_STRING_HERE" # e.g., mongodb+srv://<user>:<password>@<cluster-url>/...
EXAMPLE_DB_NAME="feyenoord_data" # The database name in MongoDB
EXAMPLE_DB_COLLECTION="examples" # The collection name containing example documents
```

**Important:**
*   Replace `"YOUR_API_KEY_HERE"` with your actual API key for the selected `LLM_PROVIDER`.
*   If using `EXAMPLE_SOURCE="mongodb"`, replace `"YOUR_MONGODB_CONNECTION_STRING_HERE"` with your actual connection string and ensure the database/collection names are correct. Treat the connection string as a secret.

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

## Disclaimer

This initiative is not affiliated with Feyenoord Rotterdam N.V. and therefore not an official Feyenoord product. The data provided through this server is unofficial and might be incorrect.