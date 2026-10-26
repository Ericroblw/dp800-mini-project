-- ============================================================================
-- SCRIPT: database/04_views_procedures.sql
-- Proyecto: Sistema Inteligente de Auditoría de Accesos e Incidencias
-- Certificación de referencia: Microsoft DP-800: SQL AI Developer Associate
-- ============================================================================

USE ControlAccesosIA;
GO

-- 1. Vista Analítica Desnormalizada (Capa Semántica)
CREATE OR ALTER VIEW dbo.vw_AuditoriaIncidenciasCompleta
AS
SELECT 
    f.fichaje_id,
    e.empleado_id,
    CONCAT(e.nombre, ' ', e.apellidos) AS nombre_completo,
    d.nombre AS departamento,
    f.fecha_jornada,
    f.hora_entrada,
    f.hora_salida,
    f.estado_acceso,
    ij.incidencia_id,
    ij.tipo_incidencia,
    ij.texto_justificacion,
    ij.estado_aprobacion,
    ij.fecha_creacion AS fecha_justificacion
FROM dbo.Fichajes f
INNER JOIN dbo.Empleados e ON f.empleado_id = e.empleado_id
INNER JOIN dbo.Departamentos d ON e.departamento_id = d.departamento_id
LEFT JOIN dbo.IncidenciasJustificaciones ij ON f.fichaje_id = ij.fichaje_id;
GO

-- 2. Stored Procedure con Manejo de Transacciones y Reglas de Negocio
CREATE OR ALTER PROCEDURE dbo.usp_RegistrarJustificacionIncidencia
    @fichaje_id BIGINT,
    @tipo_incidencia VARCHAR(30),
    @texto_justificacion NVARCHAR(1000),
    @incidencia_id BIGINT OUTPUT
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    BEGIN TRY
        BEGIN TRANSACTION;

        -- Validación de existencia y estado del fichaje
        DECLARE @estado_acceso VARCHAR(20);

        SELECT @estado_acceso = estado_acceso
        FROM dbo.Fichajes
        WHERE fichaje_id = @fichaje_id;

        IF @estado_acceso IS NULL
        BEGIN
            THROW 50001, 'El identificador de fichaje especificado no existe.', 1;
        END

        IF @estado_acceso = 'Normal'
        BEGIN
            THROW 50002, 'Un fichaje con estado Normal no admite justificación de incidencia.', 1;
        END

        -- Validación de unicidad de la justificación
        IF EXISTS (SELECT 1 FROM dbo.IncidenciasJustificaciones WHERE fichaje_id = @fichaje_id)
        BEGIN
            THROW 50003, 'Ya existe una justificación registrada para el fichaje indicado.', 1;
        END

        -- Inserción
        INSERT INTO dbo.IncidenciasJustificaciones (
            fichaje_id, 
            tipo_incidencia, 
            texto_justificacion, 
            estado_aprobacion
        )
        VALUES (
            @fichaje_id, 
            @tipo_incidencia, 
            @texto_justificacion, 
            'Pendiente'
        );

        SET @incidencia_id = SCOPE_IDENTITY();

        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0
            ROLLBACK TRANSACTION;
        
        THROW;
    END CATCH
END;
GO

-- 3. Consulta Analítica Avanzada: CTE + Window Functions
-- Ranking departamental de recurrencia en retrasos
WITH MetricasRetrasos AS (
    SELECT 
        e.empleado_id,
        CONCAT(e.nombre, ' ', e.apellidos) AS empleado,
        d.nombre AS departamento,
        COUNT(f.fichaje_id) AS total_fichajes,
        SUM(CASE WHEN f.estado_acceso = 'Retraso' THEN 1 ELSE 0 END) AS total_retrasos,
        COUNT(ij.incidencia_id) AS justificaciones_aportadas
    FROM dbo.Empleados e
    INNER JOIN dbo.Departamentos d ON e.departamento_id = d.departamento_id
    LEFT JOIN dbo.Fichajes f ON e.empleado_id = f.empleado_id
    LEFT JOIN dbo.IncidenciasJustificaciones ij ON f.fichaje_id = ij.fichaje_id
    GROUP BY e.empleado_id, e.nombre, e.apellidos, d.nombre
),
RankingDepartamental AS (
    SELECT 
        empleado_id,
        empleado,
        departamento,
        total_fichajes,
        total_retrasos,
        justificaciones_aportadas,
        DENSE_RANK() OVER (
            PARTITION BY departamento 
            ORDER BY total_retrasos DESC
        ) AS ranking_reincidencia_dept,
        CAST(AVG(CAST(total_retrasos AS DECIMAL(5,2))) OVER (
            PARTITION BY departamento
        ) AS DECIMAL(5,2)) AS promedio_retrasos_dept
    FROM MetricasRetrasos
)
SELECT 
    empleado,
    departamento,
    total_retrasos,
    ranking_reincidencia_dept,
    promedio_retrasos_dept
FROM RankingDepartamental
ORDER BY departamento, ranking_reincidencia_dept;
GO