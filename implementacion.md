# 🔐 Guía de Configuración: Autenticación SSMS y Módulo `db.py`

En arquitecturas de datos para Inteligencia Artificial (estándar **DP-800**), la seguridad en la conexión a la base de datos es tan crítica como el propio modelo de IA. Este documento detalla cómo acceder al motor de SQL Server 2025 a través de SSMS y cómo esa configuración se traslada de forma segura a nuestro orquestador en Python.

---

## 1. Conexión y Autenticación en SSMS 22

Dependiendo de cómo esté configurado el servidor en el equipo de clase o en tu entorno local, deberás usar uno de estos dos métodos para entrar a SQL Server Management Studio (SSMS).

### Opción A: Autenticación de Windows (Windows Authentication)

Es el método predeterminado y el más seguro para desarrollo local, ya que confía en las credenciales de tu sesión del sistema operativo.

**Pasos en SSMS:**

1. Abre SQL Server Management Studio.
2. En la ventana **Connect to Server**, configura:
   * **Server type:** Database Engine
   * **Server name:** `localhost`, `.` (punto), o el nombre de tu máquina.
   * **Authentication:** Windows Authentication
   * **User name:** Aparecerá tu usuario de forma automática (ej. `T07W17\AlumnoM_AI`).
3. Haz clic en **Connect**.

**Traducción a tus variables de entorno (`.env`):**

Al usar este método, tu script de Python no necesita contraseña; delega la seguridad en Windows.

```ini
DB_SERVER=localhost
DB_NAME=ControlAccesosIA
DB_TRUSTED_CONNECTION=yes
```

### Opción B: Autenticación de SQL Server (SQL Server Authentication)

Este método es obligatorio si te conectas a un servidor configurado por el instructor o si se han establecido credenciales específicas para la práctica. Requiere que el servidor tenga activo el **Mixed Mode Authentication**.

**Pasos en SSMS:**

1. Abre SQL Server Management Studio.
2. En la ventana **Connect to Server**, configura:
   * **Server type:** Database Engine
   * **Server name:** `localhost` o la IP del servidor.
   * **Authentication:** SQL Server Authentication
   * **Login:** `sa`
   * **Password:** `<tu_contraseña>`
3. Haz clic en **Connect**.

**Traducción a tus variables de entorno (`.env`):**

Tu script de Python necesitará estas credenciales explícitas para poder interactuar con el motor.

```ini
DB_SERVER=localhost
DB_NAME=ControlAccesosIA
DB_USER=sa
DB_PASS=<tu_contraseña>
```

> ⚠️ **Resolución de Problemas (Error 18456):**
> Si SSMS rechaza tu conexión con el usuario `sa`, conéctate primero usando la **Opción A** (Windows Authentication). Luego haz clic derecho sobre el servidor > **Properties** > **Security** > activa **SQL Server and Windows Authentication mode**. Ve a la carpeta **Security** > **Logins**, asegúrate de que el usuario `sa` esté habilitado (**Enabled**) en sus propiedades y reinicia el servicio de SQL Server.

---

## 2. El Corazón de la Conexión en Python: `db.py`

En arquitecturas empresariales, escribir credenciales directamente en el código (*hardcoding*) es una vulnerabilidad crítica que suspendería cualquier auditoría de seguridad. Para evitarlo, hemos diseñado el módulo `db.py`.

### ¿Qué hace exactamente `db.py`?

Este script actúa como el módulo centralizado de conexión de todo nuestro sistema RAG. Su función es leer la configuración que definiste en el paso anterior y establecer un puente seguro con SQL Server 2025.

### Características Técnicas (Estándar DP-800)

* **Aislamiento de Secretos:** Utiliza la librería `python-dotenv` para leer el archivo `.env`. Las contraseñas nunca se suben a GitHub (el `.env` se excluye mediante `.gitignore`).
* **Soporte Dinámico de Autenticación:**
  * Si detecta `DB_TRUSTED_CONNECTION=yes` en tu `.env`, construye una cadena de conexión `Trusted_Connection=yes;` (Opción A).
  * Si detecta usuario y contraseña, construye una cadena con `UID={usuario};PWD={password};` (Opción B).
* **Gestión del Controlador:** Fuerza el uso de **ODBC Driver 18 for SQL Server**, garantizando compatibilidad con las funciones nativas de vectores (`VECTOR_DISTANCE`) de SQL Server 2025 y encriptando el tráfico de red (`Encrypt=yes;TrustServerCertificate=yes;`).
* **Modularidad y Reusabilidad:** Implementa un patrón de diseño donde la función `get_connection()` se importa desde cualquier script (como `02_populate_embeddings.py` o `04_rag_agent.py`). Si mañana se migra la base de datos a la nube (Azure SQL), solo se modifica `db.py`, sin tocar ni una sola línea de la lógica de Inteligencia Artificial.