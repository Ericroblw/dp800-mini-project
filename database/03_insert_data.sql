-- ============================================================================
-- SCRIPT: database/03_insert_data.sql
-- Proyecto: Sistema Inteligente de Auditoría de Accesos e Incidencias
-- Certificación de referencia: Microsoft DP-800: SQL AI Developer Associate
-- ============================================================================

USE ControlAccesosIA;
GO

-- 1. Inserción de Departamentos
SET IDENTITY_INSERT dbo.Departamentos ON;
INSERT INTO dbo.Departamentos (departamento_id, nombre, centro_coste) VALUES
(1, N'Tecnología e Inteligencia Artificial', N'CC-IT-001'),
(2, N'Recursos Humanos y Talento', N'CC-HR-002'),
(3, N'Operaciones y Logística', N'CC-OPS-003'),
(4, N'Seguridad Corporativa', N'CC-SEC-004');
SET IDENTITY_INSERT dbo.Departamentos OFF;
GO

-- 2. Inserción de Empleados
SET IDENTITY_INSERT dbo.Empleados ON;
INSERT INTO dbo.Empleados (empleado_id, departamento_id, nombre, apellidos, dni, email, activo) VALUES
(1001, 1, N'Carlos', N'Gómez Martínez', '12345678A', N'carlos.gomez@empresa.local', 1),
(1002, 1, N'Lucía', N'Fernández Ruiz', '23456789B', N'lucia.fernandez@empresa.local', 1),
(1003, 2, N'Marcos', N'Navarro Cano', '34567890C', N'marcos.navarro@empresa.local', 1),
(1004, 3, N'Elena', N'Prieto Vega', '45678901D', N'elena.prieto@empresa.local', 1),
(1005, 3, N'David', N'Serrano Blanco', '56789012E', N'david.serrano@empresa.local', 1),
(1006, 4, N'Sara', N'Molina Ortiz', '67890123F', N'sara.molina@empresa.local', 1);
SET IDENTITY_INSERT dbo.Empleados OFF;
GO

-- 3. Inserción de Fichajes Iniciales
SET IDENTITY_INSERT dbo.Fichajes ON;
INSERT INTO dbo.Fichajes (fichaje_id, empleado_id, fecha_jornada, hora_entrada, hora_salida, estado_acceso) VALUES
(1, 1001, '2026-10-01', '08:00:00', '16:30:00', 'Normal'),
(2, 1001, '2026-10-02', '09:25:00', '17:00:00', 'Retraso'),
(3, 1002, '2026-10-02', '09:40:00', '17:30:00', 'Retraso'),
(4, 1003, '2026-10-03', '08:05:00', '16:35:00', 'Normal'),
(5, 1004, '2026-10-03', '10:15:00', '18:00:00', 'Retraso'),
(6, 1005, '2026-10-05', '09:10:00', '17:15:00', 'Retraso'),
(7, 1006, '2026-10-05', '08:00:00', '16:00:00', 'Normal'),
(8, 1001, '2026-10-06', '09:50:00', '17:20:00', 'Retraso');
SET IDENTITY_INSERT dbo.Fichajes OFF;
GO

-- 4. Inserción de Justificaciones Semánticas (Candidatos a Embeddings)
SET IDENTITY_INSERT dbo.IncidenciasJustificaciones ON;
INSERT INTO dbo.IncidenciasJustificaciones (incidencia_id, fichaje_id, tipo_incidencia, texto_justificacion, estado_aprobacion) VALUES
(1, 2, 'Transporte', N'Retraso debido a una avería eléctrica en la catenaria del tren de Cercanías entre Atocha y Chamartín, tren detenido 45 minutos.', 'Aprobada'),
(2, 3, 'Transporte', N'Corte de tráfico total por accidente múltiple en la autovía M-40 a la altura de los túneles, retención de más de una hora.', 'Aprobada'),
(3, 5, 'Salud', N'Acudí de urgencia a consulta médica por gastroenteritis aguda a primera hora de la mañana. Adjunto justificante asistencial.', 'Aprobada'),
(4, 6, 'Tecnica', N'Fallo en el sistema de apertura electrónica del garaje comunitario por corte de suministro eléctrico. Imposible sacar el vehículo.', 'Pendiente'),
(5, 8, 'Transporte', N'Huelga imprevista en la línea 6 de Metro que provocó aglomeraciones en los andenes y demoras severas en el servicio.', 'Pendiente');
SET IDENTITY_INSERT dbo.IncidenciasJustificaciones OFF;
GO

-- 5. Generación de Carga Sintética para Pruebas de Optimización (2.000 filas)
-- Nota técnica Bloque B: Empleo de formato canónico ISO y SET DATEFORMAT ymd
SET DATEFORMAT ymd;
SET NOCOUNT ON;

DECLARE @i INT = 1;
WHILE @i <= 2000
BEGIN
    INSERT INTO dbo.Fichajes (empleado_id, fecha_jornada, hora_entrada, hora_salida, estado_acceso)
    VALUES (
        1001 + (@i % 6),
        DATEADD(DAY, -(@i % 60), CAST('20261015' AS DATE)),
        CASE WHEN @i % 5 = 0 THEN '09:30:00' ELSE '08:00:00' END,
        '17:00:00',
        CASE WHEN @i % 5 = 0 THEN 'Retraso' ELSE 'Normal' END
    );
    SET @i = @i + 1;
END;
GO