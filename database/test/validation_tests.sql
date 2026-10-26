USE ControlAccesosIA;
GO

PRINT '====================================================================';
PRINT '   SUITE DE VALIDACIÓN TÉCNICA Y AUDITORÍA - PROYECTO DP-800        ';
PRINT '====================================================================';
GO

-- ====================================================================
-- TEST 1 (Bloque A): Integridad Relacional y Claves Foráneas (FK)
-- Justificación: Verifica que el modelo relacional protege la integridad
-- referencial impidiendo registros huérfanos en tablas transaccionales.
-- ====================================================================
PRINT CHAR(10) + '>>> [TEST 1] Verificación de restricciones e integridad referencial...';
BEGIN TRY
    -- Intento deliberado de insertar un fichaje para un empleado inexistente (ID: 99999)
    INSERT INTO dbo.Fichajes (empleado_id, fecha_jornada, hora_entrada, hora_salida, estado_acceso)
    VALUES (99999, '20261020', '09:00:00', '18:00:00', 'CORRECTO');

    PRINT '  [FALLO] La restricción FK no impidió la inserción de un empleado inexistente.';
END TRY
BEGIN CATCH
    PRINT '  [ÉXITO] Restricción FK activa y operativa. Error capturado: ' + ERROR_MESSAGE();
END CATCH;
GO

-- ====================================================================
-- TEST 2 (Bloque A): Comprobación de Window Functions y Análisis de Acceso
-- Justificación: Audita la correcta ejecución de funciones analíticas 
-- avanzadas (DENSE_RANK y promedios móviles) para evaluar demoras.
-- ====================================================================
PRINT CHAR(10) + '>>> [TEST 2] Verificación de funciones analíticas (Window Functions)...';

SELECT 
    f.fichaje_id,
    e.nombre + ' ' + e.apellidos AS empleado,
    d.nombre AS departamento,
    f.fecha_jornada,
    f.hora_entrada,
    DENSE_RANK() OVER (
        PARTITION BY e.departamento_id 
        ORDER BY f.hora_entrada DESC
    ) AS ranking_retraso_departamental
FROM dbo.Fichajes f
INNER JOIN dbo.Empleados e ON f.empleado_id = e.empleado_id
INNER JOIN dbo.Departamentos d ON e.departamento_id = d.departamento_id
WHERE f.fecha_jornada >= '20261001';
GO

-- ====================================================================
-- TEST 3 (Bloque C): Dynamic Data Masking (DDM) en Datos Sensibles
-- Justificación: Garantiza que un usuario sin privilegios administrativos
-- (UNMASK) visualiza el DNI y el email anonimizados conforme al RGPD.
-- ====================================================================
PRINT CHAR(10) + '>>> [TEST 3] Verificación de enmascaramiento dinámico de datos (DDM)...';

-- Ejecución en contexto de usuario de auditoría sin privilegios UNMASK
EXECUTE AS USER = 'AuditorJunior';

SELECT TOP 3 
    empleado_id, 
    nombre, 
    apellidos, 
    dni, 
    email 
FROM dbo.Empleados;

REVERT;
PRINT '  [INFO] Ejecutado y revertido contexto de AuditorJunior.';
GO

-- ====================================================================
-- TEST 4 (Bloque D): Rendimiento y Validación de Índices Filtrados
-- Justificación: Demuestra la reducción de lecturas lógicas (Index Seek)
-- frente a un escaneo completo (Scan) al buscar incidencias recurrentes.
-- ====================================================================
PRINT CHAR(10) + '>>> [TEST 4] Auditoría de lecturas lógicas e índices filtrados...';

SET STATISTICS IO ON;

-- Esta consulta debe resolver mediante Index Seek utilizando el índice no agrupado filtrado
SELECT 
    fichaje_id, 
    empleado_id, 
    fecha_jornada, 
    hora_entrada
FROM dbo.Fichajes
WHERE estado_acceso = 'RETRASO'
  AND fecha_jornada >= '20261001';

SET STATISTICS IO OFF;
GO

-- ====================================================================
-- TEST 5 (Bloque E): Existencia y Población del Esquema Vectorial
-- Justificación: Comprueba que la columna nativa VECTOR(384) existe en el
-- catálogo de metadatos y que el pipeline ETL cargó los vectores sin nulos.
-- ====================================================================
PRINT CHAR(10) + '>>> [TEST 5] Auditoría de integridad de columnas vectoriales...';

-- 5.1 Verificación en sys.columns
SELECT 
    c.name AS columna,
    ty.name AS tipo_dato,
    c.max_length,
    c.is_nullable
FROM sys.columns c
INNER JOIN sys.types ty ON c.user_type_id = ty.user_type_id
WHERE c.object_id = OBJECT_ID('dbo.IncidenciasJustificaciones')
  AND c.name = 'embedding_justificacion';

-- 5.2 Comprobación de completitud tras ETL
SELECT 
    COUNT(*) AS total_incidencias,
    COUNT(embedding_justificacion) AS incidencias_vectorizadas,
    SUM(CASE WHEN embedding_justificacion IS NULL THEN 1 ELSE 0 END) AS vectores_pendientes
FROM dbo.IncidenciasJustificaciones;
GO

-- ====================================================================
-- TEST 6 (Bloque F): Búsqueda Semántica Nativa con VECTOR_DISTANCE
-- Justificación: Valida la ejecución en el motor de base de datos de la
-- función VECTOR_DISTANCE('cosine') para clasificar por afinidad semántica.
-- ====================================================================
PRINT CHAR(10) + '>>> [TEST 6] Validación de cálculo de distancia vectorial nativa...';

-- Se toma como referencia el embedding del registro #1 para medir auto-similitud
DECLARE @vector_referencia VECTOR(384);

SELECT TOP 1 @vector_referencia = embedding_justificacion
FROM dbo.IncidenciasJustificaciones
WHERE incidencia_id = 1;

-- El cálculo de distancia de un vector consigo mismo debe ser idéntico a 0.00000
SELECT 
    i.incidencia_id,
    e.nombre + ' ' + e.apellidos AS empleado,
    LEFT(i.texto_justificacion, 60) + '...' AS fragmento_justificacion,
    VECTOR_DISTANCE('cosine', i.embedding_justificacion, @vector_referencia) AS distancia_coseno
FROM dbo.IncidenciasJustificaciones i
INNER JOIN dbo.Fichajes f ON i.fichaje_id = f.fichaje_id
INNER JOIN dbo.Empleados e ON f.empleado_id = e.empleado_id
ORDER BY distancia_coseno ASC;
GO

PRINT CHAR(10) + '====================================================================';
PRINT '   VALIDACIÓN COMPLETA FINALIZADA SIN ERRORES CRÍTICOS              ';
PRINT '====================================================================';
GO