# MS Fabric MCP Server

This project provides a Model Context Protocol (MCP) server that enables clients to query and explore schemas in Microosft Fabric items.

The goal is to enable more robust automation of data engineering flows by enabling the agent/llm to query and verify 

Enable LLMs to query lakehouses, warehouses and SQL databases to make automation of building data pipelines mor robust.

It uses Azure Active Directory (AAD) token authentication.

## Prerequisites

*   **Python 3.10+** installed.
*   **Microsoft ODBC Driver for SQL Server** installed.
    *   https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server?view=sql-server-ver16
    *   Commonly "ODBC Driver 17 for SQL Server" or "ODBC Driver 18 for SQL Server". Driver 18 is recommended for better AAD support.
*   **Azure CLI** installed and authenticated:
    *   Run `az login` and complete the authentication flow, `az login --allow-no-subscriptions` might be necessary.
    *   The authenticated user/principal must have appropriate permissions (e.g., `contributor` role in the workspace or owner of the Fabric item).

## Setup Instructions

pip installation
```bash
pip install ms-fabric-mcp
```

uv installation
```bash
uv add ms-fabric-mcp
# or
uv pip install ms-fabric-mcp
```

Example `mcp.json` configuration for use with Cursor,  Claude Desktop, etc.

```json
"ms-fabric-mcp": {
  "command": "uv",
  "args": [
    "--directory",
    "path/to/server",
    "run",
    "mcp"
  ],
  "env": {
      "SQL_SERVER_NAME": "xyz-xyz.datawarehouse.fabric.microsoft.com",
      "SQL_DATABASE_NAME": "dev",
      "ODBC_DRIVER": "{ODBC Driver 18 for SQL Server}"
  }
}
```

### Alternatives

1.  **Clone the Repository (Optional):**
    ```bash
    git clone <repository_url>
    cd ms_fabric_mcp # Or your project directory name
    ```

2.  **Install Dependencies:**
    ```bash
    uv sync
    ```

provide required env variables and run the MCP server `uv run mcp`

## Configuration

The server requires the following environment variables to be set before running:

*   `SQL_SERVER_NAME`: The fully qualified domain name of your SQL Server instance from Fabric (e.g., `xyz-xyz.datawarehouse.fabric.microsoft.com`).
*   `SQL_DATABASE_NAME`: The name of the database to connect to (not too important in Fabric, shared connection host within a single workspace).
*   `ODBC_DRIVER` (Optional): The name of your ODBC driver as it appears in your system's ODBC configuration. 
    *   Defaults to `{ODBC Driver 18 for SQL Server}` if not set.
    *   Examples: `{ODBC Driver 17 for SQL Server}`, `{ODBC Driver 18 for SQL Server}`.

## Tools

The SQL Server MCP exposes the following tools for interacting with SQL Server databases:

### query

Executes a read-only SQL query against the configured SQL Server database. This tool validates that only SELECT statements are executed for security purposes.

**Parameters:**
- `sql`: The SQL query to execute (must be a read-only SELECT statement)

**Returns:**
- A list of dictionaries where each dictionary represents a row from the query result
- If no results are found, returns a dictionary with a message

### search_tables

Search for tables by name in the INFORMATION_SCHEMA.TABLES view. Supports case-insensitive wildcards and schema filtering.

**Parameters:**
- `table_name`: Full or partial table name to search for (case-insensitive)
- `schema_name` (optional): Schema name to filter results

**Returns:**
- A list of dictionaries with metadata about matching tables
- If no matching tables are found, returns a dictionary with a message

### search_columns_by_table

Search for columns in tables matching the provided name. Retrieves detailed column metadata from the INFORMATION_SCHEMA.COLUMNS view.

**Parameters:**
- `table_name`: Full or partial table name to search for (case-insensitive)
- `schema_name` (optional): Schema name to filter results

**Returns:**
- A list of dictionaries where each dictionary represents a column with its metadata
- If no matching columns are found, returns a dictionary with a message

### search_tables_by_column

Search for tables containing columns matching the provided name. Helps locate tables that have specific columns.

**Parameters:**
- `column_name`: Full or partial column name to search for (case-insensitive)
- `schema_name` (optional): Schema name to filter results

**Returns:**
- A list of dictionaries where each dictionary represents a column with its table and metadata
- If no matching columns are found, returns a dictionary with a message

### search_query_patterns

Search historical query patterns from the queryinsights.exec_requests_history view. This tool helps discover successful query patterns that can be reused or adapted, with literal values replaced by placeholders.

**Parameters:**
- `search_term`: Text to search for in queries (table names, column names, etc.)
- `use_regex` (optional): If true, interpret search_term as regex pattern (default: false)
- `min_execution_count` (optional): Minimum times the query pattern has been executed (default: 1)
- `max_execution_time_ms` (optional): Only include queries faster than this threshold (default: 60 seconds)
- `limit` (optional): Maximum number of patterns to return (default: 10)

**Returns:**
- A list of dictionaries, each containing:
  - `pattern`: The normalized query pattern with literals replaced by placeholders
  - `example`: A concrete example with actual values
  - `execution_stats`: Statistics about execution frequency and performance
  - `tables_referenced`: List of tables referenced in the query
  - `columns_referenced`: List of columns referenced in the query
  - `last_executed`: When this pattern was last used successfully
- If no patterns match the criteria, returns a dictionary with a message

## Example Usage (Conceptual)

An MCP client would interact with the server by calling the `query` tool.


```json
// Hypothetical MCP client request body
{
  "sql": "SELECT TOP 10 * FROM YourTable;"
}
```

The server would respond with the query results or an error message.

```json
// Example successful response (structure may vary slightly based on FastMCP)
{
  "result": [
    { "Column1": "Value1", "Column2": 123 },
    { "Column1": "Value2", "Column2": 456 }
    // ... more rows
  ]
}

// Example error response
{
  "error": {
    "title": "Database Execution Error",
    "detail": "Database error occurred: [Some pyodbc error message]",
    "status_code": 500
  }
}
```

### Example prompts

> Create a query that joins table X and Y, validate that the join doesn't produce any duplicate rows, use the query tool as appropriate

> Find all tables in the database that might contain customer information. Then list all columns in those tables.

> Search for tables containing "order" in their name and show me their structure. Then build a query that shows the total number of orders per customer for the last month.

> Find all tables that have a column named "user_id" or similar

> Based on historical query patterns, help me write an efficient query to find the top 10 products by revenue. Use the patterns as a reference for good query structure.

> Explore the database schema to find all tables related to authentication or user permissions, then show me a sample of each table's data.
