# Sistema Inteligente de Auditoría de RRHH: SQL Server 2025 y RAG Local

**Autor:** Eric (@Ericroblw)  
**Nivel del proyecto:** Avanzado (Nivel 3)  
**Certificación de Referencia:** Microsoft DP-800 (Implementing Azure Data Solutions & Designing AI-Ready Solutions)  

---

## 1. Resumen Ejecutivo
Este proyecto implementa una arquitectura híbrida **Database RAG (Retrieval-Augmented Generation)** de nivel empresarial. La solución moderniza un sistema transaccional tradicional (OLTP) de control de accesos y fichajes, integrando capacidades nativas de Inteligencia Artificial mediante el motor vectorial de **SQL Server 2025**. 

En lugar de depender de bases de datos vectoriales de terceros o APIs externas en la nube, el sistema orquesta la inferencia semántica y el razonamiento generativo de forma **100% local**, garantizando la privacidad de los datos de Recursos Humanos, aplicando políticas de seguridad (RLS/DDM) y eliminando por completo las alucinaciones del LLM mediante anclaje relacional (*Grounding*).

---

## 2. Competencias Técnicas Demostradas (Rúbrica DP-800)

El desarrollo cubre los 7 bloques fundamentales de la certificación de bases de datos preparadas para IA:

*   **[Bloque A] Diseño Relacional y Programación T-SQL Avanzada:**
    *   Modelado normalizado en 3FN de las entidades corporativas (`Departamentos`, `Empleados`, `Fichajes`, `IncidenciasJustificaciones`).
    *   Desarrollo de lógica de negocio mediante Stored Procedures con control de transacciones (`BEGIN TRAN / COMMIT`).
    *   Uso de Common Table Expressions (CTE) y Window Functions (`DENSE_RANK() OVER (PARTITION BY...)`) para el análisis departamental de demoras.

*   **[Bloque B] Desarrollo Asistido por IA (Copilot/Prompting):**
    *   Documentación exhaustiva en la bitácora técnica de la resolución de incidentes de desarrollo.
    *   Corrección guiada de errores de formato regional en inserciones masivas (Error 242) mediante parametrización ISO 8601 y `SET DATEFORMAT ymd`.

*   **[Bloque C] Gobernanza y Seguridad de los Datos:**
    *   **Dynamic Data Masking (DDM):** Enmascaramiento de PII (Información Personal Identificable) como el DNI y el correo electrónico corporativo para usuarios con roles no administrativos (`AuditorJunior`).
    *   **Row-Level Security (RLS):** Aislamiento de registros a nivel de fila mediante funciones de predicado, garantizando que cada mánager solo consulte los fichajes de su departamento.

*   **[Bloque D] Optimización del Motor Relacional:**
    *   Auditoría de planes de ejecución mediante `SET STATISTICS IO ON`.
    *   Transformación de cuellos de botella (`Clustered Index Scan` con múltiples lecturas lógicas) en consultas eficientes (`Index Seek`) mediante la creación de índices no agrupados cubiertos y filtrados.

*   **[Bloque E] Procesamiento Vectorial y ETL:**
    *   Implementación del nuevo tipo de dato nativo `VECTOR(384)` en la extensión del esquema SQL.
    *   Desarrollo de un pipeline ETL en Python (`pyodbc`) que procesa textos no estructurados mediante el modelo Transformer `all-MiniLM-L6-v2`.
    *   Resolución técnica del casteo de tipos a través de ODBC (mitigación del Error 529 de conversión `ntext`) utilizando un doble casteo T-SQL: `CAST(CAST(? AS NVARCHAR(MAX)) AS VECTOR(384))`.

*   **[Bloque F] Búsqueda Semántica Integrada (Intelligent Search):**
    *   Ejecución de inferencia de proximidad directamente en el motor de base de datos utilizando la función nativa `VECTOR_DISTANCE('cosine', vector1, vector2)`.
    *   Ordenación de resultados por relevancia semántica sin necesidad de extraer los datos a un servicio externo.

*   **[Bloque G] RAG Híbrido y Orquestación LLM:**
    *   Integración mediante API local con Ollama ejecutando el modelo conversacional ligero `llama3.2:3b`.
    *   Implementación de recuperación híbrida (Semantic Search + Relational JOINs) para enriquecer el bloque `<CONTEXTO>`.
    *   Mitigación comprobada de alucinaciones: Al suministrar al LLM metadatos precisos (nombre real, departamento, fecha y hora) con `temperature: 0.0`, se evita la deducción errónea de afiliaciones corporativas (ej. asumir que el empleado trabaja para "Renfe" al citarse una huelga de trenes).

---

## 3. Arquitectura del Sistema y Flujo de Datos

```text
+-----------------------------------------------------------------------------------+
|                     CAPA RELACIONAL & VECTORIAL (SQL Server 2025)                 |
|                                                                                   |
|   [Departamentos] <--- [Empleados] <--- [Fichajes] <--- [IncidenciasJustificaciones]|
|       (RLS)               (DDM)                              embedding_justificacion|
|                                                                    VECTOR(384)    |
+-----------------------------------------------------------------------------------+
                                         ▲
         (pyodbc / T-SQL Nativo)         │
                                         ▼
+------------------------------------+       +--------------------------------------+
|        PIPELINE ETL VECTORIAL      |       |          AGENTE RAG HÍBRIDO          |
|      (sentence-transformers)       |       |       (Python + Ollama API)          |
|                                    |       |                                      |
| 1. Extracción de textos pendientes |       | 1. Inferencia: Embedding de consulta |
| 2. Modelo: all-MiniLM-L6-v2 (384d) |       | 2. Retrieval: Distancia Coseno + JOIN|
| 3. Actualización binaria T-SQL     |       | 3. Augmentation: Contexto estructurado|
| 4. Control transaccional (Commit)  |       | 4. Generation: llama3.2:3b (Temp=0.0)|
+------------------------------------+       +--------------------------------------+
```

---

## 4. Estructura Completa del Repositorio

```text
dp800-mini-project/
├── .venv/                          # Entorno virtual de Python (aislamiento de dependencias)
├── ai/
│   ├── 01_vector_schema.sql        # DDL: Alter Table para inyección de columna VECTOR(384)
│   ├── 02_populate_embeddings.py   # Script ETL: Inferencia de embeddings y persistencia
│   ├── 03_semantic_search.py       # Script CLI: Validación de la búsqueda por distancia coseno
│   ├── 04_rag_agent.py             # Script orquestador: Bucle interactivo LLM + SQL
│   └── test_env.py                 # Validación pre-ejecución de pyodbc y HuggingFace
├── docs/
│   ├── evidences/                  # Carpeta de capturas para la auditoría de la certificación
│   ├── bitacora_ai.md              # Diario de desarrollo, prompting y resolución de errores
│   └── memoria_tecnica.md          # Documento extenso de justificación arquitectónica
├── sql/
│   ├── 01_create_database.sql      # DDL: Creación e inicialización de ControlAccesosIA
│   ├── 02_create_tables.sql        # DDL: Esquema relacional OLTP en 3FN
│   ├── 03_seed_data.sql            # DML: Población de catálogos y transacciones de prueba
│   ├── 04_advanced_queries.sql     # DQL/DDL: Procedimientos, Vistas y CTEs analíticas
│   ├── 05_security.sql             # DCL/DDL: Políticas DDM y roles para RLS
│   └── 06_optimization.sql         # DDL: Creación de índices filtrados para Query Tuning
├── tests/
│   └── validation_tests.sql        # T-SQL: Suite de pruebas unitarias (Restricciones, RLS, Vectors)
├── requirements.txt                # Manifiesto de librerías Python (pyodbc, sentence-transformers, ollama)
└── README.md                       # Archivo maestro de documentación técnica (este documento)
```

---

## 5. Guía de Despliegue y Ejecución Rápida

### 5.1 Requisitos Previos (Stack Tecnológico)
*   **Base de Datos:** Microsoft SQL Server 2025 (Edición Developer/Preview con soporte vectorial).
*   **Entorno de Desarrollo:** Python 3.11+ y Visual Studio Code.
*   **Controladores:** Microsoft ODBC Driver 18 for SQL Server.
*   **IA Generativa:** Motor `Ollama` instalado y ejecutándose en `localhost:11434`.

### 5.2 Pasos de Puesta en Marcha

**Paso 1: Preparación del Entorno Virtual e IA**
```bash
# 1. Instalar las dependencias de Python
pip install -r requirements.txt

# 2. Descargar el LLM conversacional en Ollama (aprox. 2.0 GB)
ollama run llama3.2:3b
# (Escribir /bye para salir tras la descarga)
```

**Paso 2: Generación del Conocimiento Vectorial**
```bash
# 3. Leer las justificaciones de SQL Server, vectorizarlas y guardarlas
python ai/02_populate_embeddings.py
```

**Paso 3: Interacción con el Auditor RAG**
```bash
# 4. Iniciar la consola interactiva de auditoría
python ai/04_rag_agent.py
```

---

## 6. Evidencias Técnicas de Auditoría y Certificación

A continuación, se presentan las pruebas documentales exigidas para la validación de las competencias técnicas en el motor de base de datos y la orquestación IA:

### 6.1 Capa Vectorial y Esquema Nativo (Bloque E)
Demostración de la modernización del esquema añadiendo la columna especializada `VECTOR(384)`, y confirmación del éxito del pipeline de carga (ETL Python) mediante la visualización de los datos binarios no nulos en SQL Server.

![Esquema Vectorial Creado](./docs/evidencias/01_vector_schema.png)
![Ejecución ETL de Embeddings en Consola](./docs/evidencias/02_etl_embeddings_run.png)
![Datos Vectoriales Persistidos en Base de Datos](./docs/evidencias/03_sql_vector_populated.png)

### 6.2 Búsqueda Semántica (Bloque F)
Validación de la función `VECTOR_DISTANCE` aplicada en T-SQL, clasificando las incidencias de texto libre según su afinidad matemática con el vector de la pregunta del usuario.

![Ranking Semántico Nativo](./docs/evidencias/04_semantic_search_ranking.png)

### 6.3 Despliegue del Motor de Inferencia Local (Bloque G)
Verificación de que el modelo Llama 3.2 ha sido provisionado correctamente en el entorno de escritorio del desarrollador.

![Modelo Ollama Provisionado](docs/evidencias/05_ollama_model_ready.png)

### 6.4 Arquitectura RAG Híbrida y Mitigación de Alucinaciones (Bloque G)
Capturas de la consola de auditoría que demuestran el funcionamiento del *Grounding*. 
El sistema ensambla un prompt enriquecido mediante cruces relacionales (Nombre del empleado, Departamento, Timestamp) que fuerza al LLM a razonar sobre hechos estrictos. Se demuestra también la capacidad del agente para indicar la **ausencia de evidencias** (respuestas de control negativo) sin inventar incidentes.

![Auditoría sobre Incidencias de Transporte](./docs/evidencias/06_rag_grounding_audit.png)
![Tests Semánticos e Inexistencia de Datos](./docs/evidencias/07_rag_interactive_tests.png)

---
*Desarrollado para evaluación académica y demostración de capacidades avanzadas en arquitecturas Data & AI.*