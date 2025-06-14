"""Configuration settings for the MCP server, loaded from environment variables."""

import os
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

DATABASE_PATH = os.getenv("DATABASE_PATH")
PORT = int(os.getenv("PORT", 8000))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# LLM Configuration
LLM_PROVIDER = os.getenv("LLM_PROVIDER").lower()
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_MODEL = os.getenv("LLM_MODEL")

# Example Loading Configuration
EXAMPLE_SOURCE = os.getenv("EXAMPLE_SOURCE").lower()
EXAMPLE_DB_CONNECTION_STRING = os.getenv("EXAMPLE_DB_CONNECTION_STRING")
EXAMPLE_DB_NAME = os.getenv("EXAMPLE_DB_NAME")
EXAMPLE_DB_COLLECTION = os.getenv("EXAMPLE_DB_COLLECTION")
