import os
import sys

# server.py is in the same directory (src), so use a relative import.
from server import app 

def cli_start():
    print("Starting SQL Server Read-Only Query MCP Server (from src/main.py)...")

    # Check for required environment variables before starting
    required_env_vars = ["SQL_SERVER_NAME", "SQL_DATABASE_NAME"]

    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    if missing_vars:
        print(f"\nError: Missing required environment variables: {', '.join(missing_vars)}")
        print("Please set the following environment variables before running the server:")
        for var in required_env_vars:
            print(f"  - {var}")
        sys.exit(1)
    
    print("Required environment variables found.")
    print(f"  SQL_SERVER_NAME: {os.getenv('SQL_SERVER_NAME')}")
    print(f"  SQL_DATABASE_NAME: {os.getenv('SQL_DATABASE_NAME')}")
    print(f"  ODBC_DRIVER: {os.getenv('ODBC_DRIVER', '{ODBC Driver 18 for SQL Server}')}")

    host = os.getenv("MCP_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_PORT", "8000"))

    print(f"\nAttempting to run server on {host}:{port}")
    print("Make sure you have performed 'az login' and have the necessary ODBC driver installed.")
    print("-------------------------------------------------------------------------------------")

    try:
        app.run()
        # uvicorn.run(app, host=host, port=port)
    except Exception as e:
        print(f"\nFailed to start Uvicorn server: {e}")
        print("Ensure Uvicorn is installed (it should be a dependency of FastMCP or install it: pip install uvicorn[standard])")
        sys.exit(1)

if __name__ == "__main__":
    # This allows running python -m src.main directly if needed,
    # or if src/main.py is executed as a script.

    cli_start() 