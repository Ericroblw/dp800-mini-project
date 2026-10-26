### `bitacora_ai.md`

```markdown
# Bitácora de Desarrollo Asistido por IA (Bloque B - DP-800)

Registro formal de interacción técnica, diagnóstico y corrección de incidencias durante el desarrollo del sistema de auditoría con SQL Server 2025 y RAG.

---

## Caso 1: Generación de datos de prueba para optimización de índices

1. **Prompt utilizado:**
   "Genera un script en T-SQL para insertar 2.000 registros sintéticos en la tabla Fichajes alternando empleados, fechas y estados para probar planes de ejecución."

2. **Respuesta de la IA:**
   Se proporcionó un bucle `WHILE` utilizando la función `DATEADD(DAY, -(@i % 60), '2026-10-15')`.

3. **Partes aceptadas:**
   La estructura de control iterativo y la lógica de distribución modular para alternar estados normales y retrasos.

4. **Partes corregidas:**
   El formato de fecha textual `'2026-10-15'` provocó en tiempo de ejecución el **Error 242**: *"La conversión del tipo de datos varchar en datetime produjo un valor fuera de intervalo"*, debido a que la sesión en SQL Server local tiene configuración regional en español (`DMY`).
   
5. **Verificación técnica:**
   Se corrigió el script incorporando la directiva explícita `SET DATEFORMAT ymd;` y formateando el literal de fecha en formato canónico ISO sin guiones (`CAST('20261015' AS DATE)`), verificando en SSMS que las 2.000 filas se insertaron limpiamente sin errores.

---

## Caso 2: Conversión explícita de tipos al insertar vectores con pyodbc (Bloque E)

1. **Prompt utilizado:**
   "¿Cómo inserto los vectores generados por sentence-transformers en la columna VECTOR(384) de SQL Server 2025 usando pyodbc en Python?"

2. **Respuesta de la IA:**
   Se sugirió un `UPDATE` directo pasando la lista de Python convertida en cadena JSON con un único casteo: `UPDATE dbo.IncidenciasJustificaciones SET embedding_justificacion = CAST(? AS VECTOR(384)) WHERE incidencia_id = ?`.

3. **Partes aceptadas:**
   La serialización del array de flotantes a formato JSON (`json.dumps(vector.tolist())`).

4. **Partes corregidas:**
   En tiempo de ejecución mediante el controlador `ODBC Driver 18 for SQL Server`, la consulta falló con el **Error 529**: *"No se permite la conversión explícita del tipo de datos ntext a vector"*, ya que el driver mapea parámetros de cadena de texto largo al tipo heredado `ntext`.

5. **Verificación técnica:**
   Se corrigió la sentencia T-SQL aplicando un doble casteo explícito:
   ```sql
   UPDATE dbo.IncidenciasJustificaciones 
   SET embedding_justificacion = CAST(CAST(? AS NVARCHAR(MAX)) AS VECTOR(384)) 
   WHERE incidencia_id = ?;
   ```


   ## Caso 3: Mitigación de alucinaciones en RAG mediante enriquecimiento relacional (Bloque G)

1. **Prompt utilizado:**
   "Genera un script en Python que use Ollama para responder preguntas sobre los retrasos de los empleados usando las justificaciones recuperadas de SQL Server."

2. **Respuesta de la IA:**
   La IA proporcionó un script que consultaba únicamente la tabla `IncidenciasJustificaciones` y pasaba al prompt del LLM únicamente el ID de incidencia y el texto del motivo.

3. **Partes aceptadas:**
   La integración del cliente `ollama` en Python y la estructura base del *System Prompt*.

4. **Partes corregidas:**
   Al probar la pregunta sobre transporte público, el modelo LLM (`llama3.2:3b`) alucinó asumiendo que los empleados trabajaban en Renfe o Metro, y confundió los IDs de incidencia con IDs de empleado ("Un empleado de la línea 6 de Metro, identificado con ID 5..."). El contexto textual aislado carecía de anclaje factual corporativo.

5. **Verificación técnica:**
   Se rediseñó la consulta de recuperación integrando un `INNER JOIN` relacional entre `IncidenciasJustificaciones`, `Fichajes`, `Empleados` y `Departamentos`, extrayendo el nombre completo real del empleado, su departamento y la fecha/hora de fichaje. Además, se fijó el parámetro `temperature: 0.0`. Se verificó en consola que el LLM identificó con total exactitud al empleado Carlos Gómez Martínez (ID: 1001), su departamento real de Tecnología e IA, y distinguió el transporte público como causa externa del retraso.