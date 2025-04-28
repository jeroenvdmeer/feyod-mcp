"""Defines the tools available through the MCP server according to the MCP specification."""

MCP_TOOLS = [
    {
        "function": {
            "name": "get_schema",
            "description": "Retrieve the database schema description for the football matches database. Use this to understand table structures, column names, and types before generating a query.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "function": {
            "name": "generate_sql",
            "description": "Generate an SQLite query based on a natural language question about football matches, players, clubs, or seasons.",
            "parameters": {
                "type": "object",
                "properties": {
                    "natural_language_query": {
                        "type": "string",
                        "description": "The user's question in natural language (e.g., 'How many times did Feyenoord win against Ajax?', 'Wie scoorde het meest in 2023?')"
                    }
                },
                "required": ["natural_language_query"]
            }
        }
    },
    {
        "function": {
            "name": "check_query",
            "description": "Validate an SQLite query for syntactical correctness before execution against the football database. Does not check for semantic correctness or if the query returns the intended results.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sql_query": {
                        "type": "string",
                        "description": "The SQLite query string to validate."
                    }
                },
                "required": ["sql_query"]
            }
        }
    },
    {
        "function": {
            "name": "execute_query",
            "description": "Execute a validated SQLite query against the football matches database and return the results.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sql_query": {
                        "type": "string",
                        "description": "The SQLite query string to execute."
                    },
                    "params": {
                        "type": "array",
                        "description": "Optional list of parameters to safely bind to the query placeholders.",
                        "items": {
                            "type": "string"
                        }
                    }
                },
                "required": ["sql_query"]
            }
        }
    }
]
