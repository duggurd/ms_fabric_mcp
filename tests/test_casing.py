from query_normalizer import normalize_query

# Test queries with mixed casing
test_queries = [
    # Test 1: SQL keywords (TOP) and mixed-case identifiers
    "SELECT TOP 5 command FROM queryinsights.exec_requests_history WHERE status = 'Succeeded'",
    
    # Test 2: Mixed-case identifiers in schema.table format
    "SELECT TABLE_CATALOG, TABLE_SCHEMA, TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME LIKE '%query%'",
    
    # Test 3: Mixed-case function names
    "SELECT Count(*) as count, Avg(price) as avg_price FROM Products WHERE category_id IN (1, 2, 3) GROUP BY category_id"
]

# Test each query and print the results
for i, query in enumerate(test_queries):
    print(f"\nTest {i+1}: {query}")
    result = normalize_query(query)
    print(f"Normalized: {result['normalized_query']}")
    print(f"Tables referenced: {result['tables_referenced']}")
    print(f"Columns referenced: {result['columns_referenced']}")
    print("-" * 80) 