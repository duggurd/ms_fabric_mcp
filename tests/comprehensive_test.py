from query_normalizer import normalize_query
import json

# A variety of SQL query patterns to test
test_queries = [
    # Basic SELECT with WHERE
    "SELECT TOP 5 command FROM queryinsights.exec_requests_history WHERE status = 'Succeeded'",
    
    # SELECT with multiple columns, schema, and LIKE
    "SELECT TABLE_CATALOG, TABLE_SCHEMA, TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME LIKE '%query%'",
    
    # Simple SELECT with multiple conditions
    "SELECT * FROM orders WHERE customer_id = 12345 AND order_date > '2023-01-01'",
    
    # SELECT with aggregates, GROUP BY and IN clause
    "SELECT Count(*) as count, Avg(price) as avg_price FROM Products WHERE category_id IN (1, 2, 3) GROUP BY category_id",
    
    # JOIN statement
    "SELECT o.order_id, c.customer_name FROM orders o JOIN customers c ON o.customer_id = c.id WHERE o.status = 'completed'",
    
    # Complex query with subquery and ORDER BY
    "SELECT department, AVG(salary) as avg_sal FROM employees WHERE age > 30 AND department IN (SELECT dept_id FROM departments WHERE active = 1) GROUP BY department ORDER BY avg_sal DESC",
    
    # INSERT statement
    "INSERT INTO logs (timestamp, message, level) VALUES ('2023-05-18 10:15:30', 'Server started', 'INFO')",
    
    # UPDATE statement
    "UPDATE products SET price = price * 1.1 WHERE category = 'electronics' AND last_updated < '2023-01-01'",
    
    # DELETE statement
    "DELETE FROM temporary_logs WHERE created_date < DATEADD(day, -30, GETDATE())"
]

# Process each query and print the results
for i, query in enumerate(test_queries):
    print(f"\nTest Query {i+1}:")
    print(f"Original: {query}")
    
    try:
        result = normalize_query(query)
        print(f"Normalized: {result['normalized_query']}")
        
        print("Tables referenced:")
        for table in result['tables_referenced']:
            print(f"  - {table}")
            
        print("Columns referenced:")
        for column in result['columns_referenced']:
            print(f"  - {column}")
    except Exception as e:
        print(f"Error: {str(e)}")
    
    print("-" * 80) 