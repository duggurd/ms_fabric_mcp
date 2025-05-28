"""
Module for normalizing SQL queries by replacing literals with placeholders 
and extracting query metadata.
"""
import re
import sqlparse
from typing import Dict, List, Set, Tuple, Optional, Union

# Regular expressions for identifying literals
INTEGER_PATTERN = r'\b\d+\b'
FLOAT_PATTERN = r'\b\d+\.\d+\b'
STRING_PATTERN = r"'[^']*'"
DATE_PATTERN = r"'\d{4}-\d{2}-\d{2}'"
DATETIME_PATTERN = r"'\d{4}-\d{2}-\d{2}(\s+|T)\d{2}:\d{2}:\d{2}(\.\d+)?'"

# Tables and columns extraction patterns
TABLE_NAME_PATTERN = r'\b(FROM|JOIN)\s+([a-zA-Z0-9_\.]+)'
COLUMN_PATTERN = r'\b([a-zA-Z0-9_\.]+)\s*(=|<|>|<=|>=|<>|LIKE|IN|BETWEEN)'

def normalize_query(query: str) -> Dict[str, Union[str, List[str]]]:
    """
    Normalize an SQL query by replacing literals with placeholders
    and extract query metadata.
    
    Args:
        query: The SQL query to normalize
    
    Returns:
        A dictionary containing:
        - normalized_query: The query with literals replaced by placeholders
        - tables_referenced: List of tables referenced in the query
        - columns_referenced: List of columns used in conditions
    """
    if not query or not isinstance(query, str):
        return {
            "normalized_query": "",
            "tables_referenced": [],
            "columns_referenced": []
        }
    
    # Store the original query for reference
    original_query = query
    
    # Clean and format the query for extraction purposes
    query = _clean_query(query)
    
    # Extract tables and columns before normalization
    tables = _extract_tables(query)
    columns = _extract_columns(query)
    
    # For the normalized query, we need to preserve identifier casing
    # but still replace literals with placeholders and format consistently
    normalized = _normalize_with_preserved_case(original_query)
    
    return {
        "normalized_query": normalized,
        "tables_referenced": sorted(list(tables)),
        "columns_referenced": sorted(list(columns))
    }

def _clean_query(query: str) -> str:
    """Clean and format the query for better parsing."""
    # Preserve comments by temporarily replacing them
    comment_pattern = r'--.*?$'
    comments = []
    def save_comment(match):
        comments.append(match.group(0))
        return f"__COMMENT_{len(comments)-1}__"
    
    # Save comments
    query = re.sub(comment_pattern, save_comment, query, flags=re.MULTILINE)
    
    # Format the query
    query = sqlparse.format(
        query,
        keyword_case='upper',
        identifier_case=None,  # Don't change identifier case
        strip_comments=False,  # Don't strip comments as we're handling them
        reindent=True
    )
    
    # Remove newlines for simpler regex processing
    query = re.sub(r'\s+', ' ', query)
    
    # Restore comments
    for i, comment in enumerate(comments):
        query = query.replace(f"__COMMENT_{i}__", comment)
    
    return query.strip()

def _normalize_with_preserved_case(query: str) -> str:
    """Normalize query while preserving the original case of identifiers."""
    # Common SQL functions that should be uppercase
    sql_functions = {
        'count', 'sum', 'avg', 'min', 'max', 'coalesce', 'dateadd', 
        'datediff', 'convert', 'cast', 'isnull', 'getdate'
    }
    
    # SQL keywords that should always be uppercase
    sql_keywords = {
        'select', 'from', 'where', 'group', 'order', 'having', 'limit',
        'union', 'join', 'inner', 'outer', 'left', 'right', 'full',
        'on', 'by', 'top', 'distinct', 'into', 'values', 'as', 'set',
        'insert', 'update', 'delete', 'create', 'alter', 'drop', 'and', 'or'
    }
    
    # Process the query using regular expressions to handle specific patterns
    # Handle COUNT, AVG, and other function calls
    for func in sql_functions:
        # Match function pattern (case-insensitive)
        pattern = re.compile(r'\b' + func + r'\s*\(', re.IGNORECASE)
        query = pattern.sub(func.upper() + '(', query)
    
    # Handle SQL keywords
    for keyword in sql_keywords:
        # Match keyword pattern (case-insensitive) with word boundaries
        pattern = re.compile(r'\b' + keyword + r'\b', re.IGNORECASE)
        query = pattern.sub(keyword.upper(), query)
    
    # Handle TOP keyword specifically to ensure it's always uppercase
    query = re.sub(r'\bTOP\b', 'TOP', query, flags=re.IGNORECASE)
    
    # Replace literals with placeholders
    query = _replace_literals(query)
    
    # Remove excessive whitespace but preserve structure
    query = re.sub(r'\s+', ' ', query).strip()
    
    return query

def _replace_literals(query: str) -> str:
    """Replace literals with appropriate placeholders."""
    # Replace strings first (to avoid matching dates as integers)
    query = re.sub(STRING_PATTERN, "?", query)
    query = re.sub(DATE_PATTERN, "?", query)
    query = re.sub(DATETIME_PATTERN, "?", query)
    
    # Replace numbers
    query = re.sub(FLOAT_PATTERN, "?", query)
    query = re.sub(INTEGER_PATTERN, "?", query)
    
    # Replace IN clauses like "IN (1, 2, 3)" with "IN (?)"
    query = re.sub(r'IN\s*\([^)]*\)', 'IN (?)', query)
    
    return query

def _extract_tables(query: str) -> Set[str]:
    """Extract table names from the query."""
    tables = set()
    matches = re.finditer(TABLE_NAME_PATTERN, query, re.IGNORECASE)
    
    for match in matches:
        table_name = match.group(2).strip()
        # Handle schema.table notation
        if '.' in table_name:
            schema, table = table_name.split('.', 1)
            tables.add(table)
        else:
            tables.add(table_name)
    
    return tables

def _extract_columns(query: str) -> Set[str]:
    """Extract column names used in conditions and SELECT clause."""
    columns = set()
    
    # Common SQL keywords that shouldn't be treated as columns
    sql_keywords = {
        'select', 'from', 'where', 'group', 'order', 'having', 'limit',
        'union', 'join', 'inner', 'outer', 'left', 'right', 'full',
        'on', 'by', 'top', 'distinct', 'into', 'values', 'as', 'query',
        'and', 'or', 'not', 'is', 'null', 'like'
    }
    
    # Common SQL functions that shouldn't be treated as columns
    sql_functions = {
        'count', 'sum', 'avg', 'min', 'max', 'coalesce', 'dateadd', 
        'datediff', 'convert', 'cast', 'isnull', 'getdate'
    }
    
    try:
        # Extract columns from WHERE conditions
        where_pattern = r'WHERE\s+([^=<>]+)(?:=|<|>|<=|>=|<>|LIKE|IN|BETWEEN)'
        where_matches = re.finditer(where_pattern, query, re.IGNORECASE)
        
        for match in where_matches:
            condition = match.group(1).strip()
            
            # Skip SQL keywords and functions
            if condition.lower() in sql_keywords or condition.lower() in sql_functions:
                continue
                
            # Skip numeric literals
            if condition.isdigit():
                continue
                
            # Handle AND/OR in conditions
            if ' AND ' in condition.upper() or ' OR ' in condition.upper():
                continue
                
            # Handle table.column notation
            if '.' in condition:
                table, col = condition.split('.', 1)
                if col.lower() not in sql_keywords and col.lower() not in sql_functions:
                    columns.add(col)
            else:
                if condition.lower() not in sql_keywords and condition.lower() not in sql_functions:
                    columns.add(condition)
        
        # Extract columns from SELECT clause
        select_pattern = r'SELECT\s+(?:TOP\s+\d+\s+)?(.+?)\s+FROM'
        select_match = re.search(select_pattern, query, re.IGNORECASE | re.DOTALL)
        
        if select_match:
            select_columns = select_match.group(1).strip()
            
            # Skip SELECT * cases
            if select_columns == '*':
                pass
            else:
                # Handle column list
                in_parentheses = 0
                current_column = ''
                column_parts = []
                
                for char in select_columns:
                    if char == '(':
                        in_parentheses += 1
                        current_column += char
                    elif char == ')':
                        in_parentheses -= 1
                        current_column += char
                    elif char == ',' and in_parentheses == 0:
                        column_parts.append(current_column.strip())
                        current_column = ''
                    else:
                        current_column += char
                
                if current_column:
                    column_parts.append(current_column.strip())
                
                # Process each column expression
                for part in column_parts:
                    # Skip functions like COUNT(*), AVG(column)
                    if any(func.lower() + '(' in part.lower() for func in sql_functions):
                        continue
                        
                    # Handle column aliases
                    if ' AS ' in part.upper():
                        part = part.split(' AS ')[0].strip()
                    
                    # Skip expressions with operations
                    if any(op in part for op in ['+', '-', '*', '/']):
                        continue
                        
                    # Handle table.column notation
                    if '.' in part:
                        table, col = part.split('.', 1)
                        if col.lower() not in sql_keywords and col.lower() not in sql_functions:
                            columns.add(col)
                    else:
                        if part.lower() not in sql_keywords and part.lower() not in sql_functions:
                            columns.add(part)
    
    except Exception:
        # If regex fails, fall back to basic extraction
        pass
    
    return columns

def generate_pattern_key(query_info: Dict[str, Union[str, List[str]]]) -> str:
    """
    Generate a key for grouping similar query patterns.
    
    Args:
        query_info: The normalized query information
        
    Returns:
        A string key that can be used to group similar queries
    """
    norm_query = query_info.get("normalized_query", "")
    
    # Remove all placeholders to focus on structure
    structure_only = re.sub(r'\?', "", norm_query)
    
    # Further simplify by removing spaces
    structure_only = re.sub(r'\s+', " ", structure_only).strip()
    
    # Use a hash of the structure as the key
    return f"pattern:{hash(structure_only)}" 