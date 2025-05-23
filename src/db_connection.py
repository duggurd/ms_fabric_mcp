import pyodbc
import os
import struct
from azure.identity import AzureCliCredential

# Constants for AAD authentication
SQL_SERVER_SCOPE = "https://database.windows.net/.default"
# SQL_COPT_SS_ACCESS_TOKEN is a constant used by pyodbc to set the access token
# It's defined in msodbcsql.h, usually value is 1256
SQL_COPT_SS_ACCESS_TOKEN = 1256

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
    """Establishes a pyodbc connection to SQL Server using AAD token authentication."""
    server_name = os.getenv("SQL_SERVER_NAME")
    database_name = os.getenv("SQL_DATABASE_NAME")
    odbc_driver = os.getenv("ODBC_DRIVER", "{ODBC Driver 18 for SQL Server}") # Default to Driver 18

    if not server_name or not database_name:
        raise ConnectionError("SQL_SERVER_NAME and/or SQL_DATABASE_NAME environment variables are not set.")

    try:
        access_token = get_aad_token()
        token_bytes = access_token.encode("utf-16-le")
        token_struct = struct.pack(f"<i{len(token_bytes)}s", len(token_bytes), token_bytes)
        
        # The struct packing should match what the ODBC driver expects for the token attribute.
        # For SQL_COPT_SS_ACCESS_TOKEN, it's typically a pointer to a struct containing token length and token bytes.
        # However, pyodbc handles this by expecting the raw token bytes for certain auth modes, or a specific struct for others.
        # The common pattern for SQL_COPT_SS_ACCESS_TOKEN is to pass a struct containing the length of the token and the token itself.
        # The format is: int length, byte array token.
        # struct.pack("=i" + str(len(token_bytes)) + "s", len(token_bytes), token_bytes)
        # Using "=i" for standard size integer (4 bytes), followed by the bytes of the token.
        conn_str = f"DRIVER={odbc_driver};SERVER={server_name};DATABASE={database_name};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=2;"

        # SQL_COPT_SS_ACCESS_TOKEN tells the driver that we are providing an access token
        cnxn = pyodbc.connect(conn_str, attrs_before={SQL_COPT_SS_ACCESS_TOKEN: token_struct})
        return cnxn
    except pyodbc.Error as db_err:
        print(f"PyODBC Error: {db_err}")
        # sqlstate = db_err.args[0]
        # print(f"SQLSTATE: {sqlstate}")
        # print(f"Message: {db_err.args[1]}")
        raise ConnectionError(f"Database connection failed: {db_err}") from db_err
    except ConnectionError: # To re-raise ConnectionError from get_aad_token
        raise
    except Exception as e:
        print(f"Error establishing database connection: {e}")
        raise ConnectionError(f"An unexpected error occurred during database connection: {e}") from e 