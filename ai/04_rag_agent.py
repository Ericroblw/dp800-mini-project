import json
import pyodbc
from sentence_transformers import SentenceTransformer
import ollama

def ejecutar_consulta_rag(pregunta_usuario: str, model_embeddings, conn, top_k: int = 2):
    # 1. RETRIEVAL: Generación de embedding
    vector_pregunta = model_embeddings.encode(pregunta_usuario)
    vector_json = json.dumps(vector_pregunta.tolist())

    cursor = conn.cursor()
    try:
        # 2. RETRIEVAL: Búsqueda vectorial con metadata relacional
        sql_query = """
            DECLARE @vector_consulta VECTOR(384) = CAST(CAST(? AS NVARCHAR(MAX)) AS VECTOR(384));

            SELECT TOP (?)
                i.incidencia_id,
                e.empleado_id,
                e.nombre + ' ' + e.apellidos AS nombre_completo,
                d.nombre AS departamento,
                CONVERT(VARCHAR(10), f.fecha_jornada, 120) AS fecha_jornada,
                CONVERT(VARCHAR(8), f.hora_entrada, 108) AS hora_entrada,
                i.texto_justificacion,
                VECTOR_DISTANCE('cosine', i.embedding_justificacion, @vector_consulta) AS distancia_coseno
            FROM dbo.IncidenciasJustificaciones i
            INNER JOIN dbo.Fichajes f ON i.fichaje_id = f.fichaje_id
            INNER JOIN dbo.Empleados e ON f.empleado_id = e.empleado_id
            INNER JOIN dbo.Departamentos d ON e.departamento_id = d.departamento_id
            ORDER BY distancia_coseno ASC;
        """
        cursor.execute(sql_query, (vector_json, top_k))
        filas = cursor.fetchall()

        if not filas:
            print("\n[RAG] No se recuperaron registros relevantes en la base de datos.")
            return

        # 3. AUGMENTATION: Ensamblado del contexto factual
        bloques_contexto = []
        for row in filas:
            bloques_contexto.append(
                f"- Registro #{row.incidencia_id}:\n"
                f"  * Empleado: {row.nombre_completo} (ID: {row.empleado_id})\n"
                f"  * Departamento: {row.departamento}\n"
                f"  * Fecha: {row.fecha_jornada} | Hora Entrada: {row.hora_entrada}\n"
                f"  * Justificación: \"{row.texto_justificacion}\"\n"
                f"  * Distancia Coseno: {row.distancia_coseno:.4f}"
            )
        contexto_textual = "\n\n".join(bloques_contexto)

        # 4. GENERATION: Inferencia con LLM local
        system_prompt = (
            "Eres un auditor senior de Recursos Humanos y Seguridad Física corporativa. "
            "Responde a la consulta basándote ÚNICAMENTE en la información explícita del CONTEXTO. "
            "Normas:\n"
            "1. Cita el nombre del empleado y su departamento real.\n"
            "2. No asumas que el empleado trabaja en empresas externas mencionadas en la causa.\n"
            "3. Si los hechos no constan en el contexto, declara que no hay evidencia registrada.\n"
            "4. Cita siempre el número de Registro (#X)."
        )

        user_content = f"<CONTEXTO>\n{contexto_textual}\n</CONTEXTO>\n\n<PREGUNTA>\n{pregunta_usuario}\n</PREGUNTA>"

        response = ollama.chat(
            model="llama3.2:3b",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            options={"temperature": 0.0}
        )

        print("\n" + "="*50 + " RESPUESTA AUDITOR RAG " + "="*50)
        print(response["message"]["content"])
        print("="*123 + "\n")

    finally:
        cursor.close()

def main():
    print("Iniciando Agente RAG sobre SQL Server 2025...")
    model_embeddings = SentenceTransformer("all-MiniLM-L6-v2")
    conn_str = (
        "DRIVER={ODBC Driver 18 for SQL Server};"
        "SERVER=localhost;"
        "DATABASE=ControlAccesosIA;"
        "Trusted_Connection=yes;"
        "TrustServerCertificate=yes;"
    )
    conn = pyodbc.connect(conn_str)

    print("\n--- AGENTE RAG LISTO PARA AUDITORÍA ---")
    print("Escribe tus preguntas o escribe 'salir' para cerrar.\n")

    while True:
        try:
            pregunta = input("Pregunta al RAG >> ")
            if not pregunta.strip():
                continue
            if pregunta.strip().lower() in ["salir", "exit", "quit"]:
                print("Cerrando sesión de auditoría...")
                break

            ejecutar_consulta_rag(pregunta, model_embeddings, conn, top_k=5)

        except KeyboardInterrupt:
            break

    conn.close()

if __name__ == "__main__":
    main()