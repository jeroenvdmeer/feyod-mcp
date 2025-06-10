"""Database connection and interaction logic for the MCP server."""

import aiosqlite
import logging
from pathlib import Path
import config

logger = logging.getLogger(__name__)
DATABASE_PATH = Path(config.DATABASE_PATH)


async def get_db_connection():
    """Establishes an asynchronous connection to the SQLite database."""
    try:
        if not DATABASE_PATH.exists():
            logger.error(f"Database file not found at: {DATABASE_PATH}")
            raise FileNotFoundError(f"Database file not found at: {DATABASE_PATH}")
        conn = await aiosqlite.connect(DATABASE_PATH)
        conn.row_factory = aiosqlite.Row  # Return rows as dictionary-like objects
        logger.info(f"Successfully connected to database: {DATABASE_PATH}")
        return conn
    except aiosqlite.Error as e:
        logger.error(f"Error connecting to database: {e}")
        raise


async def close_db_connection(conn: aiosqlite.Connection):
    """Closes the database connection."""
    if conn:
        await conn.close()
        logger.info("Database connection closed.")


async def get_schema_description() -> str:
    """Retrieves a string description of the database schema."""
    conn = None
    try:
        conn = await get_db_connection()
        cursor = await conn.cursor()

        # Get table names
        await cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = await cursor.fetchall()

        schema_parts = []
        for table in tables:
            table_name = table["name"]
            schema_parts.append(f"Table '{table_name}':")

            # Get column details for each table
            await cursor.execute(f"PRAGMA table_info({table_name});")
            columns = await cursor.fetchall()
            for column in columns:
                col_name = column["name"]
                col_type = column["type"]
                col_pk = " (Primary Key)" if column["pk"] else ""
                schema_parts.append(f"  - {col_name}: {col_type}{col_pk}")
            schema_parts.append("")  # Add a blank line between tables

        return "\n".join(schema_parts)
    except aiosqlite.Error as e:
        logger.error(f"Error retrieving schema: {e}")
        return f"Error retrieving schema: {e}"
    finally:
        await close_db_connection(conn)


async def execute_query(sql: str, params: tuple = ()) -> list[dict]:
    """Executes a given SQL query safely with parameters and returns results."""
    conn = None
    results = []
    try:
        conn = await get_db_connection()
        cursor = await conn.cursor()
        logger.info(f"Executing SQL: {sql} with params: {params}")
        await cursor.execute(sql, params)
        rows = await cursor.fetchall()
        # Convert Row objects to dictionaries for JSON serialization
        results = [dict(row) for row in rows]
        await conn.commit()  # Commit if the query involved changes (though selects don't strictly need it)
        logger.info(f"Query executed successfully. Fetched {len(results)} rows.")
    except aiosqlite.Error as e:
        logger.error(f"Error executing query '{sql}' with params {params}: {e}")
        # In a real app, you might want to raise a custom exception
        raise ValueError(f"Error executing query: {e}")
    finally:
        await close_db_connection(conn)
    return results


# Example usage (for testing purposes)
async def main():
    print("Testing database connection...")
    conn = await get_db_connection()
    await close_db_connection(conn)
    print("Connection test successful.")

    print("\nFetching schema...")
    schema = await get_schema_description()
    print(schema)

    print("\nTesting query execution (example: first 5 clubs)...")
    try:
        clubs = await execute_query("SELECT clubId, clubName FROM clubs LIMIT ?;", (5,))
        print(clubs)
    except Exception as e:
        print(f"Query failed: {e}")


if __name__ == "__main__":
    import asyncio

    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
