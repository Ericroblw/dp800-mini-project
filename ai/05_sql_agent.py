import json
import ollama
from sentence_transformers import SentenceTransformer
from db import get_connection

# Inicializamos el modelo de embeddings
embedder = SentenceTransformer("all-MiniLM-L6-v2")
MODEL_LLM = "llama3.2:3b"

# =====================================================================
# CEREBRO: ENRUTADOR DE INTENCIONES (ROUTER AGENT)
# =====================================================================
def clasificar_intencion(user_query):
    system_prompt = """Eres el enrutador de un sistema de Inteligencia Artificial corporativo.
- Responde "VECTORES" si la pregunta busca motivos, justificaciones, textos libres, excusas o circunstancias de incidencias (ej. tren, atasco, médico).
- Responde "SQL" si la pregunta busca porcentajes, contar, listar totales, sumar, buscar empleados específicos o estadísticas.
NO des explicaciones. Devuelve únicamente VECTORES o SQL."""

    response = ollama.chat(
        model=MODEL_LLM,
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_query}],
        options={"temperature": 0.0}
    )
    decision = response["message"]["content"].strip().upper()
    return "VECTORES" if "VECTORES" in decision else "SQL"

# =====================================================================
# MOTOR 1: RUTA SEMÁNTICA Y RAG HÍBRIDO (VECTORES NATIVOS DP-800)
# =====================================================================
def get_all_employees():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT empleado_id, nombre + ' ' + apellidos, departamento_id FROM dbo.Empleados;")
    datos = cursor.fetchall()
    conn.close()
    return datos

def get_all_delays():
    conn = get_connection()
    cursor = conn.cursor()
    sql = """
        SELECT DISTINCT TOP (30) e.nombre, f.fecha_jornada, COALESCE(i.texto_justificacion, '[SIN JUSTIFICANTE]')
        FROM dbo.Fichajes f
        INNER JOIN dbo.Empleados e ON f.empleado_id = e.empleado_id
        LEFT JOIN dbo.IncidenciasJustificaciones i ON f.fichaje_id = i.fichaje_id
        WHERE f.estado_acceso = 'Retraso' ORDER BY f.fecha_jornada DESC;
    """
    cursor.execute(sql)
    datos = cursor.fetchall()
    conn.close()
    return datos

def retrieve_semantic_context(user_query):
    query_vector = embedder.encode(user_query).tolist()
    conn = get_connection()
    cursor = conn.cursor()
    sql = """
        SELECT TOP (5) e.nombre, i.texto_justificacion, 
        VECTOR_DISTANCE('cosine', i.embedding_justificacion, CAST(CAST(? AS NVARCHAR(MAX)) AS VECTOR(384))) AS dist
        FROM dbo.IncidenciasJustificaciones i
        INNER JOIN dbo.Fichajes f ON i.fichaje_id = f.fichaje_id
        INNER JOIN dbo.Empleados e ON f.empleado_id = e.empleado_id
        WHERE i.embedding_justificacion IS NOT NULL ORDER BY dist ASC;
    """
    cursor.execute(sql, (json.dumps(query_vector),))
    datos = cursor.fetchall()
    conn.close()
    return datos

def ejecutar_ruta_vectores(user_query):
    empleados = get_all_employees()
    retrasos = get_all_delays()
    semantica = retrieve_semantic_context(user_query)

    ctx = f"Censo: {len(empleados)} empleados.\nÚltimos retrasos: {retrasos}\nCoincidencias semánticas: {semantica}"
    prompt = "Eres un auditor corporativo. Usa los siguientes datos para responder la duda del usuario de forma profesional y concisa. No inventes nada fuera de este contexto: " + ctx

    response = ollama.chat(
        model=MODEL_LLM,
        messages=[{"role": "system", "content": prompt}, {"role": "user", "content": user_query}],
        options={"temperature": 0.0}
    )
    return response["message"]["content"]

# =====================================================================
# MOTOR 2: RUTA ANALÍTICA Y GENERACIÓN AUTÓNOMA (TEXT-TO-SQL)
# =====================================================================
def get_database_schema():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME IN ('Empleados', 'Departamentos', 'Fichajes', 'IncidenciasJustificaciones');")
    schema_dict = {}
    for t, c, d in cursor.fetchall():
        schema_dict.setdefault(t, []).append(f"{c} ({d})")
    conn.close()
    return "".join([f"Tabla: {t}\nCols: {', '.join(c)}\n" for t, c in schema_dict.items()])

def ejecutar_ruta_sql(user_query, schema_text):
    # 1. Fase de Ingeniería de Prompts (Guardrails y Sintaxis)
    prompt_sql = f"""Esquema de la base de datos:
{schema_text}

Eres un DBA estricto experto en SQL Server 2025. Genera ÚNICAMENTE código T-SQL válido (sin comillas ni formato markdown).

GUARDRAIL CRÍTICO (DP-800):
Analiza si los datos que pide el usuario existen en el Esquema. Si pide datos como género, sexo, edad o salario, y NO existen columnas para ello, NO INVENTES lógicas. DEBES devolver EXACTAMENTE y únicamente esta consulta:
SELECT 'ERROR: DATO NO DISPONIBLE EN EL ESQUEMA' AS resultado;

REGLAS DE GENERACIÓN:
1. SINTAXIS: Todo SELECT debe llevar su cláusula FROM correspondiente.
2. LÍMITES: Usa TOP (10) para listar registros, evitando colapsar la consola.
3. AGREGACIONES: Usa COUNT() sin TOP para totales.
4. PORCENTAJES: Usa CAST(COUNT(...) AS FLOAT) * 100.0 para evitar la división entera.
5. GLOSARIO DE NEGOCIO: Cuando el usuario pregunte por "llegar tarde", "retrasos" o "tardanzas", DEBES filtrar estrictamente utilizando la condición: estado_acceso = 'Retraso' en la tabla Fichajes.
6. FECHAS EN ENTORNO DE PRUEBAS: Si el usuario pregunta por "hoy", "el día actual" o "último día", NO utilices GETDATE(). Debes asumir que "hoy" es la fecha más reciente registrada en la base de datos. Utiliza esta subconsulta exacta para filtrar: fecha_jornada = (SELECT MAX(fecha_jornada) FROM Fichajes).
"""
    res_sql = ollama.chat(
        model=MODEL_LLM,
        messages=[{"role": "system", "content": prompt_sql}, {"role": "user", "content": user_query}],
        options={"temperature": 0.0}
    )
    sql_code = res_sql["message"]["content"].replace("```sql", "").replace("```", "").strip()
    
    # Debug silencioso interno para auditoría
    print(f"    [Trace] T-SQL Generado:\n{sql_code}\n")
    
    # 2. Ejecución Segura y Empaquetado de Metadatos
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(sql_code)
        datos_crudos = cursor.fetchall()
        if datos_crudos:
            # Extraemos los nombres de las columnas y empaquetamos cada fila como un diccionario JSON
            columnas = [col[0] for col in cursor.description]
            db_data = "\n".join([str(dict(zip(columnas, row))) for row in datos_crudos])
        else:
            db_data = "La base de datos devolvió 0 resultados."
    except Exception as e:
        db_data = f"El código SQL generado fue inválido o falló la ejecución: {e}"
        print(f"    [Error] {e}")
    finally:
        cursor.close()
        conn.close()
        
    # 3. Redacción Natural Interactiva
    prompt_redaccion = f"""Eres el auditor de la empresa. El sistema ha ejecutado la consulta y devuelto estos datos estructurados con el nombre de sus columnas:
{db_data}

Responde la duda original del usuario utilizando esta información. 
- Si los datos indican un ERROR de esquema o falta de disponibilidad, notifícaselo al usuario amablemente. 
- Interpreta los datos basándote en los nombres de las columnas proporcionadas.
- Omite detalles técnicos de SQL."""
    
    res_final = ollama.chat(
        model=MODEL_LLM,
        messages=[{"role": "system", "content": prompt_redaccion}, {"role": "user", "content": user_query}],
        options={"temperature": 0.2}
    )
    return res_final["message"]["content"]

# =====================================================================
# BUCLE ORQUESTADOR DEL SISTEMA
# =====================================================================
if __name__ == "__main__":
    print("="*75)
    print(" 🧠 AGENTE MAESTRO UNIFICADO DP-800 (RAG Semántico + Text-to-SQL)")
    print("="*75)
    print("[*] Levantando orquestador, motores vectoriales y mapeando BD...")
    esquema_global = get_database_schema()
    print("[*] Sistema 100% operativo. Escribe 'salir' para terminar.\n")
    
    while True:
        query = input("Auditoría > ").strip()
        if query.lower() in ("salir", "exit", "quit"): break
        if not query: continue
        
        print("  [Analizando intención del usuario...]")
        ruta = clasificar_intencion(query)
        print(f"  [Enrutando petición al motor especializado: {ruta}]")
        
        try:
            if ruta == "VECTORES":
                respuesta = ejecutar_ruta_vectores(query)
            else:
                respuesta = ejecutar_ruta_sql(query, esquema_global)
                
            print("\n[Dictamen Final]")
            print(respuesta)
            print("-" * 75 + "\n")
        except Exception as e:
            print(f"\n[!] Error crítico de infraestructura: {e}")