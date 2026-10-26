

USE ControlAccesosIA;
GO

-- 1. Limpieza ordenada para permitir re-ejecución limpia (Scripts idempotentes)
IF OBJECT_ID(N'dbo.IncidenciasJustificaciones', N'U') IS NOT NULL DROP TABLE dbo.IncidenciasJustificaciones;
IF OBJECT_ID(N'dbo.Fichajes', N'U') IS NOT NULL DROP TABLE dbo.Fichajes;
IF OBJECT_ID(N'dbo.Empleados', N'U') IS NOT NULL DROP TABLE dbo.Empleados;
IF OBJECT_ID(N'dbo.Departamentos', N'U') IS NOT NULL DROP TABLE dbo.Departamentos;
GO

-- 2. Entidad Maestra: Departamentos
CREATE TABLE dbo.Departamentos (
    departamento_id   INT IDENTITY(1,1) CONSTRAINT PK_Departamentos PRIMARY KEY,
    nombre            NVARCHAR(100) NOT NULL CONSTRAINT UQ_Departamentos_Nombre UNIQUE,
    centro_coste      NVARCHAR(20) NOT NULL
);
GO

-- 3. Entidad Maestra: Empleados
-- Nota DP-800: Columnas 'dni' y 'email' reservadas para Dynamic Data Masking (DDM) en Bloque C
CREATE TABLE dbo.Empleados (
    empleado_id       INT IDENTITY(1001,1) CONSTRAINT PK_Empleados PRIMARY KEY,
    departamento_id   INT NOT NULL,
    nombre            NVARCHAR(100) NOT NULL,
    apellidos         NVARCHAR(100) NOT NULL,
    dni               VARCHAR(15) NOT NULL CONSTRAINT UQ_Empleados_DNI UNIQUE,
    email             NVARCHAR(150) NOT NULL CONSTRAINT UQ_Empleados_Email UNIQUE,
    activo            BIT NOT NULL CONSTRAINT DF_Empleados_Activo DEFAULT 1,
    CONSTRAINT FK_Empleados_Departamentos FOREIGN KEY (departamento_id) 
        REFERENCES dbo.Departamentos(departamento_id)
);
GO

-- 4. Entidad Transaccional: Fichajes
-- Representa el hecho del acceso físico diario y su estado de puntualidad
CREATE TABLE dbo.Fichajes (
    fichaje_id        BIGINT IDENTITY(1,1) CONSTRAINT PK_Fichajes PRIMARY KEY,
    empleado_id       INT NOT NULL,
    fecha_jornada     DATE NOT NULL,
    hora_entrada      TIME NOT NULL,
    hora_salida       TIME NULL,
    estado_acceso     VARCHAR(20) NOT NULL,
    CONSTRAINT FK_Fichajes_Empleados FOREIGN KEY (empleado_id) 
        REFERENCES dbo.Empleados(empleado_id),
    CONSTRAINT CK_Fichajes_Estado CHECK (estado_acceso IN ('Normal', 'Retraso', 'Ausencia', 'Discrepancia'))
);
GO

-- 5. Entidad Cualitativa: IncidenciasJustificaciones
-- Almacena la justificación en lenguaje natural que será vectorizada para la búsqueda semántica
CREATE TABLE dbo.IncidenciasJustificaciones (
    incidencia_id       BIGINT IDENTITY(1,1) CONSTRAINT PK_Incidencias PRIMARY KEY,
    fichaje_id          BIGINT NOT NULL,
    tipo_incidencia     VARCHAR(30) NOT NULL,
    texto_justificacion NVARCHAR(1000) NOT NULL,
    estado_aprobacion   VARCHAR(20) NOT NULL CONSTRAINT DF_Incidencias_Estado DEFAULT 'Pendiente',
    fecha_creacion      DATETIME2(0) NOT NULL CONSTRAINT DF_Incidencias_Fecha DEFAULT SYSDATETIME(),
    CONSTRAINT FK_Incidencias_Fichajes FOREIGN KEY (fichaje_id) 
        REFERENCES dbo.Fichajes(fichaje_id),
    CONSTRAINT CK_Incidencias_Tipo CHECK (tipo_incidencia IN ('Transporte', 'Salud', 'Personal', 'Tecnica')),
    CONSTRAINT CK_Incidencias_Aprobacion CHECK (estado_aprobacion IN ('Pendiente', 'Aprobada', 'Rechazada'))
);
GO



-- 6. Verificación de la creación de tablas

USE ControlAccesosIA;
GO

SELECT 
    t.name AS [Tabla],
    COUNT(c.column_id) AS [TotalColumnas]
FROM sys.tables t
INNER JOIN sys.columns c ON t.object_id = c.object_id
WHERE t.name IN ('Departamentos', 'Empleados', 'Fichajes', 'IncidenciasJustificaciones')
GROUP BY t.name
ORDER BY t.name;
GO