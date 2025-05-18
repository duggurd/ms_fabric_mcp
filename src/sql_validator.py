def is_readonly_query(sql_query: str) -> bool:
    """Checks if the given SQL query is a read-only SELECT statement (basic check)."""
    if not sql_query:
        return False
    # Normalize by stripping whitespace and converting the first part to uppercase
    normalized_query = sql_query.strip()
    # Check if the query starts with SELECT (case-insensitive)
    if normalized_query.upper().startswith("SELECT"):
        return True
    return False 