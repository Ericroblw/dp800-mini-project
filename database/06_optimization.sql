-- ============================================================================
-- SCRIPT: database/06_optimization.sql
-- Proyecto: Sistema Inteligente de Auditoría de Accesos e Incidencias
-- Certificación de referencia: Microsoft DP-800: SQL AI Developer Associate
-- ============================================================================

USE ControlAccesosIA;
GO

-- ============================================================================
-- ESTADO INICIAL (Antes de Optimizar)
-- Se observa: Clustered Index Scan | Lecturas Lógicas: 13
-- ============================================================================

-- Asegurarse de que el índice no existe para reproducir el estado inicial
IF EXISTS (SELECT name FROM sys.indexes WHERE name = N'IX_Fichajes_Retrasos_Fecha')
BEGIN
    DROP INDEX IX_Fichajes_Retrasos_Fecha ON dbo.Fichajes;
END
GO

SET STATISTICS IO ON;
SET STATISTICS TIME ON;
GO

SELECT 
    fichaje_id, 
    empleado_id, 
    fecha_jornada, 
    hora_entrada
FROM dbo.Fichajes
WHERE estado_acceso = 'Retraso'
  AND fecha_jornada >= '2026-10-01';
GO

SET STATISTICS IO OFF;
SET STATISTICS TIME OFF;
GO

-- ============================================================================
-- CREACIÓN DEL ÍNDICE OPTIMIZADO
-- Técnica: Filtro por anomalía + Clave temporal + Cobertura (INCLUDE)
-- ============================================================================

CREATE NONCLUSTERED INDEX IX_Fichajes_Retrasos_Fecha
ON dbo.Fichajes (fecha_jornada)
INCLUDE (empleado_id, hora_entrada)
WHERE estado_acceso = 'Retraso';
GO

-- ============================================================================
-- ESTADO FINAL (Después de Optimizar)
-- Se observa: Index Seek (NonClustered) | Lecturas Lógicas: 4 (Reducción ~69%)
-- ============================================================================

SET STATISTICS IO ON;
SET STATISTICS TIME ON;
GO

SELECT 
    fichaje_id, 
    empleado_id, 
    fecha_jornada, 
    hora_entrada
FROM dbo.Fichajes
WHERE estado_acceso = 'Retraso'
  AND fecha_jornada >= '2026-10-01';
GO

SET STATISTICS IO OFF;
SET STATISTICS TIME OFF;
GO