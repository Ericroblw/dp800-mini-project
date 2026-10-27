import json
import pyodbc
from sentence_transformers import SentenceTransformer
from db import get_connection

def run_embedding_pipeline():
    # 1. Carga del modelo denso de embeddings (384 dimensiones)
    model_name = "all-MiniLM-L6-v2"
    print(f"[*] Cargando modelo de embeddings ({model_name})...")
    model = SentenceTransformer(model_name)

    # 2. Conexión a la base de datos mediante el conector modular
    print("[*] Conectando a SQL Server...")
    try:
        conn = get_connection()
        cursor = conn.cursor()
    except Exception as e:
        print(f"[!] Error de conexión a la base de datos: {e}")
        return

    try:
        # 3. Extracción: Obtener solo incidencias pendientes de vectorizar
        query_select = """
            SELECT incidencia_id, texto_justificacion
            FROM dbo.IncidenciasJustificaciones
            WHERE embedding_justificacion IS NULL;
        """
        cursor.execute(query_select)
        registros = cursor.fetchall()

        if not registros:
            print("[+] No hay incidencias pendientes de vectorizar. Todo el dataset está sincronizado.")
            return

        print(f"[*] Registros detectados para procesar: {len(registros)}")

        # 4. Transformación y Carga: Cálculo de embeddings e inyección T-SQL
        query_update = """
            UPDATE dbo.IncidenciasJustificaciones
            SET embedding_justificacion = CAST(CAST(? AS NVARCHAR(MAX)) AS VECTOR(384))
            WHERE incidencia_id = ?;
        """

        for reg in registros:
            incidencia_id = reg.incidencia_id
            texto = reg.texto_justificacion

            # Inferencia: generación del vector denso de 384 floats
            vector = model.encode(texto).tolist()
            vector_json = json.dumps(vector)

            # Persistencia con casteo doble explícito
            cursor.execute(query_update, (vector_json, incidencia_id))
            print(f"  [✓] Incidencia ID {incidencia_id} vectorizada y actualizada.")

        # Confirmación transaccional en el motor
        conn.commit()
        print("\n[+] Proceso ETL finalizado con éxito. Transacción consolidada (COMMIT).")

    except pyodbc.Error as db_err:
        conn.rollback()
        print(f"[!] Error en la transacción de SQL Server (Rollback aplicado): {db_err}")
    except Exception as ex:
        conn.rollback()
        print(f"[!] Error inesperado durante el pipeline: {ex}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    run_embedding_pipeline()