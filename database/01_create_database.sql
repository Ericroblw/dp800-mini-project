

-- 1. Verificación e inicialización de la base de datos
IF NOT EXISTS (
    SELECT 1 
    FROM sys.databases 
    WHERE name = N'ControlAccesosIA'
)
BEGIN
    PRINT 'Creando la base de datos ControlAccesosIA...';
    CREATE DATABASE ControlAccesosIA;
END
ELSE
BEGIN
    PRINT 'La base de datos ControlAccesosIA ya existe en la instancia.';
END
GO

-- 2. Conmutar el contexto de ejecución a la base de datos del proyecto
USE ControlAccesosIA;
GO

-- 3. Verificación de confirmación de contexto
SELECT 
    DB_NAME() AS [BaseDeDatosActual],
    DATABASEPROPERTYEX(DB_NAME(), 'Collation') AS [Collation],
    DATABASEPROPERTYEX(DB_NAME(), 'Status') AS [Estado];
GO