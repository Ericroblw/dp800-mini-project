-- ============================================================================
-- SCRIPT: database/05_security.sql
-- Proyecto: Sistema Inteligente de Auditoría de Accesos e Incidencias
-- Certificación de referencia: Microsoft DP-800: SQL AI Developer Associate
-- ============================================================================

USE ControlAccesosIA;
GO

-- ============================================================================
-- 1. DYNAMIC DATA MASKING (DDM)
-- ============================================================================

-- Aplicar máscara parcial sobre el DNI (muestra primeros 2 dígitos y la letra final)
ALTER TABLE dbo.Empleados
ALTER COLUMN dni ADD MASKED WITH (FUNCTION = 'partial(2, "XXXXXX", 1)');
GO

-- Aplicar máscara estándar sobre el correo electrónico
ALTER TABLE dbo.Empleados
ALTER COLUMN email ADD MASKED WITH (FUNCTION = 'email()');
GO

-- ============================================================================
-- 2. ROLES, USUARIOS Y PRINCIPIO DE MÍNIMO PRIVILEGIO
-- ============================================================================

-- Usuario Auditor (acceso de consulta con datos enmascarados)
IF NOT EXISTS (SELECT name FROM sys.database_principals WHERE name = N'UsuarioAuditor')
BEGIN
    CREATE USER UsuarioAuditor WITHOUT LOGIN;
END
GO
GRANT SELECT ON SCHEMA::dbo TO UsuarioAuditor;
GO

-- Usuario Supervisor de Operaciones (departamento_id = 3)
IF NOT EXISTS (SELECT name FROM sys.database_principals WHERE name = N'SupervisorOperaciones')
BEGIN
    CREATE USER SupervisorOperaciones WITHOUT LOGIN;
END
GO
GRANT SELECT ON dbo.Empleados TO SupervisorOperaciones;
GRANT SELECT ON dbo.Fichajes TO SupervisorOperaciones;
GO

-- ============================================================================
-- 3. ROW-LEVEL SECURITY (RLS)
-- ============================================================================

-- Función con valores de tabla en línea (Inline TVF) para predicado de seguridad
CREATE OR ALTER FUNCTION dbo.fn_SeguridadFiltroDepartamento(@departamento_id INT)
RETURNS TABLE
WITH SCHEMABINDING
AS
RETURN (
    SELECT 1 AS acceso_concedido
    WHERE 
        USER_NAME() IN ('dbo', 'UsuarioAuditor')
        OR (USER_NAME() = 'SupervisorOperaciones' AND @departamento_id = 3)
);
GO

-- Directiva de seguridad (Security Policy)
IF EXISTS (SELECT 1 FROM sys.security_policies WHERE name = N'Pol_FiltroEmpleadosPorDepartamento')
BEGIN
    DROP SECURITY POLICY dbo.Pol_FiltroEmpleadosPorDepartamento;
END
GO

CREATE SECURITY POLICY dbo.Pol_FiltroEmpleadosPorDepartamento
ADD FILTER PREDICATE dbo.fn_SeguridadFiltroDepartamento(departamento_id)
ON dbo.Empleados
WITH (STATE = ON);
GO

-- ============================================================================
-- 4. CONSULTAS DE DEMOSTRACIÓN Y VERIFICACIÓN
-- ============================================================================

-- Verificación DDM: Administrador (ve datos en claro)
SELECT empleado_id, nombre, apellidos, dni, email FROM dbo.Empleados;
GO

-- Verificación DDM: UsuarioAuditor (ve datos ofuscados)
EXECUTE AS USER = 'UsuarioAuditor';
SELECT empleado_id, nombre, apellidos, dni, email FROM dbo.Empleados;
REVERT;
GO

-- Verificación RLS: SupervisorOperaciones (solo filas con departamento_id = 3)
EXECUTE AS USER = 'SupervisorOperaciones';
SELECT empleado_id, departamento_id, nombre, apellidos FROM dbo.Empleados;
REVERT;
GO