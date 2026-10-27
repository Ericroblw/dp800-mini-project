import json
import ollama
from sentence_transformers import SentenceTransformer
from db import get_connection

MODEL_EMBEDDINGS = "all-MiniLM-L6-v2"
MODEL_LLM = "llama3.2:3b"

embedder = SentenceTransformer(MODEL_EMBEDDINGS)

def get_all_employees():
    """Recupera el censo maestro de empleados y departamentos."""
    conn = get_connection()
    cursor = conn.cursor()
    sql = """
        SELECT 
            e.empleado_id,
            e.nombre + ' ' + e.apellidos AS empleado,
            d.nombre AS departamento
        FROM dbo.Empleados e
        INNER JOIN dbo.Departamentos d ON e.departamento_id = d.departamento_id
        ORDER BY e.empleado_id;
    """
    try:
        cursor.execute(sql)
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

def get_all_delays():
    """
    Recupera una muestra segura (TOP 30) de retrasos para evitar 
    exceder la ventana de contexto (Context Window Overflow) del LLM.
    """
    conn = get_connection()
    cursor = conn.cursor()
    sql = """
        SELECT DISTINCT TOP (30)
            e.nombre + ' ' + e.apellidos AS empleado,
            d.nombre AS departamento,
            CONVERT(VARCHAR(10), f.fecha_jornada, 120) AS fecha,
            CONVERT(VARCHAR(8), f.hora_entrada, 108) AS hora_entrada,
            COALESCE(i.texto_justificacion, '[SIN JUSTIFICANTE APORTADO]') AS justificacion,
            CASE 
                WHEN i.incidencia_id IS NULL THEN 'NO JUSTIFICADO'
                ELSE 'JUSTIFICADO'
            END AS estado_incidencia
        FROM dbo.Fichajes f
        INNER JOIN dbo.Empleados e ON f.empleado_id = e.empleado_id
        INNER JOIN dbo.Departamentos d ON e.departamento_id = d.departamento_id
        LEFT JOIN dbo.IncidenciasJustificaciones i ON f.fichaje_id = i.fichaje_id
        WHERE f.estado_acceso = 'Retraso'
        ORDER BY fecha DESC, hora_entrada ASC;
    """
    try:
        cursor.execute(sql)
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

def retrieve_semantic_context(user_query, top_k=5):
    """Calcula similitud coseno para consultas sobre motivos y circunstancias."""
    query_vector = embedder.encode(user_query).tolist()
    query_vector_json = json.dumps(query_vector)

    conn = get_connection()
    cursor = conn.cursor()
    sql = """
        SELECT TOP (?)
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
        cursor.execute(sql, (top_k, query_vector_json))
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

def build_prompt(user_query, employees, delays, semantic_rows):
    # 1. Catálogo total de la empresa
    censo_text = f"Total empleados en plantilla: {len(employees)}\n"
    for emp_id, emp_nom, emp_dpto in employees:
        censo_text += f"- [ID: {emp_id}] {emp_nom} | Departamento: {emp_dpto}\n"

    # 2. Histórico reciente (Límite dinámico de seguridad)
    retrasos_text = f"Muestra de las últimas {len(delays)} incidencias de retraso registradas:\n"
    for emp, dpto, fecha, hora, just, est in delays:
        retrasos_text += (
            f"- Fecha: {fecha} | Entrada: {hora} | Empleado: {emp} ({dpto}) | "
            f"Estado: {est} | Detalle: {just}\n"
        )

    # 3. Ranking semántico
    semantica_text = ""
    for emp, dpto, fecha, hora, texto, dist in semantic_rows:
        semantica_text += (
            f"- Empleado: {emp} ({dpto}) | Fecha: {fecha} ({hora}) | "
            f"Justificación: {texto} | Distancia: {dist:.4f}\n"
        )

    system_instruction = (
        "Eres un auditor técnico y asistente de Recursos Humanos corporativo.\n"
        "Dispones de tres bloques de datos fidedignos en <CONTEXTO> extraídos de SQL Server 2025:\n\n"
        "1. <CENSO_TOTAL_EMPLEADOS>: Catálogo maestro de toda la plantilla.\n"
        "2. <HISTORICO_RECIENTE_RETRASOS>: Registro de los accesos con estado 'Retraso' más recientes. Es una muestra de 30 registros, no la base histórica completa.\n"
        "3. <COINCIDENCIAS_SEMANTICAS>: Justificaciones ordenadas por proximidad semántica.\n\n"
        "Instrucciones de auditoría:\n"
        "- Si el usuario pide buscar por letras específicas o iniciales (ej. 'empiezan por A'), advierte que tu lectura se basa en tokens y busca manualmente en <CENSO_TOTAL_EMPLEADOS> para dar la mejor aproximación posible.\n"
        "- Consultas genéricas de incidencias ('quiénes llegaron tarde'): Indica que la información se basa en los últimos registros recientes de <HISTORICO_RECIENTE_RETRASOS>.\n"
        "- Consultas sobre ausencias de justificante: Identifica aquellos registros con estado 'NO JUSTIFICADO'.\n"
        "- Consultas sobre motivos específicos: Revisa <COINCIDENCIAS_SEMANTICAS>.\n"
        "- Responde en español de forma directa, analítica y sin inventar datos fuera del contexto."
    )

    user_message = (
        f"<CONTEXTO>\n"
        f"--- <CENSO_TOTAL_EMPLEADOS> ---\n{censo_text}\n"
        f"--- <HISTORICO_RECIENTE_RETRASOS> ---\n{retrasos_text}\n"
        f"--- <COINCIDENCIAS_SEMANTICAS> ---\n{semantica_text}\n"
        f"</CONTEXTO>\n\n"
        f"Pregunta del auditor: {user_query}"
    )

    return system_instruction, user_message

def ask_rag_agent(user_query):
    empleados = get_all_employees()
    retrasos = get_all_delays()
    coincidencias_semanticas = retrieve_semantic_context(user_query, top_k=5)

    system_instruction, user_message = build_prompt(
        user_query, empleados, retrasos, coincidencias_semanticas
    )

    response = ollama.chat(
        model=MODEL_LLM,
        messages=[
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_message}
        ],
        options={"temperature": 0.0}
    )

    return response["message"]["content"]

def main():
    print("=" * 72)
    print("  AGENTE AUDITOR RAG HÍBRIDO TOTAL - SQL SERVER 2025 & OLLAMA (DP-800)")
    print("=" * 72)
    print("Sesión iniciada con protección de contexto (Max 30 registros transaccionales).")
    print("Escribe 'salir' para finalizar.\n")

    while True:
        query = input("Auditoría > ").strip()
        if query.lower() in ("salir", "exit", "quit"):
            print("Cerrando sesión de auditoría.")
            break

        if not query:
            continue

        print("\n[*] Extrayendo datos relacionales, vectoriales y generando dictamen...")
        try:
            respuesta = ask_rag_agent(query)
            print("\n[Dictamen del Auditor]")
            print(respuesta)
            print("-" * 72 + "\n")
        except Exception as e:
            print(f"[!] Error al procesar la auditoría: {e}\n")

if __name__ == "__main__":
    main()