import json
import pyodbc
from sentence_transformers import SentenceTransformer

def run_embedding_pipeline():
    print("--- INICIANDO PIPELINE ETL DE EMBEDDINGS (BLOQUE E) ---")

    # 1. Cargar modelo de embeddings en memoria local
    print("Cargando modelo local all-MiniLM-L6-v2...")
    model = SentenceTransformer("all-MiniLM-L6-v2")

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
        # 3. Extraer incidencias pendientes de vectorización
        cursor.execute("""
            SELECT incidencia_id, texto_justificacion
            FROM dbo.IncidenciasJustificaciones
            WHERE embedding_justificacion IS NULL;
        """)
        registros = cursor.fetchall()

        if not registros:
            print("No hay registros pendientes de vectorizar. Todo el dataset está al día.")
            return

        print(f"Se encontraron {len(registros)} registros para procesar.")

        # 4. Transformar y Cargar (Bucle de inferencia y actualización)
        for row in registros:
            incidencia_id = row.incidencia_id
            texto = row.texto_justificacion

            print(f"Procesando Incidencia ID {incidencia_id}: '{texto[:50]}...'")

            # Inferencia del modelo local
            embedding = model.encode(texto)
            embedding_json = json.dumps(embedding.tolist())

            # Actualización en base de datos con casteo explícito a VECTOR(384)
            cursor.execute("""
                UPDATE dbo.IncidenciasJustificaciones
                SET embedding_justificacion = CAST(CAST(? AS NVARCHAR(MAX)) AS VECTOR(384))
                WHERE incidencia_id = ?;
            """, (embedding_json, incidencia_id))

        # Confirmar la transacción
        conn.commit()
        print("\n-> ¡Pipeline completado con éxito! Registros actualizados en SQL Server.")

    except Exception as e:
        conn.rollback()
        print(f"\n[ERROR] El pipeline falló y se aplicó rollback: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    run_embedding_pipeline()