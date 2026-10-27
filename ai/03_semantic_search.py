import json
import pyodbc
from sentence_transformers import SentenceTransformer
from db import get_connection

def semantic_search(query_text, top_k=3):
    """
    Calcula el embedding de la pregunta del usuario y ejecuta una búsqueda
    por distancia coseno directamente en SQL Server 2025.
    """
    model = SentenceTransformer("all-MiniLM-L6-v2")
    query_vector = model.encode(query_text).tolist()
    query_vector_json = json.dumps(query_vector)

    conn = get_connection()
    cursor = conn.cursor()

    # Consulta con nombres reales: d.nombre, f.fecha_jornada, f.hora_entrada
    query_sql = """
        SELECT TOP (?)
            i.incidencia_id,
            e.nombre + ' ' + e.apellidos AS empleado,
            d.nombre AS departamento,
            CONVERT(VARCHAR(10), f.fecha_jornada, 120) AS fecha,
            CONVERT(VARCHAR(8), f.hora_entrada, 108) AS hora_entrada,
            i.texto_justificacion,
            VECTOR_DISTANCE('cosine', i.embedding_justificacion, CAST(CAST(? AS NVARCHAR(MAX)) AS VECTOR(384))) AS distancia
        FROM dbo.IncidenciasJustificaciones i
        INNER JOIN dbo.Fichajes f ON i.fichaje_id = f.fichaje_id
        INNER JOIN dbo.Empleados e ON f.empleado_id = e.empleado_id
        INNER JOIN dbo.Departamentos d ON e.departamento_id = d.departamento_id
        WHERE i.embedding_justificacion IS NOT NULL
        ORDER BY distancia ASC;
    """

    try:
        cursor.execute(query_sql, (top_k, query_vector_json))
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

def main():
    print("=" * 70)
    print("  BUSCADOR SEMÁNTICO NATIVO - SQL SERVER 2025 (DP-800)")
    print("=" * 70)
    print("Introduce una consulta en lenguaje natural (escribe 'salir' para terminar).\n")

    while True:
        prompt = input("Consulta semántica > ").strip()
        if prompt.lower() in ("salir", "exit", "quit"):
            print("Cerrando motor de búsqueda semántica.")
            break

        if not prompt:
            continue

        print("\n[*] Vectorizando consulta y calculando distancia coseno en BD...")
        try:
            filas = semantic_search(prompt, top_k=3)
            if not filas:
                print("[-] No se encontraron registros vectorizados en la base de datos.\n")
                continue

            print(f"\nResultados más afines (Top {len(filas)}):")
            for idx, row in enumerate(filas, start=1):
                inc_id, empleado, dpto, fecha, hora, justificacion, distancia = row
                similitud = (1 - distancia) * 100
                print(f"\n  [{idx}] Empleado: {empleado} | Departamento: {dpto}")
                print(f"      Jornada: {fecha} a las {hora}")
                print(f"      Justificación: \"{justificacion}\"")
                print(f"      Distancia Coseno: {distancia:.4f} (Afinidad: {similitud:.1f}%)")
            print("-" * 70 + "\n")
        except Exception as e:
            print(f"[!] Error durante la ejecución: {e}\n")

if __name__ == "__main__":
    main()