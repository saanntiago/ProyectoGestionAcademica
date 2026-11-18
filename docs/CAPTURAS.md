# Capturas de la aplicación

Evidencias tomadas de la aplicación en funcionamiento (datos de ejemplo de `schema.sql`
y eventos reales registrados en MongoDB Atlas durante una sesión de pruebas).

| Archivo | Contenido |
| --- | --- |
| `01_login.png` | Pantalla de inicio de sesión. Muestra el formulario, la cuenta de prueba y la descripción de la arquitectura MySQL + MongoDB. |
| `02_panel.png` | Panel de control con estudiantes, matrículas activas, cursos, recaudo, distribución por carrera y últimos eventos leídos de MongoDB. |
| `03_estudiantes.png` | Listado de estudiantes con búsqueda parametrizada y acciones de edición/eliminación. |
| `04_formulario_estudiante.png` | Formulario de alta de estudiante con validaciones del navegador. |
| `05_matriculas.png` | Matrículas registradas con el JOIN de `MATRICULA`, `DETALLE_MATRICULA`, `CURSO` y `MATERIA`, notas y estado. |
| `06_cursos.png` | Oferta académica: curso, materia, periodo, cupos, aula y horario. |
| `07_carreras.png` | Catálogo de carreras con el número de estudiantes y creación de una nueva carrera (la llave foránea usa `ON DELETE RESTRICT`). |
| `08_preferencias.png` | Preferencias del usuario almacenadas como documento en MongoDB (`tema`, `idioma`, `registros_por_pagina`) y vista del documento en bruto. |
| `09_logs.png` | Colección `logs` de MongoDB: usuario, acción, detalle, IP y fecha UTC de cada evento. |
| `10_perfil_hash.png` | Perfil del usuario con el hash bcrypt almacenado en MySQL (evidencia de que no se guarda la contraseña en texto plano). |
| `11_tema_oscuro.png` | Tema oscuro aplicado desde las preferencias NoSQL, sin reiniciar la aplicación. |
| `12_inyeccion_sql.png` | Intento de inyección SQL en el login (`' OR '1'='1`): la aplicación rechaza el acceso y registra `login_fallido`. |

Todas las imágenes se generaron con Playwright sobre Chrome en
`http://127.0.0.1:5000`, con una resolución de 1440 × 950 px.
