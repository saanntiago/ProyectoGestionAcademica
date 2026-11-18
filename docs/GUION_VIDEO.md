# Guion de la demostración en video (3 minutos)

Objetivo: mostrar que la aplicación cumple los requisitos del Proyecto Integrador:
Flask + MySQL para datos transaccionales, MongoDB para datos no estructurados,
autenticación con bcrypt y consultas parametrizadas.

**Preparación antes de grabar**

1. MySQL (XAMPP) iniciado y `schema.sql` aplicado.
2. MongoDB Atlas accesible (o Compass abierto en la colección `logs` como apoyo visual).
3. Aplicación corriendo con `python app.py` en <http://127.0.0.1:5000>.
4. Navegador con el zoom al 100 %, sin sesión iniciada.
5. Tener a mano el usuario `admin` / `Admin123`.

| Tiempo | Sección | Qué mostrar / decir |
| --- | --- | --- |
| 0:00 – 0:15 | **Presentación** | Nombre, curso y objetivo: “Aplicación de gestión académica con MySQL para datos transaccionales y MongoDB para logs y preferencias”. Mostrar la pantalla de login. |
| 0:15 – 0:35 | **Inicio de sesión seguro** | Iniciar sesión con `admin` / `Admin123`. Mencionar que la contraseña se valida con `bcrypt.checkpw` contra el hash almacenado. |
| 0:35 – 1:00 | **Panel de control** | Recorrer las tarjetas: estudiantes, matrículas activas, cursos y recaudo. Señalar la distribución por carrera y el bloque “Últimos eventos” (datos que vienen de MongoDB). |
| 1:00 – 1:30 | **CRUD de estudiantes** | Abrir *Estudiantes*, buscar por nombre o correo y crear un estudiante nuevo. Mencionar que la búsqueda usa `LIKE %s` con parámetros. Editar el teléfono y guardar. |
| 1:30 – 2:05 | **Matrículas y transacción** | Ir a *Matrículas*, registrar una matrícula (cabecera + detalle en una sola transacción), ingresar una nota y mostrar el estado `APROBADO`/`REPROBADO`. Explicar la relación N:M `MATRICULA` – `DETALLE_MATRICULA` – `CURSO`. |
| 2:05 – 2:25 | **Datos NoSQL** | Abrir *Preferencias*, cambiar a tema oscuro y guardar (se refleja de inmediato). Luego abrir *Registro de actividad* y mostrar los eventos generados: inicio de sesión, estudiante creado/editado, matrícula y nota. |
| 2:25 – 2:45 | **Seguridad** | Cerrar sesión, intentar entrar con usuario `' OR '1'='1` y cualquier contraseña: la aplicación responde “Usuario o contraseña incorrectos”. Abrir *Perfil* (con sesión iniciada) para mostrar el hash bcrypt almacenado. |
| 2:45 – 3:00 | **Cierre** | Recordar la arquitectura (MySQL + MongoDB Atlas), el repositorio en GitHub y agradecer. |

**Consejos de grabación**

- Grabar en una sola toma y hablar mientras se navega; no es necesario editar.
- Evitar mostrar el archivo `.env` con credenciales reales.
- Si MongoDB no responde, la app sigue funcionando: sirve para explicar la tolerancia a fallos.
- Al terminar, dejar la base limpia (eliminar el estudiante y la matrícula creados durante la demo) o aclarar que son datos de ejemplo.

**Evidencias de apoyo:** las capturas equivalentes a cada sección están en [`capturas/`](capturas) y descritas en [`CAPTURAS.md`](CAPTURAS.md).
