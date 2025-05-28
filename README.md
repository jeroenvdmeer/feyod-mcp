# Feyod MCP Server

FastMCP-based Model Context Protocol (MCP) server for querying Feyenoord football match data using natural language. Compatible with Claude Desktop and other MCP clients.

---

## Overview

This MCP server provides a natural language interface to query Feyod: Feyenoord Open Data. The underlying database is maintained in the [feyod GitHub repository](https://github.com/jeroenvdmeer/feyod). You will need to obtain the latest SQL file from that repository to set up the required database.

The server uses LangChain to:
1.  Convert natural language questions into SQL queries (optionally leveraging few-shot examples for better accuracy).
2.  Validate the generated SQL.
3.  Attempt to fix invalid SQL using an LLM.
4.  Execute the valid SQL against a SQLite database.
5.  Return the raw query results.

LLM and embedding models are dynamically loaded based on configuration using a provider factory (`llm_factory.py`), allowing easy switching between providers like OpenAI, Google, etc.

---

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
2.  **Create and activate a virtual environment (recommended: uv):**

    Refer to https://docs.astral.sh/uv/ for the installation instructions of `uv`.

    ```bash
    uv venv
    .venv\Scripts\activate  # Windows
    # or
    source .venv/bin/activate  # macOS/Linux
    ```
3.  **Install dependencies:**
    ```bash
    # Using uv (recommended)
    uv add "mcp[cli]" langchain langchain-openai langchain-google-genai python-dotenv aiosqlite
    # Or using pip
    pip install -r requirements.txt
    ```
4.  **Set up the database:**
    ```bash
    # Change directory to the feyod directory with the SQL file
    cd ../feyod

    # Build the SQLite database using the SQL statements
    sqlite3 feyod.db < feyod.sql
    ```

---

## Configuration

Create a `.env` file in the `mcp` directory with the following variables:

```dotenv
# Path to the SQLite database file (relative to mcp folder or absolute)
DATABASE_PATH="../feyod/feyod.db"

# Logging level (e.g., DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=INFO

# --- LLM Configuration ---
LLM_PROVIDER="google"  # or "openai", etc.
LLM_API_KEY="YOUR_API_KEY_HERE"
LLM_MODEL="gemini-2.5-flash-preview-05-20"

# --- Example Loading Configuration (Optional) ---
EXAMPLE_SOURCE="local"  # or "mongodb"
EXAMPLE_DB_CONNECTION_STRING=""
EXAMPLE_DB_NAME="feyenoord_data"
EXAMPLE_DB_COLLECTION="examples"
```

**Notes:**
- Replace placeholder API key with your actual key.
- Ensure the `LLM_PROVIDER` matches one defined in `llm_factory.py`.
- Install the necessary LangChain integration package for your chosen provider (e.g., `langchain-google-genai`).
- If using `EXAMPLE_SOURCE="mongodb"`, configure MongoDB settings as above.

---

## Running the Server

You can run the server in several ways:

- **Development mode (with hot reload and Inspector support):**
    ```bash
    mcp dev main.py
    ```
- **Standard execution:**
    ```bash
    python main.py
    # or
    mcp run main.py
    ```

The server will start and listen for MCP connections (stdio by default, or HTTP/SSE if configured).

---

## Running with Docker

You can containerize the MCP server using the provided `Dockerfile`.

1.  **Build the Docker image:**
    Navigate to the `mcp` directory in your terminal and run the following command:
    ```bash
    docker build -t feyod-mcp:latest .
    ```
    This will build an image tagged `feyod-mcp:latest`.

2.  **Run the Docker container:**
    You can run the container, mapping the internal port 8000 to an external port (e.g., 8000) on your host machine. You will also need to mount the database file as a volume so the container can access it.

    ```bash
    docker run -p 8000:8000 -v <absolute_path_to_feyod_db>:/app/../feyod/feyod.db feyod-mcp:latest
    ```
    Replace `<absolute_path_to_feyod_db>` with the absolute path to your `feyod.db` file on your host machine.

    Alternatively, you can pass environment variables directly:
    ```bash
    docker run -p 8000:8000 -e DATABASE_PATH="/app/../feyod/feyod.db" -e LLM_PROVIDER="google" -e LLM_API_KEY="YOUR_API_KEY_HERE" -e LLM_MODEL="gemini-2.5-flash-preview-05-20" -v <absolute_path_to_feyod_db>:/app/../feyod/feyod.db feyod-mcp:latest
    ```
    Remember to replace the placeholder values with your actual configuration.

The server inside the container will start and listen on `0.0.0.0:8000`.

---

## API Endpoints and Tools

This server exposes MCP tools for querying the Feyenoord database. Tools are discoverable via the MCP protocol (`tools/list`).

- **query_feyod_database**: Converts a natural language query about Feyenoord matches into a SQL query, executes it, and returns the SQL query and its result.

See the MCP Inspector or Claude Desktop's tool list for details.

---

## Adding New LLM Providers

To add support for a new provider:
1.  **Install Package:** Install the required LangChain integration package (e.g., `pip install langchain-anthropic`).
2.  **Update Factory:** Edit `llm_factory.py` to add the provider.
3.  **Update `.env` / README:** Add the necessary API key to your `.env` file.

---

## Dependencies

- Python 3.10+
- MCP Python SDK (`mcp`)
- See `requirements.txt` for specific package dependencies.
- Provider-specific packages (e.g., `langchain-openai`, `langchain-google-genai`).

---

## Debugging and Troubleshooting

- Use `mcp dev main.py` and the [MCP Inspector](https://github.com/modelcontextprotocol/inspector) for local testing.
- Logs are written to stderr and can be viewed in Claude Desktop logs or your terminal.
- For environment/config issues, check `.env` and Claude Desktop config.
- See [MCP Debugging Guide](https://modelcontextprotocol.info/llms-full.txt#debugging) for more tips.

---

## Security

[![MseeP.ai Security Assessment Badge](https://mseep.net/pr/jeroenvdmeer-feyod-mcp-badge.png)](https://mseep.ai/app/jeroenvdmeer-feyod-mcp)

## References

- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [MCP Documentation](https://modelcontextprotocol.info/llms-full.txt)
- [Official MCP Servers](https://github.com/modelcontextprotocol/servers)

---

## Disclaimer

This initiative is not affiliated with Feyenoord Rotterdam N.V. and therefore not an official Feyenoord product. The data provided through this server is unofficial and might be incorrect.