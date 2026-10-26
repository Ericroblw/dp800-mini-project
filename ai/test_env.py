import pyodbc
from sentence_transformers import SentenceTransformer

print("1. Probando carga del modelo de embeddings en local...")
# Descarga/carga el modelo compacto en CPU (384 dimensiones)
model = SentenceTransformer("all-MiniLM-L6-v2")
vector_prueba = model.encode("Prueba de vectorización de justificación")
print(f"-> Modelo cargado con éxito. Dimensión del vector generado: {len(vector_prueba)}")

print("\n2. Probando conexión ODBC con SQL Server local...")
# Cadena de conexión usando autenticación de Windows y cifrado compatible
conn_str = (
    "DRIVER={ODBC Driver 18 for SQL Server};"
    "SERVER=localhost;"
    "DATABASE=ControlAccesosIA;"
    "Trusted_Connection=yes;"
    "TrustServerCertificate=yes;"
)

try:
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    cursor.execute("SELECT @@VERSION AS Version, DB_NAME() AS BDActual;")
    row = cursor.fetchone()
    print(f"-> Conexión exitosa a la base de datos: {row.BDActual}")
    conn.close()
except Exception as e:
    print(f"-> Error en la conexión ODBC: {e}")