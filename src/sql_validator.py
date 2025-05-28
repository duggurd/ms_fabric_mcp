def is_readonly_query(sql_query: str) -> bool:
    """Checks if the given SQL query is a read-only SELECT statement (basic check)."""
    if not sql_query:
        return False

    first_significant_line = ""
    for line in sql_query.strip().splitlines():
        stripped_line = line.strip()
        if not stripped_line.startswith("--") and stripped_line:
            first_significant_line = stripped_line
            break

    if not first_significant_line:
        # Query was empty or only comments
        return False

    # Check if the first significant part of the query starts with SELECT or WITH (case-insensitive)
    if first_significant_line.upper().startswith("SELECT") or \
       first_significant_line.upper().startswith("WITH"):
        return True
    return False 