# Proyecto Integrador — Gestión Académica

Aplicación web desarrollada en **Flask** que combina dos modelos de datos para administrar la información de una universidad:

| Motor | Tipo de dato | Contenido |
| --- | --- | --- |
| **MySQL** (`bd_universidad`) | Transaccional (relacional, ACID) | usuarios, carreras, estudiantes, profesores, materias, cursos y matrículas |
| **MongoDB Atlas** (`gestion_academica`) | No estructurado (documentos) | logs de actividad y preferencias de cada usuario |

Incluye **autenticación básica** con contraseñas cifradas mediante **bcrypt + salt**, **consultas 100 % parametrizadas** para prevenir inyección SQL, registro de auditoría en MongoDB y una interfaz responsiva construida con Bootstrap 5.

> **Curso:** Teoría de Bases de Datos — Universidad Manuela Beltrán
> **Entrega:** Actividad 5 — Proyecto Integrador
> **Autor:** Santiago Duque

---

## 1. Requisitos previos

- **Python 3.10 o superior** (probado con Python 3.14 en Windows).
- **MySQL Server 8** o **MariaDB / XAMPP** (probado con MariaDB 10.4 de XAMPP).
- **MongoDB Atlas** (cuenta gratuita) o **MongoDB Community Server** local.
  - Alternativa opcional: **Firebase / Cloud Firestore** (`NOSQL_BACKEND=firebase`).
- Opcional para inspeccionar los datos: **MySQL Workbench**, **phpMyAdmin** y **MongoDB Compass**.

---

## 2. Obtener el código

```bash
git clone https://github.com/saanntiago/ProyectoGestionAcademica.git
cd ProyectoGestionAcademica
```

---

## 3. Crear el entorno virtual e instalar dependencias

**Windows (PowerShell / CMD):**

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

**Linux / macOS:**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## 4. Crear la base de datos MySQL

Con XAMPP/MySQL encendido, ejecutar el script desde la carpeta del proyecto:

```powershell
# Opción A: consola de XAMPP (Windows)
C:\xampp\mysql\bin\mysql.exe -u root < schema.sql

# Opción B: si "mysql" está en el PATH
mysql -u root -p < schema.sql
```

También se puede abrir `schema.sql` en **MySQL Workbench** o **phpMyAdmin** y ejecutarlo completo.

El script es **idempotente**: crea la base `bd_universidad`, sus tablas (`CARRERA`, `ESTUDIANTE`, `PROFESOR`, `MATERIA`, `CURSO`, `PROFESOR_CURSO`, `MATRICULA`, `DETALLE_MATRICULA` y `USUARIO`) y carga datos de ejemplo solo si no existen. Aplica llaves primarias, llaves foráneas, restricciones `UNIQUE`, `CHECK` e integridad referencial con `ON DELETE CASCADE / RESTRICT`.

### Crear el usuario de prueba

```powershell
python seed.py
```

Crea el usuario **`admin`** con contraseña **`Admin123`** (guardada como hash bcrypt). Es idempotente: si ya existe, no lo duplica. También puedes registrar tu propia cuenta desde la pantalla **Regístrate**.

---

## 5. Configurar MongoDB Atlas

1. Crear un clúster gratuito en [MongoDB Atlas](https://www.mongodb.com/atlas).
2. En **Database Access**, crear un usuario de base de datos.
3. En **Network Access**, permitir la IP desde la que se conecta (o `0.0.0.0/0` para la demo).
4. En **Connect → Drivers**, copiar la cadena de conexión:

```
mongodb+srv://USUARIO:CONTRASENA@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
```

No es necesario crear la base ni las colecciones: la aplicación crea `gestion_academica` con las colecciones `logs` y `preferencias` en el primer uso.

> **Alternativa local:** instalar MongoDB Community Server y usar `MONGO_URI=mongodb://localhost:27017`.

> **Alternativa Firebase:** `pip install firebase-admin`, descargar la llave de servicio como `firebase-key.json` y poner `NOSQL_BACKEND=firebase`. El resto del código no cambia, porque `db_nosql.py` selecciona el motor automáticamente.

---

## 6. Configurar las variables de entorno

Copiar la plantilla y completar los valores reales:

```powershell
# Windows
copy .env.example .env

# Linux / macOS
cp .env.example .env
```

Contenido mínimo del `.env`:

```ini
SECRET_KEY=<clave larga y aleatoria>
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=
MYSQL_DB=bd_universidad
NOSQL_BACKEND=mongo
MONGO_URI=mongodb+srv://USUARIO:CONTRASENA@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
MONGO_DB=gestion_academica
VALOR_CREDITO=1000000
FLASK_DEBUG=0
```

Generar una `SECRET_KEY` segura:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

> El archivo `.env` contiene credenciales reales y está incluido en `.gitignore`: **nunca se sube al repositorio**.

---

## 7. Ejecutar la aplicación

```powershell
python app.py
```

Abrir <http://127.0.0.1:5000> e iniciar sesión:

| Usuario | Contraseña |
| --- | --- |
| `admin` | `Admin123` |

Si el puerto 5000 está ocupado:

```powershell
flask --app app run --port 5001
```

---

## 8. Estructura del proyecto

```
ProyectoGestionAcademica/
├── app.py              # Rutas: panel, estudiantes, carreras, cursos, matrículas, preferencias, logs, perfil
├── auth.py             # Registro, login, logout y decorador @login_required
├── config.py           # Lectura de variables de entorno (.env)
├── db_mysql.py         # Conexión MySQL y funciones consultar() / ejecutar() / transaccion()
├── db_nosql.py         # Selecciona MongoDB o Firebase según NOSQL_BACKEND
├── db_mongo.py         # Logs y preferencias en MongoDB
├── db_firebase.py      # Logs y preferencias en Firestore (alternativa)
├── utils.py            # Funciones auxiliares (formato de fechas, validaciones)
├── seed.py             # Crea el usuario administrador de prueba
├── schema.sql          # Creación de la base relacional y datos de ejemplo
├── templates/          # Vistas HTML (Jinja2 + Bootstrap 5)
├── static/             # CSS, JS, favicon y Bootstrap/Icons locales
├── docs/
│   ├── capturas/       # Evidencias de la aplicación en funcionamiento
│   ├── CAPTURAS.md     # Descripción de cada captura
│   └── GUION_VIDEO.md  # Guion de la demostración en video (3 minutos)
├── requirements.txt
├── .env.example        # Plantilla de configuración
└── .gitignore
```

---

## 9. Funcionalidades

- **Autenticación:** registro e inicio de sesión con contraseña cifrada (bcrypt, 12 rondas + salt) y sesiones firmadas por Flask.
- **Rutas protegidas:** sin sesión, cualquier ruta privada redirige al login.
- **Panel de control:** totales de estudiantes, matrículas activas, cursos ofertados y recaudo; distribución de estudiantes por carrera y últimos eventos de MongoDB.
- **CRUD de estudiantes** con búsqueda parametrizada por nombre, correo o ID.
- **Catálogo de carreras y cursos** con cupos, periodo, aula y horario.
- **Matrículas (relación N:M):** una sola transacción crea la cabecera `MATRICULA` y el detalle `DETALLE_MATRICULA`; validación de duplicados y de cupos.
- **Registro de notas** por curso, con estado `APROBADO` / `REPROBADO`.
- **Preferencias por usuario en NoSQL:** tema claro/oscuro, idioma y registros por página.
- **Auditoría en MongoDB:** cada login, login fallido, creación, edición o eliminación genera un documento en `logs` con usuario, acción, detalle, IP y fecha UTC.
- **Perfil:** muestra el hash bcrypt almacenado y los datos de la cuenta.

---

## 10. Seguridad implementada

| Riesgo | Medida |
| --- | --- |
| Inyección SQL (OWASP A03) | Todas las consultas usan marcadores `%s`; los valores viajan separados del SQL. |
| Inyección NoSQL | Los filtros de MongoDB convierten los valores a `str()` antes de usarlos. |
| Contraseñas en texto plano | Solo se guarda el hash bcrypt con salt (`bcrypt.hashpw` / `checkpw`). |
| Acceso no autorizado | Decorador `@login_required` y `session.clear()` en cada login/logout. |
| Credenciales en el código | Se leen del `.env`, excluido del repositorio. |
| Manipulación de sesión | `SECRET_KEY` privada que firma la cookie de Flask. |
| Errores internos expuestos | Manejadores de error 404/500 con vista amigable y log en consola. |

---

## 11. Pruebas sugeridas

1. **Inyección SQL en el login:** usuario `' OR '1'='1` y cualquier contraseña → debe responder *“Usuario o contraseña incorrectos”* y registrar un evento `login_fallido`.
2. **Búsqueda maliciosa:** en Estudiantes buscar `%' OR 1=1 --` → no lista todo ni genera error.
3. **Hash:** en MySQL ejecutar `SELECT Username, PasswordHash FROM USUARIO;` → no aparece la contraseña en texto plano.
4. **Integridad:** intentar registrar dos matrículas activas del mismo estudiante en el mismo curso → se rechaza.
5. **Rutas protegidas:** cerrar sesión y abrir `/estudiantes` → redirige al login.
6. **Transacción:** crear una matrícula y verificar que se insertan cabecera y detalle; si falla el detalle, no queda la cabecera.
7. **Borrado en cascada:** eliminar una matrícula con detalle → desaparecen ambos registros.
8. **NoSQL:** revisar en MongoDB Compass / Atlas las colecciones `logs` y `preferencias` de `gestion_academica`.
9. **Tolerancia a fallos:** detener MongoDB; la app sigue funcionando y solo muestra una advertencia en consola.

Las capturas de estas pruebas están en [`docs/capturas`](docs/capturas) y descritas en [`docs/CAPTURAS.md`](docs/CAPTURAS.md).

---

## 12. Solución de problemas

| Error | Causa probable | Solución |
| --- | --- | --- |
| `Access denied for user 'root'` | Contraseña de MySQL incorrecta | Revisar `MYSQL_PASSWORD` en `.env` |
| `Unknown database 'bd_universidad'` | No se ejecutó el script | Ejecutar `schema.sql` |
| `Can't connect to MySQL server` | MySQL apagado o puerto distinto | Iniciar MySQL en XAMPP o ajustar `MYSQL_PORT` |
| `[ADVERTENCIA] No se pudo registrar el log` | MongoDB apagado o URI incorrecta | Revisar `MONGO_URI`; la app sigue funcionando |
| `ServerSelectionTimeoutError` (Atlas) | IP no autorizada | Agregar la IP en *Network Access* de Atlas |
| `Address already in use` | Puerto 5000 ocupado | `flask --app app run --port 5001` |
| `ModuleNotFoundError` | Entorno virtual sin activar | Activar `.venv` y repetir `pip install -r requirements.txt` |
| `pymongo` no reconoce el certificado | Reloj del sistema desfasado | Sincronizar la hora de Windows |

---

## 13. Guion de la demostración

El guion con los tiempos sugeridos para el video de 3 minutos está en [`docs/GUION_VIDEO.md`](docs/GUION_VIDEO.md).
