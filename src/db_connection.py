import pyodbc
import os
import struct
from azure.identity import AzureCliCredential

# Constants for AAD authentication
SQL_SERVER_SCOPE = "https://database.windows.net/.default"
# SQL_COPT_SS_ACCESS_TOKEN is a constant used by pyodbc to set the access token
# It's defined in msodbcsql.h, usually value is 1256
SQL_COPT_SS_ACCESS_TOKEN = 1256

# Module-level variable for connection reuse
_cached_connection = None

def get_aad_token():
    """Obtains an AAD access token for SQL Server."""
    try:
        token = AzureCliCredential().get_token(SQL_SERVER_SCOPE).token
        return token
    except Exception as e:
        # Log or handle specific exceptions from azure-identity if needed
        print(f"Error obtaining AAD token: {e}")
        raise ConnectionError(f"Failed to obtain AAD token: {e}") from e

def get_db_connection():
    """Establishes a pyodbc connection to SQL Server using AAD token authentication. Reuses the connection within a session."""
    global _cached_connection
    if _cached_connection is not None:
        try:
            # Check if the connection is still open
            _cached_connection.cursor().execute("SELECT 1")
            return _cached_connection
        except Exception:
            # Connection is closed or invalid, reset it
            _cached_connection = None

    server_name = os.getenv("SQL_SERVER_NAME")
    database_name = os.getenv("SQL_DATABASE_NAME")
    odbc_driver = os.getenv("ODBC_DRIVER", "{ODBC Driver 18 for SQL Server}") # Default to Driver 18

    if not server_name or not database_name:
        raise ConnectionError("SQL_SERVER_NAME and/or SQL_DATABASE_NAME environment variables are not set.")

    try:
        access_token = get_aad_token()
        token_bytes = access_token.encode("utf-16-le")
        token_struct = struct.pack(f"<i{len(token_bytes)}s", len(token_bytes), token_bytes)
        conn_str = f"DRIVER={odbc_driver};SERVER={server_name};DATABASE={database_name};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=2;"
        _cached_connection = pyodbc.connect(conn_str, attrs_before={SQL_COPT_SS_ACCESS_TOKEN: token_struct})
        return _cached_connection
    except pyodbc.Error as db_err:
        print(f"PyODBC Error: {db_err}")
        raise ConnectionError(f"Database connection failed: {db_err}") from db_err
    except ConnectionError: # To re-raise ConnectionError from get_aad_token
        raise
    except Exception as e:
        print(f"Error establishing database connection: {e}")
        raise ConnectionError(f"An unexpected error occurred during database connection: {e}") from e

def close_db_connection():
    """Closes the cached database connection, if it exists."""
    global _cached_connection
    if _cached_connection is not None:
        try:
            _cached_connection.close()
        except Exception:
            pass
        _cached_connection = None 