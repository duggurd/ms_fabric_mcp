from fastmcp import FastMCP
from fastmcp.exceptions import FastMCPError
import pyodbc
import os
import re
from typing import Optional, Union, Dict, List
from collections import defaultdict

from db_connection import get_db_connection
from sql_validator import is_readonly_query
from query_normalizer import normalize_query, generate_pattern_key

app = FastMCP(
    title="SQL Server Read-Only Query MCP",
    description="An MCP server to run read-only SELECT queries against a Microsoft SQL Server.",
    version="0.1.0"
)

@app.tool(
    name="query",
    description="Executes a read-only SQL query against the configured SQL Server database.",
)
async def query(sql: str) -> Union[List[Dict], Dict[str, str]]:
    """Executes a read-only SQL query against the configured SQL Server database.
    
    Args:
        sql: The SELECT SQL query to execute.
        
    Returns:
        A list of dictionaries, where each dictionary represents a row from the query result.
        If no results are found, returns a dictionary with a message.
        
    Raises:
        FastMCPError: If the query is not a SELECT statement, if database connection fails,
                      or if any other error occurs during query execution.
    """

    if not is_readonly_query(sql):
        return {
            "error": "Invalid Query Type: The provided SQL query is not a read-only SELECT statement. Only SELECT queries are allowed.",
        }

    cnxn = None
    try:
        # get_db_connection handles environment variable checks and AAD token
        cnxn = get_db_connection()
        cursor = cnxn.cursor()
        
        print(f"Executing SQL query: {sql[:200]}..." if len(sql) > 200 else f"Executing SQL query: {sql}")
        cursor.execute(sql)
        
        # Fetch results as a list of dictionaries
        columns = [column[0] for column in cursor.description]
        results = []
        for row in cursor.fetchall():
            results.append(dict(zip(columns, row)))
        
        print(f"Query returned {len(results)} rows.")
        
        # Check if results are empty
        if not results:
            return {"message": "No results found for the specified query."}
        
        return results

    except pyodbc.Error as db_err:
        error_message = f"Database error occurred: {str(db_err)}"
        print(error_message) # Log to server console
        # Attempt to get more specific error details if available
        # sqlstate = db_err.args[0] if len(db_err.args) > 0 else "N/A"
        # detailed_message = db_err.args[1] if len(db_err.args) > 1 else str(db_err)
        return {
            "error": "Database Execution Error: " + error_message,
        }
    except ConnectionError as conn_err: # Raised by get_db_connection or get_aad_token
        error_message = f"Database connection failed: {str(conn_err)}"
        print(error_message)
        # Surface authentication errors clearly
        return error_message
    except Exception as e:
        error_message = f"An unexpected error occurred during query execution: {str(e)}"
        print(error_message)
        return {
            "error": "Unexpected Server Error: " + error_message,
        }
    finally:
        if cnxn:
            print("Closing database connection.")
            cnxn.close()

@app.tool(
    name="search_tables",
    description="Search for tables by name, wildcard, case insensitive, and schema in the INFORMATION_SCHEMA.TABLES view.",
)
async def search_tables(table_name: str, schema_name: Optional[str] = None) -> Union[List[Dict], Dict[str, str]]:
    """Search for tables by name in the INFORMATION_SCHEMA.TABLES view.
    
    Args:
        table_name: Full or partial table name to search for (case-insensitive)
        schema_name: Optional schema name to filter results
        
    Returns:
        A list of dictionaries, where each dictionary represents a matching table with its metadata.
        If no matching tables are found, returns a dictionary with a message.
        
    Raises:
        FastMCPError: If database connection fails or any other error occurs during query execution.
    """
    # Build SQL query with parameterized query to prevent SQL injection
    sql = """
    SELECT 
        TABLE_CATALOG,
        TABLE_SCHEMA,
        TABLE_NAME,
        TABLE_TYPE
    FROM 
        INFORMATION_SCHEMA.TABLES
    WHERE 
        LOWER(TABLE_NAME) LIKE LOWER(?)
    """
    
    # Add schema filter if provided
    params = [f'%{table_name}%']
    if schema_name:
        sql += " AND TABLE_SCHEMA = ?"
        params.append(schema_name)
    
    # Add ordering for consistent results
    sql += " ORDER BY TABLE_SCHEMA, TABLE_NAME"
    
    # Ensure the query is valid
    if not is_readonly_query(sql):
        return {
            "error": "Invalid Query Type: The generated SQL query is not a read-only SELECT statement.",
        }
        
    cnxn = None
    try:
        cnxn = get_db_connection()
        cursor = cnxn.cursor()
        
        print(f"Executing search_tables query for table_name: '{table_name}', schema_name: '{schema_name or 'None'}'")
        cursor.execute(sql, params)
        
        # Fetch results as a list of dictionaries
        columns = [column[0] for column in cursor.description]
        results = []
        for row in cursor.fetchall():
            results.append(dict(zip(columns, row)))
        
        print(f"Query returned {len(results)} tables.")
        
        # Check if results are empty
        if not results:
            return {"message": f"No tables found matching the name '{table_name}'" + 
                    (f" in schema '{schema_name}'" if schema_name else "") + "."}
        
        return results
        
    except pyodbc.Error as db_err:
        error_message = f"Database error occurred: {str(db_err)}"
        print(error_message)
        return {
            "error": "Database Execution Error: " + error_message,
        }
    except ConnectionError as conn_err:
        error_message = f"Database connection failed: {str(conn_err)}"
        print(error_message)
        return {
            "error": "Database Connection Error: " + error_message,
        }
    except Exception as e:
        error_message = f"An unexpected error occurred during query execution: {str(e)}"
        print(error_message)
        return {
            "error": "Unexpected Server Error: " + error_message,
        }
    finally:
        if cnxn:
            print("Closing database connection.")
            cnxn.close()

@app.tool(
    name="search_columns_by_table",
    description="Search for columns in tables matching the provided name, wildcard, case insensitive, and schema in the INFORMATION_SCHEMA.COLUMNS view.",
)
async def search_columns_by_table(table_name: str, schema_name: Optional[str] = None) -> Union[List[Dict], Dict[str, str]]:
    """Search for columns in tables matching the provided name.
    
    Args:
        table_name: Full or partial table name to search for (case-insensitive)
        schema_name: Optional schema name to filter results
        
    Returns:
        A list of dictionaries, where each dictionary represents a column with its metadata.
        If no matching columns are found, returns a dictionary with a message.
        
    Raises:
        FastMCPError: If database connection fails or any other error occurs during query execution.
    """
    # Build SQL query with parameterized query to prevent SQL injection
    sql = """
    SELECT 
        TABLE_CATALOG,
        TABLE_SCHEMA,
        TABLE_NAME,
        COLUMN_NAME,
        ORDINAL_POSITION,
        COLUMN_DEFAULT,
        IS_NULLABLE,
        DATA_TYPE,
        CHARACTER_MAXIMUM_LENGTH,
        NUMERIC_PRECISION,
        NUMERIC_SCALE
    FROM 
        INFORMATION_SCHEMA.COLUMNS
    WHERE 
        LOWER(TABLE_NAME) LIKE LOWER(?)
    """
    
    # Add schema filter if provided
    params = [f'%{table_name}%']
    if schema_name:
        sql += " AND TABLE_SCHEMA = ?"
        params.append(schema_name)
    
    # Add ordering for consistent results
    sql += " ORDER BY TABLE_SCHEMA, TABLE_NAME, ORDINAL_POSITION"
    
    # Ensure the query is valid
    if not is_readonly_query(sql):
        raise FastMCPError(
            "Invalid Query Type: The generated SQL query is not a read-only SELECT statement."
        )
        
    cnxn = None
    try:
        cnxn = get_db_connection()
        cursor = cnxn.cursor()
        
        print(f"Executing search_columns_by_table query for table_name: '{table_name}', schema_name: '{schema_name or 'None'}'")
        cursor.execute(sql, params)
        
        # Fetch results as a list of dictionaries
        columns = [column[0] for column in cursor.description]
        results = []
        for row in cursor.fetchall():
            results.append(dict(zip(columns, row)))
        
        print(f"Query returned {len(results)} columns.")
        
        # Check if results are empty
        if len(results) == 0:
            return {"message": f"No columns found for tables matching the name '{table_name}'" + 
                    (f" in schema '{schema_name}'" if schema_name else "") + "."}
        
        return results
        
    except pyodbc.Error as db_err:
        error_message = f"Database error occurred: {str(db_err)}"
        print(error_message)
        return {
            "error": "Database Execution Error: " + error_message,
        }
    except ConnectionError as conn_err:
        error_message = f"Database connection failed: {str(conn_err)}"
        print(error_message)
        return {
            "error": "Database Connection Error: " + error_message,
        }
    except Exception as e:
        error_message = f"An unexpected error occurred during query execution: {str(e)}"
        print(error_message)
        return {
            "error": "Unexpected Server Error: " + error_message,
        }
    finally:
        if cnxn:
            print("Closing database connection.")
            cnxn.close()

@app.tool(
    name="search_tables_by_column",
    description="Search for tables containing columns matching the provided name, wildcard, case insensitive, and schema in the INFORMATION_SCHEMA.COLUMNS view.",
)
async def search_tables_by_column(column_name: str, schema_name: Optional[str] = None) -> Union[List[Dict], Dict[str, str]]:
    """Search for tables containing columns matching the provided name.
    
    Args:
        column_name: Full or partial column name to search for (case-insensitive)
        schema_name: Optional schema name to filter results
        
    Returns:
        A list of dictionaries, where each dictionary represents a column with its table and metadata.
        If no matching columns are found, returns a dictionary with a message.
        
    Raises:
        FastMCPError: If database connection fails or any other error occurs during query execution.
    """
    # Build SQL query with parameterized query to prevent SQL injection
    sql = """
    SELECT 
        TABLE_CATALOG,
        TABLE_SCHEMA,
        TABLE_NAME,
        COLUMN_NAME,
        ORDINAL_POSITION,
        COLUMN_DEFAULT,
        IS_NULLABLE,
        DATA_TYPE,
        CHARACTER_MAXIMUM_LENGTH,
        NUMERIC_PRECISION,
        NUMERIC_SCALE
    FROM 
        INFORMATION_SCHEMA.COLUMNS
    WHERE 
        LOWER(COLUMN_NAME) LIKE LOWER(?)
    """
    
    # Add schema filter if provided
    params = [f'%{column_name}%']
    if schema_name:
        sql += " AND TABLE_SCHEMA = ?"
        params.append(schema_name)
    
    # Add ordering for consistent results
    sql += " ORDER BY TABLE_SCHEMA, TABLE_NAME, ORDINAL_POSITION"
    
    # Ensure the query is valid
    if not is_readonly_query(sql):
        raise FastMCPError(
            "Invalid Query Type: The generated SQL query is not a read-only SELECT statement."
        )
        
    cnxn = None
    try:
        cnxn = get_db_connection()
        cursor = cnxn.cursor()
        
        print(f"Executing search_tables_by_column query for column_name: '{column_name}', schema_name: '{schema_name or 'None'}'")
        cursor.execute(sql, params)
        
        # Fetch results as a list of dictionaries
        columns = [column[0] for column in cursor.description]
        results = []
        for row in cursor.fetchall():
            results.append(dict(zip(columns, row)))
        
        print(f"Query returned {len(results)} columns.")
        
        # Check if results are empty
        if len(results) == 0:
            return {"message": f"No columns found matching the name '{column_name}'" + 
                    (f" in schema '{schema_name}'" if schema_name else "") + "."}
        
        return results
        
    except pyodbc.Error as db_err:
        error_message = f"Database error occurred: {str(db_err)}"
        print(error_message)
        return {
            "error": "Database Execution Error: " + error_message,
        }
    except ConnectionError as conn_err:
        error_message = f"Database connection failed: {str(conn_err)}"
        print(error_message)
        return {
            "error": "Database Connection Error: " + error_message,
        }
    except Exception as e:
        error_message = f"An unexpected error occurred during query execution: {str(e)}"
        print(error_message)
        return {
            "error": "Unexpected Server Error: " + error_message,
        }
    finally:
        if cnxn:
            print("Closing database connection.")
            cnxn.close()

@app.tool(
    name="search_query_patterns",
    description="Search historical query patterns matching the provided search criteria.",
)
async def search_query_patterns(
    search_term: str,
    use_regex: bool = False,
    min_execution_count: int = 1,
    max_execution_time_ms: int = 60000,
    limit: int = 10
) -> Union[List[Dict], Dict[str, str]]:
    """Search historical query patterns matching the provided search criteria.
    
    Args:
        search_term: Text to search for in queries (table names, column names, etc.)
        use_regex: If True, interpret search_term as regex pattern (Python re syntax)
        min_execution_count: Minimum times the query pattern has been executed
        max_execution_time_ms: Only include queries faster than this threshold (default 60 seconds)
        limit: Maximum number of patterns to return
        
    Returns:
        A list of dictionaries, each containing:
        - pattern: The normalized query pattern with literals replaced by placeholders
        - example: A concrete example with actual values
        - execution_stats: Statistics about execution frequency and performance
        - tables_referenced: List of tables referenced in the query
        - last_executed: When this pattern was last used successfully
        
    Raises:
        FastMCPError: If database connection fails or any other error occurs during query execution.
    """
    # SQL to retrieve successful queries
    sql = """
    SELECT
        command,
        total_elapsed_time_ms,
        end_time,
        query_hash
    FROM 
        queryinsights.exec_requests_history
    WHERE 
        status = 'Succeeded'
        AND total_elapsed_time_ms < ?
        AND command LIKE ?
    ORDER BY
        end_time DESC
    """
    
    # Parameters for the query
    params = [max_execution_time_ms, f'%{search_term}%']
    
    cnxn = None
    try:
        cnxn = get_db_connection()
        cursor = cnxn.cursor()
        
        print(f"Executing search_query_patterns for search_term: '{search_term}', " 
              f"use_regex: {use_regex}, min_execution_count: {min_execution_count}, "
              f"max_execution_time_ms: {max_execution_time_ms}")
        
        cursor.execute(sql, params)
        
        # Fetch all matching queries
        columns = [column[0] for column in cursor.description]
        raw_results = []
        for row in cursor.fetchall():
            raw_results.append(dict(zip(columns, row)))
        
        print(f"Initial query returned {len(raw_results)} rows.")
        
        # If no results found, return a message
        if not raw_results:
            return {"message": f"No query patterns found matching '{search_term}'."}
        
        # Apply regex filtering if requested
        if use_regex:
            try:
                pattern = re.compile(search_term, re.IGNORECASE)
                raw_results = [r for r in raw_results if pattern.search(r['command'])]
                if not raw_results:
                    return {"message": f"No query patterns found matching regex pattern '{search_term}'."}
            except re.error as e:
                raise FastMCPError(
                    f"Invalid regex pattern: {str(e)}",
                ) from e
        
        # Process the results and group by patterns
        pattern_groups = defaultdict(list)
        for result in raw_results:
            # Normalize the query
            query_info = normalize_query(result['command'])
            
            # Generate a key for grouping similar patterns
            pattern_key = generate_pattern_key(query_info)
            
            # Add to the appropriate group
            pattern_groups[pattern_key].append({
                "original_query": result['command'],
                "normalized_info": query_info,
                "elapsed_time_ms": result['total_elapsed_time_ms'],
                "end_time": result['end_time'],
                "query_hash": result['query_hash']
            })
        
        # Process pattern groups and calculate statistics
        processed_patterns = []
        for pattern_key, instances in pattern_groups.items():
            # Skip patterns that haven't been executed enough times
            if len(instances) < min_execution_count:
                continue
            
            # Calculate statistics
            avg_time = sum(i['elapsed_time_ms'] for i in instances) / len(instances)
            latest_execution = max(instances, key=lambda i: i['end_time'])
            
            # Create pattern record
            pattern_record = {
                "pattern": instances[0]['normalized_info']['normalized_query'],
                "example": latest_execution['original_query'],
                "execution_stats": {
                    "count": len(instances),
                    "avg_execution_time_ms": avg_time,
                    "min_execution_time_ms": min(i['elapsed_time_ms'] for i in instances),
                    "max_execution_time_ms": max(i['elapsed_time_ms'] for i in instances)
                },
                "tables_referenced": instances[0]['normalized_info']['tables_referenced'],
                "columns_referenced": instances[0]['normalized_info']['columns_referenced'],
                "last_executed": latest_execution['end_time'].isoformat() if hasattr(latest_execution['end_time'], 'isoformat') else str(latest_execution['end_time'])
            }
            
            processed_patterns.append(pattern_record)
        
        # Sort by execution count (descending), then by average time (ascending)
        processed_patterns.sort(
            key=lambda p: (-p['execution_stats']['count'], p['execution_stats']['avg_execution_time_ms'])
        )
        
        # Limit the results
        if limit > 0:
            processed_patterns = processed_patterns[:limit]
        
        # If no patterns match the criteria, return a message
        if not processed_patterns:
            return {"message": f"No query patterns found that meet the criteria (min executions: {min_execution_count})."}
        
        return processed_patterns
        
    except pyodbc.Error as db_err:
        error_message = f"Database error occurred: {str(db_err)}"
        print(error_message)
        return {
            "error": "Database Execution Error: " + error_message,
        }
    except ConnectionError as conn_err:
        error_message = f"Database connection failed: {str(conn_err)}"
        print(error_message)
        return {
            "error": "Database Connection Error: " + error_message,
        }
    except Exception as e:
        error_message = f"An unexpected error occurred: {str(e)}"
        print(error_message)
        return {
            "error": "Unexpected Server Error: " + error_message,
        }
    finally:
        if cnxn:
            print("Closing database connection.")
            cnxn.close()
