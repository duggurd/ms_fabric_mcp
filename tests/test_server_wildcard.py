import asyncio
import os
import sys

# Add the project root directory to Python path

from server import search_tables, search_columns_by_table, search_tables_by_column

async def run_tests():
    # Test 1: search_tables with wildcard
    print("\n=== Test 1: search_tables with wildcard ===")
    print("Testing partial match for 'delta' (should find multiple sys.managed_delta_* tables):")
    result = await search_tables(table_name="delta", use_wildcard=True)
    print("Wildcard result:", result)

    # Test 2: search_tables exact match
    print("\n=== Test 2: search_tables exact match ===")
    print("Testing exact match for 'managed_delta_tables' (should find only one table):")
    result = await search_tables(table_name="managed_delta_tables", use_wildcard=False)
    print("Exact match result:", result)

    # Test 3: search_tables with schema
    print("\n=== Test 3: search_tables with schema ===")
    print("Testing in 'queryinsights' schema for 'exec' tables:")
    result = await search_tables(table_name="exec", schema_name="queryinsights", use_wildcard=True)
    print("Schema-specific result:", result)

    # Test 4: search_columns_by_table with wildcard
    print("\n=== Test 4: search_columns_by_table with wildcard ===")
    print("Testing partial match for 'exec' (should find columns from exec_* tables):")
    result = await search_columns_by_table(table_name="exec", use_wildcard=True)
    print("Wildcard result:", result)

    # Test 5: search_columns_by_table exact match
    print("\n=== Test 5: search_columns_by_table exact match ===")
    print("Testing exact match for 'exec_requests_history':")
    result = await search_columns_by_table(table_name="exec_requests_history", use_wildcard=False)
    print("Exact match result:", result)

    # Test 6: search_tables_by_column with wildcard
    print("\n=== Test 6: search_tables_by_column with wildcard ===")
    print("Testing partial match for column name 'time' (should find multiple *_time* columns):")
    result = await search_tables_by_column(column_name="time", use_wildcard=True)
    print("Wildcard result:", result)

    # Test 7: search_tables_by_column exact match
    print("\n=== Test 7: search_tables_by_column exact match ===")
    print("Testing exact match for column 'end_time':")
    result = await search_tables_by_column(column_name="end_time", use_wildcard=False)
    print("Exact match result:", result)

    # Test 8: Negative test cases
    print("\n=== Test 8: Negative test cases ===")
    print("Testing non-existent table exact match:")
    result = await search_tables(table_name="nonexistent_table", use_wildcard=False)
    print("Non-existent table result:", result)

    print("\nTesting non-existent column exact match:")
    result = await search_tables_by_column(column_name="nonexistent_column", use_wildcard=False)
    print("Non-existent column result:", result)

if __name__ == "__main__":
    asyncio.run(run_tests()) 