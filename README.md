# Feyod MCP Server

Model Context Protocol (MCP) server for querying Feyenoord football match data using natural language.

The Streamable HTTP server is publicly available at https://mcp.feyod.nl/mcp. A Docker container is available on [Docker Hub](https://hub.docker.com/r/jeroenvdmeer/feyod-mcp).

## Key features

This MCP server provides a natural language interface to query Feyod: Feyenoord Open Data. This allows users to get answers to their questions related to Feyenoord matches, players, opponents and related events.

The underlying Feyod database is maintained in the [`jeroenvdmeer/feyod` GitHub repository](https://github.com/jeroenvdmeer/feyod). You will need to obtain the latest SQL file from that repository to set up the required database.

The server uses LangChain to:
1.  Convert natural language questions into SQL queries (optionally leveraging few-shot examples for better accuracy).
2.  Validate the generated SQL.
3.  Attempt to fix invalid SQL using an LLM.
4.  Execute the valid SQL against a SQLite database.
5.  Return the raw query results.

LLM and embedding models are dynamically loaded based on configuration using a provider factory (`llm_factory.py`), allowing easy switching between providers like OpenAI, Google, etc.

## Consumption

### Using the Public Endpoint

The Feyod MCP server is publicly available at `https://mcp.feyod.nl/mcp`. You can connect to this endpoint from any MCP-compatible client, such as Claude Desktop.

### Using the Docker Container

A Docker image of the Feyod MCP server is available on Docker Hub. You can pull and run it using the following commands:

1.  **Pull the Docker image:**
    ```bash
    docker pull jeroenvdmeer/feyod-mcp
    ```

2.  **Run the Docker container:**
    You will need to provide the necessary environment variables for the LLM provider and API key. You can also mount the `feyod.db` file if you want to use a local database instead of the one included in the image.

    ```bash
    docker run -p 8000:8000 \
      -e LLM_PROVIDER="your_llm_provider" \
      -e LLM_API_KEY="your_api_key" \
      jeroenvdmeer/feyod-mcp
    ```
    Replace `your_llm_provider` and `your_api_key` with your actual LLM configuration.

    To mount a local database file:
    ```bash
    docker run -p 8000:8000 \
      -e LLM_PROVIDER="your_llm_provider" \
      -e LLM_API_KEY="your_api_key" \
      -v <absolute_path_to_feyod_db>:/app/feyod/feyod.db \
      jeroenvdmeer/feyod-mcp
    ```
    Replace `<absolute_path_to_feyod_db>` with the absolute path to your `feyod.db` file on your host machine.

## Tools

This server exposes MCP tools for querying the Feyenoord database. Tools are discoverable via the MCP protocol (`tools/list`).

- **answer_feyenoord_question**: Answers questions about Feyenoord. Questions can be asked in natural language, text, and can be about matches (lineups, results, goals, cards, etc.), players, and opponents.

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

## Configuration

Create a `.env` file in the `mcp` directory with the following variables:

```dotenv
# Path to the SQLite database file (relative to mcp folder or absolute)
DATABASE_PATH="../feyod/feyod.db"

# Server host binding (defaults to localhost/127.0.0.1)
HOST="127.0.0.1"

# Logging level (e.g., DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=INFO

# --- LLM Configuration ---
LLM_PROVIDER="google"  # or "openai", etc.
LLM_API_KEY="YOUR_API_KEY_HERE"
LLM_MODEL="gemini-2.5-flash"

# --- Example Loading Configuration (Optional) ---
EXAMPLE_SOURCE="local"  # or "mongodb"
EXAMPLE_DB_CONNECTION_STRING=""
EXAMPLE_DB_NAME="feyenoord_data"
EXAMPLE_DB_COLLECTION="examples"
```

**Notes:**
- Replace placeholder API key with your actual key.
- The `HOST` setting defaults to "127.0.0.1" for local development. When running in Docker, it's automatically set to "0.0.0.0" to allow external connections.
- Ensure the `LLM_PROVIDER` matches one defined in `llm_factory.py`.
- Install the necessary LangChain integration package for your chosen provider (e.g., `langchain-google-genai`).
- If using `EXAMPLE_SOURCE="mongodb"`, configure MongoDB settings as above.

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
    docker run -p 8000:8000 -e DATABASE_PATH="/app/../feyod/feyod.db" -e LLM_PROVIDER="google" -e LLM_API_KEY="YOUR_API_KEY_HERE" -e LLM_MODEL="gemini-2.5-flash" -v <absolute_path_to_feyod_db>:/app/../feyod/feyod.db feyod-mcp:latest
    ```
    Remember to replace the placeholder values with your actual configuration.

The server inside the container will start and listen on `0.0.0.0:8000`.

## Adding New LLM Providers

To add support for a new provider:
1.  **Install Package:** Install the required LangChain integration package (e.g., `pip install langchain-anthropic`).
2.  **Update Factory:** Edit `llm_factory.py` to add the provider.
3.  **Update `.env` / README:** Add the necessary API key to your `.env` file.

## Dependencies

- Python 3.10+
- See `requirements.txt` for specific package dependencies.
- Provider-specific packages (e.g., `langchain-openai`, `langchain-google-genai`).

## Debugging and Troubleshooting

- Use `mcp dev main.py` and the [MCP Inspector](https://github.com/modelcontextprotocol/inspector) for local testing.
- Logs are written to stderr and can be viewed in Claude Desktop logs or your terminal.
- For environment/config issues, check `.env` and Claude Desktop config.
- See [MCP Debugging Guide](https://modelcontextprotocol.info/llms-full.txt#debugging) for more tips.

## Security

This section provides an overview of the key security measures implemented in the MCP server. These measures are selected based on a risk assessment and the security considerations provided in the MCP documentation.

### Risk assessment

The key assets of the MCP server are:
1. The information in the Feyod database
2. The publicly exposed Streamable HTTP server that can be consumed by end-users

Both assets serve the key objective of the MCP server to provide correct answers to questions from the end-user.

#### Risks related to the information in the Feyod database

As a basis for the risk assessment you can find the analysis of the information security criteria in the following overview.

| Criterium | Impact | Description |
| --------- | ---------- | ----------- |
| Confidentiality | None | As the Feyod database is publicly available, exposure of the data will have no impact. |
| Integrity | High | The key features of the MCP server resolves around providing accurate answers to questions. When the data is no longer complete and/or correct, the MCP server can no longer live up to this promise.|
| Availability | High | The key features of the MCP server resolves around providing accurate answers to questions. When the data is no longer available, the MCP server can no longer live up to this promise.|

Given the importance of the integrity and availability of the data, interactions with the database which delete and/or alter the Feyod database are considered the key risks that impact the security of the information in the Feyod database. Such interactions can be performed by:
1. Misusing the MCP server to generate malicious SQL queries (e.g. `DELETE` and `UPDATE` queries)
1. Unauthorised access to the database in hosting platform of the MCP server

#### Risks related to the publicly exposed Streamable HTTP server

Given the objective to provide correct answers to questions from the end-user to the following key risks are considered:
1. Incorrect SQL queries and/or output messages generated by the LLM leading to incorrect answers
1. Excessive requests are made to the MCP server leading to unavailability of the service and high costs
1. Malicious requests are made to the MCP service which trigger a high number of costly LLM calls and lead to high costs

### Key security controls

Based on the key risks identified related to the information in the Feyod database and the publicly exposed Streamable HTTP server, the following key security controls are implemented.

#### Key controls related to the information in the Feyod database

| Risk                                                                                           | Control                             | Implementation Details                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| ---------------------------------------------------------------------------------------------- | ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Misusing the MCP server to generate malicious SQL queries (e.g. `DELETE` and `UPDATE` queries) | Prompt Engineering & Query Validation | **Prompt-Level Enforcement:** The system prompt sent to the LLM in `query_processor.py` contains the explicit instruction: `"DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.) to the database. Only SELECT statements are allowed."`<br><br>**Application-Level Guardrail:** After generation, the application code validates that the returned SQL string begins with `SELECT` (case-insensitive). This serves as a deterministic check to prevent the execution of other statement types.<br><br>**Read-Only Access:** For the publicly hosted service, the database file is mounted as read-only. This provides a strong, infrastructure-level guarantee that no write or delete operations can be performed, regardless of the generated SQL. |
| Unauthorised access to the database in hosting platform of the MCP server                      | Filesystem and Network Isolation      | **Local File Access:** Per standard configuration the SQLite database is a local file (`feyod.db`) and is not exposed over a network port. The application, as seen in `database.py`, accesses it directly from the filesystem, minimizing the network attack surface.<br><br>**Principle of Least Privilege:** In the production hosting environment, standard filesystem permissions are used to ensure that only the service account running the MCP server process has read access to the database file.                                                                                                            |

#### Key controls related to the publicly exposed Streamable HTTP server

| Risk                                                                                                 | Control                                 | Implementation Details                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| ---------------------------------------------------------------------------------------------------- | --------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Incorrect SQL queries and/or output messages generated by the LLM leading to incorrect answers         | Multi-Stage Validation Workflow         | **Context-Rich Generation:** To improve accuracy, the LLM is provided with the full database schema (from `database.get_schema_description`) and, when available, few-shot examples of valid question-query pairs (from `examples.py`).<br><br>**Pre-Execution Syntax Check:** In `query_processor.py`, every generated SQL query is first checked using an `EXPLAIN` statement (`check_sql_syntax` function). This validates the query's syntax against the database schema without actually executing it, catching most errors.<br><br>**Automated Fixing Loop:** If the syntax check fails, the workflow (`attempt_fix_sql` function) triggers a second LLM call, providing it with the invalid query and the specific database error it produced. This allows the model to attempt a correction, which is then re-validated before execution. |
| Excessive requests are made to the MCP server leading to unavailability of the service and high costs    | Resource & Infrastructure Limiting      | **Query Result Capping:** The SQL generation prompt instructs the LLM to `"always limit your query to at most 5 results"`, which prevents queries from returning excessively large datasets that could strain the server or client.<br><br>**Containerization:** The use of Docker allows for applying resource limits (CPU, memory) on the container, preventing a single runaway process from impacting the entire host machine.                                                                                                |
| Malicious requests are made to the MCP service which trigger a high number of costly LLM calls and lead to high costs | Efficient Workflow & External Monitoring | **Optimized LLM Usage:** The query processing workflow is designed to be efficient. For a valid user question, it typically requires only a single LLM call. The more expensive "fixer" call is only triggered upon failure of the initial generated query.|

### Security audits

[![MseeP.ai Security Assessment Badge](https://mseep.net/pr/jeroenvdmeer-feyod-mcp-badge.png)](https://mseep.ai/app/jeroenvdmeer-feyod-mcp)

## References

MCP resources:
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [MCP Documentation](https://modelcontextprotocol.info/llms-full.txt)
- [Official MCP Servers](https://github.com/modelcontextprotocol/servers)

Securing generative AI and LLM applications:
- [OWASP Top 10 for LLM Applications 2025](https://genai.owasp.org/llm-top-10/)
- [OWASP Agentic AI – Threats and Mitigations 1.0 (February 17, 2025)](https://genai.owasp.org/resource/agentic-ai-threats-and-mitigations/)
- [OWASP Multi-Agentic system Threat Modeling Guide 1.0](https://genai.owasp.org/resource/multi-agentic-system-threat-modeling-guide-v1-0/)

## Disclaimer

This initiative is not affiliated with Feyenoord Rotterdam N.V. and therefore not an official Feyenoord product. The data provided through this server is unofficial and might be incorrect.