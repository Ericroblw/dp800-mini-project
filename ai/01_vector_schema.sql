USE ControlAccesosIA;
GO

-- 1. Agregar columna vectorial nativa para almacenar embeddings de 384 dimensiones
IF NOT EXISTS (
    SELECT 1 
    FROM sys.columns 
    WHERE object_id = OBJECT_ID('dbo.IncidenciasJustificaciones') 
      AND name = 'embedding_justificacion'
)
BEGIN
    ALTER TABLE dbo.IncidenciasJustificaciones
    ADD embedding_justificacion VECTOR(384) NULL;
    
    PRINT 'Columna embedding_justificacion VECTOR(384) agregada correctamente.';
END
ELSE
BEGIN
    PRINT 'La columna embedding_justificacion ya existe en dbo.IncidenciasJustificaciones.';
END
GO