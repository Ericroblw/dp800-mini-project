import json
import pyodbc
from sentence_transformers import SentenceTransformer

def buscar_incidencias_similares(consulta_usuario: str, top_k: int = 3):
    print(f"\n--- BÚSQUEDA SEMÁNTICA VECTORIAL (BLOQUE F) ---")
    print(f"Pregunta del auditor: '{consulta_usuario}'")

    # 1. Cargar modelo y calcular vector de la pregunta
    model = SentenceTransformer("all-MiniLM-L6-v2")
    query_vector = model.encode(consulta_usuario)
    query_vector_json = json.dumps(query_vector.tolist())

    # 2. Conectar a SQL Server 2025
    conn_str = (
        "DRIVER={ODBC Driver 18 for SQL Server};"
        "SERVER=localhost;"
        "DATABASE=ControlAccesosIA;"
        "Trusted_Connection=yes;"
        "TrustServerCertificate=yes;"
    )

    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()

    try:
        # 3. Consulta vectorial directa a la tabla IncidenciasJustificaciones
        sql_query = """
            DECLARE @vector_consulta VECTOR(384) = CAST(CAST(? AS NVARCHAR(MAX)) AS VECTOR(384));

            SELECT TOP (?)
                incidencia_id,
                fichaje_id,
                texto_justificacion,
                VECTOR_DISTANCE('cosine', embedding_justificacion, @vector_consulta) AS distancia_coseno
            FROM dbo.IncidenciasJustificaciones
            ORDER BY distancia_coseno ASC;
        """

        cursor.execute(sql_query, (query_vector_json, top_k))
        resultados = cursor.fetchall()

        print(f"\nTop {top_k} incidencias más relevantes semánticamente:\n")
        for row in resultados:
            print(f"Incidencia ID: {row.incidencia_id} | Fichaje ID: {row.fichaje_id}")
            print(f"Distancia Coseno: {row.distancia_coseno:.4f} (más cercano a 0 = mayor similitud)")
            print(f"Justificación: {row.texto_justificacion}\n" + "-" * 70)

    except Exception as e:
        print(f"[ERROR] Fallo en la búsqueda semántica: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    buscar_incidencias_similares("problemas con el transporte público o trenes", top_k=3)