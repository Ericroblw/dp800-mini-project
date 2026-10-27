import os
import pyodbc
from dotenv import load_dotenv

# Carga las variables definidas en el archivo .env
load_dotenv()

def get_connection():
    """
    Construye dinámicamente la cadena ODBC según el método de autenticación configurado.
    Soporta Windows Authentication y SQL Server Authentication sin modificar código.
    """
    server = os.getenv("DB_SERVER", "localhost")
    database = os.getenv("DB_NAME", "ControlAccesosIA")
    trusted_conn = os.getenv("DB_TRUSTED_CONNECTION", "false").lower() in ("true", "1", "yes")

    if trusted_conn:
        # Autenticación integrada de Windows
        conn_str = (
            "DRIVER={ODBC Driver 18 for SQL Server};"
            f"SERVER={server};"
            f"DATABASE={database};"
            "Trusted_Connection=yes;"
            "TrustServerCertificate=yes;"
        )
    else:
        # Autenticación nativa de SQL Server (ej. usuario sa)
        user = os.getenv("DB_USER")
        password = os.getenv("DB_PASSWORD")
        conn_str = (
            "DRIVER={ODBC Driver 18 for SQL Server};"
            f"SERVER={server};"
            f"DATABASE={database};"
            f"UID={user};"
            f"PWD={password};"
            "TrustServerCertificate=yes;"
        )

    return pyodbc.connect(conn_str)