"""Handles the core logic for processing natural language queries to SQL execution and formatting."""

import logging
import aiosqlite
from typing import List, Dict, Any, Tuple, Optional

# LangChain imports
from langchain.prompts import ChatPromptTemplate

# Corrected import for BaseChatModel
from langchain.chat_models.base import BaseChatModel

import database

# Import the factory functions and the example selector getter
from llm_factory import get_llm  # Import from the factory
from examples import get_few_shot_selector

logger = logging.getLogger(__name__)

# --- Prompt Definitions ---


def build_sql_generation_chain():
    """Builds the SQL generation chain with the latest few-shot selector and LLM from the factory."""
    prompt_messages = [
        (
            "system",
            """
You are an expert SQLite assistant with strong attention to detail. Given the question, database table schema, and example queries, output a valid SQLite query. When generating the query, follow these rules:

**Core Logic & Context:**
- The input question is likely from the perspective of a fan of the football club Feyenoord. Use this knowledge when generating a query. For example, when data about a football match is requested and only an opponent is mentioned, assume that the other club is Feyenoord.
- When a club name is referenced, do not just use the columns homeClubName and awayClubName in the WHERE statement. Be smart, and also query the clubName column in the clubs table using the clubId. Additionally, take into account that a typo can have been made in the club name, so make the query flexible (e.g., using LIKE or checking variations if appropriate, but prioritize joining with the `clubs` table via `clubId`).
- When dates are mentioned in the question, remember to use the `strftime` function for comparisons if the database stores dates as text or numbers in a specific format. Assume dates are stored in 'YYYY-MM-DD HH:MM:SS' format unless schema indicates otherwise.

**Query Structure & Best Practices:**
- Unless the user specifies a specific number of examples they wish to obtain, always limit your query to at most 5 results. You can order the results by a relevant column to return the most interesting examples in the database.
- Never query for all the columns from a specific table (e.g., `SELECT *`). Only select the specific columns relevant to the question.
- DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.) to the database. Only SELECT statements are allowed.
- Double-check for common mistakes:
    - Using `NOT IN` with subqueries that might return NULL values.
    - Using `UNION` when `UNION ALL` is sufficient and more performant (if duplicates are acceptable or impossible).
    - Using `BETWEEN` for ranges; ensure inclusivity/exclusivity matches the intent.
    - Data type mismatches in predicates (e.g., comparing text to numbers).
    - Properly quoting identifiers (table names, column names) if they contain spaces or reserved keywords, although standard SQL identifiers usually don't require quotes in SQLite.
    - Using the correct number of arguments for SQL functions.
    - Casting data types explicitly if needed for comparisons or functions.
    - Ensuring correct join conditions, especially when joining multiple tables. Use the `clubs` table to select clubs based on `clubId` instead of relying solely on `homeClubName` and `awayClubName` text columns in other tables like `matches`.
    - Correct usage and placement of parentheses in complex `WHERE` clauses.

**Output Format:**
- Only output the raw SQL query. Do not include explanations, markdown formatting (like ```sql ... ```), or any text other than the SQL query itself.
""",
        ),
    ]
    few_shot_selector = get_few_shot_selector()
    if few_shot_selector:
        logger.info("Adding few-shot examples to SQL generation prompt.")
        prompt_messages.append(few_shot_selector)
    else:
        logger.warning(
            "Few-shot examples not available, SQL generation prompt will not include them."
        )
    prompt_messages.append(
        (
            "human",
            "=== Question:\n{natural_language_query}\n=== Schemas:\n{schema}\n=== Resulting query:",
        )
    )
    prompt_template = ChatPromptTemplate.from_messages(prompt_messages)

    llm: Optional[BaseChatModel] = get_llm()  # Get LLM instance from factory
    if not llm:
        logger.error(
            "LLM not available from factory. Cannot build SQL generation chain."
        )
        return None

    # Return a chain that invokes the LLM directly; parser is unnecessary for raw string output
    return prompt_template | llm


def build_sql_fixing_chain():
    """Builds the SQL fixing chain using the LLM from the factory."""
    prompt_template = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """
You are an expert SQLite assistant. You are given an invalid SQLite query, the error message it produced, the database schema, and the original natural language query.
Your task is to fix the SQL query so it is syntactically correct and likely addresses the user's original intent based on the provided context.

Database Schema:
{schema}

Original Natural Language Query:
{original_nl_query}

Invalid SQL Query:
{invalid_sql}

Syntax Error:
{error_message}

Rules for Fixing:
- Analyze the error message and the invalid SQL to understand the cause of the syntax error.
- Refer to the database schema to ensure table and column names are correct and used appropriately.
- Consider the original natural language query to maintain the intended logic.
- Apply SQLite syntax rules correctly. Pay attention to function usage, join conditions, quoting, data types, and clause structure.
- Only output the corrected, raw SQL query. Do not include explanations or markdown formatting.
""",
            ),
        ]
    )
    llm: Optional[BaseChatModel] = get_llm()  # Get LLM instance from factory
    if not llm:
        logger.error("LLM not available from factory. Cannot build SQL fixing chain.")
        return None

    # Return a chain that invokes the LLM directly; parser is unnecessary for raw string output
    return prompt_template | llm


# --- Core Functions ---


async def generate_sql_from_nl(natural_language_query: str, schema: str) -> str:
    """Converts natural language query to SQL using a LangChain chain built with the factory LLM."""
    # Check LLM availability first
    if not get_llm():
        raise ValueError(
            "LangChain LLM not initialized via factory. Cannot generate SQL."
        )

    sql_generation_chain = build_sql_generation_chain()
    if not sql_generation_chain:
        # This implies LLM was available moments ago but chain build failed (unlikely)
        raise ValueError("SQL generation chain could not be built.")

    logger.info(f"Generating SQL for: {natural_language_query} using LangChain")
    try:
        # Invoke the chain which returns an AIMessage; extract its content
        response = await sql_generation_chain.ainvoke(
            {"schema": schema, "natural_language_query": natural_language_query}
        )
        # Extract text from response object
        if hasattr(response, "content"):
            sql_text = response.content
        else:
            sql_text = str(response)
        sql_query = sql_text.strip()
        # Basic cleanup (optional, LLM should follow instructions)
        if sql_query.startswith("```sql"):
            sql_query = sql_query[6:]
        if sql_query.endswith("```"):
            sql_query = sql_query[:-3]
        sql_query = sql_query.strip()

        logger.info(f"LangChain generated SQL: {sql_query}")
        if not sql_query or not sql_query.upper().startswith("SELECT"):
            raise ValueError("LangChain chain did not return a valid SELECT query.")
        return sql_query
    except Exception as e:
        logger.error(f"Error invoking LangChain SQL generation chain: {e}")
        raise ValueError(f"Failed to generate SQL using LangChain: {e}")


async def check_sql_syntax(sql_query: str) -> Tuple[bool, Optional[str]]:
    """Checks the syntax of an SQLite query using EXPLAIN. Returns (True, None) on success, (False, error_message) on failure."""
    conn = None
    try:
        conn = await database.get_db_connection()
        await conn.execute(f"EXPLAIN {sql_query}")
        logger.info(f"SQL syntax check passed for: {sql_query}")
        return True, None
    except aiosqlite.Error as e:
        error_message = str(e)
        logger.warning(
            f"SQL syntax check failed for query '{sql_query}': {error_message}"
        )
        return False, error_message
    finally:
        await database.close_db_connection(conn)


async def attempt_fix_sql(
    invalid_sql: str, error_message: str, schema: str, original_nl_query: str
) -> str:
    """Attempts to fix an invalid SQL query using a LangChain chain built with the factory LLM."""
    # Check LLM availability first
    if not get_llm():
        raise ValueError("LangChain LLM not initialized via factory. Cannot fix SQL.")

    sql_fixing_chain = build_sql_fixing_chain()
    if not sql_fixing_chain:
        raise ValueError("SQL fixing chain could not be built.")

    logger.warning(
        f"Attempting to fix SQL: {invalid_sql} based on error: {error_message} using LangChain"
    )
    try:
        # Invoke the chain which returns an AIMessage; extract its content
        response = await sql_fixing_chain.ainvoke(
            {
                "schema": schema,
                "original_nl_query": original_nl_query,
                "invalid_sql": invalid_sql,
                "error_message": error_message,
            }
        )
        # Extract text from response object
        if hasattr(response, "content"):
            fixed_text = response.content
        else:
            fixed_text = str(response)
        fixed_sql = fixed_text.strip()
        # Basic cleanup (optional)
        if fixed_sql.startswith("```sql"):
            fixed_sql = fixed_sql[6:]
        if fixed_sql.endswith("```"):
            fixed_sql = fixed_sql[:-3]
        fixed_sql = fixed_sql.strip()

        logger.info(f"LangChain proposed fixed SQL: {fixed_sql}")
        if not fixed_sql or not fixed_sql.upper().startswith("SELECT"):
            raise ValueError(
                "LangChain chain did not return a valid fixed SELECT query."
            )
        return fixed_sql
    except Exception as e:
        logger.error(f"Error invoking LangChain SQL fixing chain: {e}")
        raise ValueError(f"Failed to fix SQL using LangChain: {e}")


async def process_query_workflow(
    natural_language_query: str,
) -> List[Dict[str, Any]] | str:
    """
    Runs the full workflow: Text -> SQL -> Check -> (Fix) -> Execute using the factory LLM.
    Returns the raw query results as a list of dictionaries, or an error string.
    """
    max_fix_attempts = 1
    attempts = 0
    sql_query = None
    schema = None
    error_message = "An unknown syntax error occurred."

    # Check LLM availability at the start of the workflow using the factory getter
    if not get_llm():
        logger.error("LLM not initialized via factory. Cannot process query workflow.")
        return "Server configuration error: LLM not initialized."

    try:
        # 1. Get Schema
        logger.info("Workflow step: Fetching schema")
        schema = await database.get_schema_description()
        if "Error retrieving schema" in schema:
            return f"Failed to retrieve database schema: {schema}"

        # 2. Generate SQL (using updated LangChain function)
        logger.info("Workflow step: Generating initial SQL")
        sql_query = await generate_sql_from_nl(natural_language_query, schema)

        while attempts <= max_fix_attempts:
            # 3. Check SQL Syntax
            logger.info(f"Workflow step: Checking SQL syntax (Attempt {attempts + 1})")
            is_valid, current_error_message = await check_sql_syntax(sql_query)
            if current_error_message:
                error_message = current_error_message

            if is_valid:
                logger.info("SQL syntax is valid.")
                break
            else:
                attempts += 1
                if attempts > max_fix_attempts:
                    logger.error(
                        f"SQL syntax invalid after maximum fix attempts. Last error: {error_message}"
                    )
                    return f"Generated SQL query has invalid syntax after fix attempts: {error_message}"

                # 4. Attempt to Fix SQL
                logger.warning(
                    f"Workflow step: Attempting to fix invalid SQL. Error: {error_message}"
                )
                sql_query = await attempt_fix_sql(
                    sql_query, error_message, schema, natural_language_query
                )
                logger.info(f"Retrying with fixed SQL: {sql_query}")

        # 5. Execute SQL Query (no change needed)
        logger.info("Workflow step: Executing SQL query")
        results = await database.execute_query(sql_query)
        logger.info(f"Query executed. Results count: {len(results)}")

        # 6. Return Raw Results
        return results

    except (ValueError, aiosqlite.Error, FileNotFoundError) as e:
        logger.exception(f"Error during query processing workflow: {e}")
        return f"Error processing your request: {e}"
    except Exception as e:
        logger.exception(
            "An unexpected error occurred during query processing workflow."
        )
        return f"An unexpected error occurred: {e}"
