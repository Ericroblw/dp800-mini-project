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

---

## Caso 3: Mitigación de alucinaciones en RAG mediante enriquecimiento relacional (Bloque G)

1. **Prompt utilizado:**
   "Genera un script en Python que use Ollama para responder preguntas sobre los retrasos de los empleados usando las justificaciones recuperadas de SQL Server."

2. **Respuesta de la IA:**
   La IA proporcionó un script que consultaba únicamente la tabla `IncidenciasJustificaciones` y pasaba al prompt del LLM únicamente el ID de incidencia y el texto del motivo.

3. **Partes aceptadas:**
   La integración del cliente `ollama` en Python y la estructura base del System Prompt.

4. **Partes corregidas:**
   Al probar la pregunta sobre transporte público, el modelo LLM (`llama3.2:3b`) alucinó asumiendo que los empleados trabajaban en Renfe o Metro, y confundió los IDs de incidencia con IDs de empleado (*"Un empleado de la línea 6 de Metro, identificado con ID 5..."*). El contexto textual aislado carecía de anclaje factual corporativo.

5. **Verificación técnica:**
   Se rediseñó la consulta de recuperación integrando un `INNER JOIN` relacional entre `IncidenciasJustificaciones`, `Fichajes`, `Empleados` y `Departamentos`, extrayendo el nombre completo real del empleado, su departamento y la fecha/hora de fichaje. Además, se fijó el parámetro `temperature: 0.0`. Se verificó en consola que el LLM identificó con total exactitud al empleado Carlos Gómez Martínez (ID: 1001), su departamento real de Tecnología e IA, y distinguió el transporte público como causa externa del retraso.

---

## Caso 4: Alucinación de esquema por carencia de datos estructurales (Schema Hallucination)

1. **Prompt utilizado:**
   "¿Qué porcentajes son hombres y qué porcentajes son mujeres?"

2. **Respuesta de la IA:**
   El modelo generó T-SQL inventando una regla condicional basada en iniciales: `COUNT(CASE WHEN apellidos LIKE '%M%' THEN 1 END)`. Además, la consulta carecía de cláusula `FROM`, generando el **Error 207** (*Invalid Column Name*).

3. **Partes aceptadas:**
   La conversión matemática utilizando `CAST(... AS FLOAT)` para prevenir la división entera al calcular los porcentajes en SQL Server.

4. **Partes corregidas:**
   El modelo intentó inferir el género de los empleados a partir de sus apellidos porque el esquema no contenía dicha columna. Se diagnosticó un sesgo de complacencia (*Attention Drift*) donde la IA prioriza dar una respuesta sobre respetar las limitaciones de los datos.

5. **Verificación técnica:**
   Se implementó un **Guardrail Crítico** en el System Prompt del orquestador Text-to-SQL indicando explícitamente: *"Si pide datos como género, sexo, edad o salario, y NO existen columnas para ello, NO INVENTES lógicas. Devuelve: `SELECT 'ERROR: DATO NO DISPONIBLE EN EL ESQUEMA'`"*. La corrección obligó al modelo a notificar educadamente la carencia de datos.

---

## Caso 5: Pérdida de metadatos relacionales en el paso a lenguaje natural (Metadata Loss)

1. **Prompt utilizado:**
   "¿Cuál es el empleado que más veces ha llegado tarde?"

2. **Respuesta de la IA:**
   La base de datos se consultó correctamente y devolvió una tupla cruda a Python (ej. `(1006, 'Sara', 'Molina', 1)`). Al redactar la respuesta natural, la IA interpretó erróneamente los datos y dictaminó: *"Sara Molina Ortiz, con una llegada tarde en la fecha 1006"*.

3. **Partes aceptadas:**
   La precisión de la consulta T-SQL generada (`INNER JOIN`, filtro `estado_acceso = 'Retraso'`, `GROUP BY` y ordenación `DESC`).

4. **Partes corregidas:**
   El modelo carecía de cabeceras de columnas, asumiendo que el ID numérico del empleado (`1006`) representaba un año o fecha.

5. **Verificación técnica:**
   Se modificó el paso de recolección de Python utilizando `cursor.description` para capturar los nombres de las columnas reales de SQL Server y se inyectaron en el prompt como un diccionario clave-valor mediante `dict(zip(columnas, row))`. El LLM pasó a recibir metadatos legibles (`{'empleado_id': 1006, 'nombre': 'Sara'}`), eliminando por completo la confusión.

---

## Caso 6: Mapeo temporal dinámico y anclaje de veracidad (Temporal Mocking)

1. **Prompt utilizado:**
   "¿Quiénes han llegado tarde hoy?"

2. **Respuesta de la IA:**
   El agente generó la condición temporal estricta `AND F.fecha_jornada = GETDATE()`, lo que provocó una consulta vacía al estar trabajando sobre una base de datos de pruebas estática con fechas pasadas.

3. **Partes aceptadas:**
   La correcta interpretación semántica de "hoy" traducida a una función de fecha nativa de SQL Server.

4. **Partes corregidas:**
   Tras inyectar una regla temporal para usar `MAX(fecha_jornada)` en lugar de `GETDATE()`, la redacción del dictamen final dudó de la condición. Aunque el motor extrajo un registro a las 09:30, la IA respondió: *"no hay evidencia de que nadie haya llegado tarde"*, reevaluando lógicamente la hora en lugar de confiar en el filtro ya aplicado por la base de datos.

5. **Verificación técnica:**
   Se consolidó una instrucción de **Glosario de Negocio** en el prompt Text-to-SQL y se añadió un anclaje defensivo en el prompt de redacción: *"Los datos que recibes ya cumplen la condición. NO reevalúes lógicamente los datos"*. Esto forzó al LLM a respetar la integridad de las vistas y respuestas devueltas por SQL Server sin cuestionar las horas reportadas.
