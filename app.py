"""app.py
------
Proyecto Integrador: Mini-Aplicación de Gestión Académica (UNIVERSIDAD).

Propósito:
    Definir las rutas web de la aplicación Flask.
      - MySQL (bd_universidad) -> datos transaccionales: estudiantes,
        carreras, cursos y matrículas.
      - MongoDB Atlas -> datos no estructurados: logs de actividad y
        preferencias de cada usuario.

Seguridad:
    - Todas las operaciones sobre MySQL usan consultas parametrizadas (%s).
    - Todas las rutas, excepto login y registro, exigen sesión
      (@login_required).
    - Las contraseñas se guardan con hash bcrypt (ver auth.py).

Ejecución:
    python app.py          (o  flask --app app run)
    Abrir http://127.0.0.1:5000

Autor:  Santiago Duque
Curso:  Teoría de Bases de Datos
"""

import math
from datetime import date, datetime, timedelta

from flask import (Flask, abort, flash, g, redirect, render_template,
                   request, session, url_for)
from mysql.connector import IntegrityError

from auth import auth_bp, login_required
from config import Config
from db_mysql import (ErrorBaseDatos, consultar, ejecutar, ejecutar_en,
                      transaccion)
from db_nosql import (contar_logs, contar_por_accion, guardar_preferencias,
                      obtener_documento_preferencias, obtener_logs,
                      obtener_preferencias, registrar_log)
from utils import (correo_valido, entero, formatear_moneda, ip_cliente,
                   patron_like, telefono_valido)

app = Flask(__name__)
app.config.from_object(Config)
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,   # la cookie de sesión no es accesible por JS
    SESSION_COOKIE_SAMESITE="Lax",  # mitiga envíos de cookies desde otros sitios
    PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
)
app.register_blueprint(auth_bp)  # rutas /login, /registro y /logout

# ---------------------------------------------------------------------------
# Constantes de negocio
# ---------------------------------------------------------------------------
ESTADOS_MATRICULA = ("ACTIVA", "PENDIENTE", "FINALIZADA", "CANCELADA")

ACCIONES_LOG = {
    "registro": "Registro de usuario",
    "login": "Inicio de sesión",
    "login_fallido": "Login fallido",
    "logout": "Cierre de sesión",
    "estudiante_creado": "Estudiante creado",
    "estudiante_editado": "Estudiante editado",
    "estudiante_eliminado": "Estudiante eliminado",
    "carrera_creada": "Carrera creada",
    "curso_creado": "Curso creado",
    "matricula_creada": "Matrícula creada",
    "matricula_eliminada": "Matrícula eliminada",
    "nota_actualizada": "Nota actualizada",
    "preferencias_actualizadas": "Preferencias actualizadas",
}

TONOS_LOG = {
    "login": "success",
    "login_fallido": "danger",
    "logout": "secondary",
    "registro": "info",
    "estudiante_creado": "primary",
    "estudiante_editado": "primary",
    "estudiante_eliminado": "danger",
    "carrera_creada": "primary",
    "curso_creado": "primary",
    "matricula_creada": "success",
    "matricula_eliminada": "danger",
    "nota_actualizada": "warning",
    "preferencias_actualizadas": "secondary",
}


# ---------------------------------------------------------------------------
# Utilidades de plantillas y preferencias
# ---------------------------------------------------------------------------
def preferencias_actuales():
    """Preferencias del usuario en sesión, cacheadas durante la petición.

    Se guardan en flask.g para no consultar MongoDB dos veces en la misma
    petición (una para la ruta y otra para el tema de la plantilla).
    """
    if "prefs" not in g:
        g.prefs = obtener_preferencias(session.get("username", "anónimo"))
    return g.prefs


@app.context_processor
def inyectar_contexto():
    """Variables disponibles en todas las plantillas."""
    prefs = preferencias_actuales() if "usuario_id" in session else {
        "tema": "claro", "idioma": "es", "registros_por_pagina": 10
    }
    return {
        "prefs": prefs,
        "hoy": date.today(),
        "valor_credito": Config.VALOR_CREDITO,
        "acciones_log": ACCIONES_LOG,
        "url_pagina": url_pagina,
        "backend_nosql": Config.NOSQL_BACKEND,
    }


@app.template_filter("moneda")
def filtro_moneda(valor):
    """Formatea 4300000 como $4.300.000."""
    return formatear_moneda(valor)


@app.template_filter("fecha")
def filtro_fecha(valor):
    """Formatea una fecha como dd/mm/aaaa."""
    if not valor:
        return "—"
    if isinstance(valor, (datetime, date)):
        return valor.strftime("%d/%m/%Y")
    return str(valor)


@app.template_filter("iso")
def filtro_iso(valor):
    """Devuelve una fecha en formato AAAA-MM-DD para los input type=date."""
    if not valor:
        return ""
    if isinstance(valor, (datetime, date)):
        return valor.strftime("%Y-%m-%d")
    return str(valor)


@app.template_filter("fecha_hora")
def filtro_fecha_hora(valor):
    """Formatea una fecha y hora como dd/mm/aaaa hh:mm (UTC)."""
    if not valor:
        return "—"
    if isinstance(valor, datetime):
        return valor.strftime("%d/%m/%Y %H:%M")
    return str(valor)


def url_pagina(numero):
    """Construye la URL de una página conservando los filtros de la URL."""
    argumentos = request.args.to_dict()
    argumentos["pagina"] = numero
    return url_for(request.endpoint, **argumentos)


def paginar(total, pagina, por_pagina):
    """Calcula los datos de paginación que consume la plantilla."""
    paginas = max(1, math.ceil(total / por_pagina))
    pagina = min(max(1, pagina), paginas)
    desde = (pagina - 1) * por_pagina
    return {
        "total": total,
        "pagina": pagina,
        "paginas": paginas,
        "por_pagina": por_pagina,
        "offset": desde,
        "desde": desde + 1 if total else 0,
        "hasta": min(desde + por_pagina, total),
        "anterior": pagina - 1 if pagina > 1 else None,
        "siguiente": pagina + 1 if pagina < paginas else None,
        "ventana": list(range(max(1, pagina - 2), min(paginas, pagina + 2) + 1)),
    }


# ---------------------------------------------------------------------------
# Seguridad: cabeceras HTTP básicas en todas las respuestas
# ---------------------------------------------------------------------------
@app.after_request
def cabeceras_seguridad(respuesta):
    respuesta.headers.setdefault("X-Content-Type-Options", "nosniff")
    respuesta.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    respuesta.headers.setdefault("Referrer-Policy", "same-origin")
    return respuesta


# ---------------------------------------------------------------------------
# Panel principal
# ---------------------------------------------------------------------------
@app.route("/")
@login_required
def dashboard():
    """Panel con los indicadores generales del sistema."""
    totales = {
        "estudiantes": consultar(
            "SELECT COUNT(*) AS total FROM ESTUDIANTE", uno=True)["total"],
        "cursos": consultar(
            "SELECT COUNT(*) AS total FROM CURSO", uno=True)["total"],
        "matriculas_activas": consultar(
            "SELECT COUNT(*) AS total FROM MATRICULA WHERE Estado = 'ACTIVA'",
            uno=True)["total"],
        "recaudo": consultar(
            "SELECT COALESCE(SUM(Valor), 0) AS total FROM MATRICULA "
            "WHERE Estado = 'ACTIVA'", uno=True)["total"],
    }

    # Estudiantes por carrera (para el gráfico de barras horizontal).
    carreras = consultar(
        """SELECT c.NombreCarrera, COUNT(e.IdEstudiante) AS Total
           FROM CARRERA c
           LEFT JOIN ESTUDIANTE e ON e.IdCarrera = c.IdCarrera
           GROUP BY c.IdCarrera, c.NombreCarrera
           ORDER BY Total DESC, c.NombreCarrera"""
    )
    maximo = max((fila["Total"] for fila in carreras), default=0)
    for fila in carreras:
        fila["Porcentaje"] = round((fila["Total"] / maximo) * 100) if maximo else 0

    # Matrículas agrupadas por estado.
    estados = consultar(
        """SELECT Estado, COUNT(*) AS Total, COALESCE(SUM(Valor), 0) AS Recaudo
           FROM MATRICULA
           GROUP BY Estado
           ORDER BY Total DESC"""
    )
    total_matriculas = sum(fila["Total"] for fila in estados) or 1
    for fila in estados:
        fila["Porcentaje"] = round((fila["Total"] / total_matriculas) * 100)

    # Promedio general de notas registradas.
    promedio = consultar(
        """SELECT ROUND(AVG(NotaFinal), 2) AS Promedio,
                  COUNT(NotaFinal) AS Calificadas
           FROM DETALLE_MATRICULA""",
        uno=True,
    )

    ultimos_logs = obtener_logs(limite=6)

    return render_template(
        "dashboard.html",
        totales=totales,
        carreras=carreras,
        estados=estados,
        promedio=promedio,
        ultimos_logs=ultimos_logs,
        tonos=TONOS_LOG,
    )


# ---------------------------------------------------------------------------
# CRUD de estudiantes
# ---------------------------------------------------------------------------
@app.route("/estudiantes")
@login_required
def listar_estudiantes():
    """Lista los estudiantes con búsqueda y paginación."""
    busqueda = request.args.get("q", "").strip()[:100]
    patron = patron_like(busqueda)
    por_pagina = preferencias_actuales()["registros_por_pagina"]
    pagina = entero(request.args.get("pagina"), 1, minimo=1)

    # La condición es fija; los valores del usuario viajan como parámetros.
    filtro = """WHERE (%s = ''
                     OR CONCAT_WS(' ', e.PrimerNombre, e.SegundoNombre,
                                     e.PrimerApellido, e.SegundoApellido) LIKE %s
                     OR e.CorreoElectronico LIKE %s
                     OR CAST(e.IdEstudiante AS CHAR) LIKE %s)"""
    params_filtro = (busqueda, patron, patron, patron)

    total = consultar(
        f"SELECT COUNT(*) AS total FROM ESTUDIANTE e {filtro}",
        params_filtro, uno=True,
    )["total"]
    paginacion = paginar(total, pagina, por_pagina)

    estudiantes = consultar(
        f"""SELECT e.IdEstudiante, e.PrimerNombre, e.SegundoNombre,
                  e.PrimerApellido, e.SegundoApellido, e.CorreoElectronico,
                  e.NumeroTel, e.FechaNacimiento, e.IdCarrera,
                  c.NombreCarrera,
                  TIMESTAMPDIFF(YEAR, e.FechaNacimiento, CURDATE()) AS Edad,
                  (SELECT COUNT(*) FROM MATRICULA m
                    WHERE m.IdEstudiante = e.IdEstudiante) AS Matriculas
           FROM ESTUDIANTE e
           JOIN CARRERA c ON c.IdCarrera = e.IdCarrera
           {filtro}
           ORDER BY e.PrimerApellido, e.PrimerNombre
           LIMIT %s OFFSET %s""",
        params_filtro + (paginacion["por_pagina"], paginacion["offset"]),
    )

    return render_template(
        "estudiantes.html",
        estudiantes=estudiantes,
        busqueda=busqueda,
        paginacion=paginacion,
    )


def _leer_formulario_estudiante():
    """Lee y valida los datos del formulario de estudiante.

    Retorna (datos, errores, fecha_nacimiento, id_carrera). Si hay errores, la
    ruta vuelve a mostrar el formulario conservando lo que escribió el usuario.
    """
    datos = {
        "PrimerNombre": request.form.get("PrimerNombre", "").strip()[:50],
        "SegundoNombre": request.form.get("SegundoNombre", "").strip()[:50],
        "PrimerApellido": request.form.get("PrimerApellido", "").strip()[:50],
        "SegundoApellido": request.form.get("SegundoApellido", "").strip()[:50],
        "NumeroTel": request.form.get("NumeroTel", "").strip()[:20],
        "CorreoElectronico": request.form.get("CorreoElectronico", "").strip()[:100],
        "Direccion": request.form.get("Direccion", "").strip()[:50],
        "FechaNacimiento": request.form.get("FechaNacimiento", "").strip(),
        "IdCarrera": request.form.get("IdCarrera", "").strip(),
    }
    errores = []

    if len(datos["PrimerNombre"]) < 2:
        errores.append("El primer nombre es obligatorio (mínimo 2 caracteres).")
    if len(datos["PrimerApellido"]) < 2:
        errores.append("El primer apellido es obligatorio (mínimo 2 caracteres).")
    if not correo_valido(datos["CorreoElectronico"]):
        errores.append("El correo electrónico no tiene un formato válido.")
    if datos["NumeroTel"] and not telefono_valido(datos["NumeroTel"]):
        errores.append("El número de teléfono no es válido (solo números, "
                       "espacios, '+', '-' y paréntesis).")

    fecha_nacimiento = None
    try:
        fecha_nacimiento = datetime.strptime(datos["FechaNacimiento"], "%Y-%m-%d").date()
        if fecha_nacimiento > date.today():
            errores.append("La fecha de nacimiento no puede ser futura.")
        elif fecha_nacimiento < date(1900, 1, 1):
            errores.append("La fecha de nacimiento no es válida.")
    except ValueError:
        errores.append("Debes indicar una fecha de nacimiento válida.")

    id_carrera = entero(datos["IdCarrera"], 0)
    if not id_carrera:
        errores.append("Debes seleccionar una carrera.")
    elif not consultar("SELECT IdCarrera FROM CARRERA WHERE IdCarrera = %s",
                       (id_carrera,), uno=True):
        errores.append("La carrera seleccionada no existe.")

    return datos, errores, fecha_nacimiento, id_carrera


def _carreras_para_formulario():
    """Carreras ordenadas para el <select> del formulario."""
    return consultar("SELECT IdCarrera, NombreCarrera FROM CARRERA "
                     "ORDER BY NombreCarrera")


@app.route("/estudiantes/nuevo", methods=["GET", "POST"])
@login_required
def crear_estudiante():
    """Crea un estudiante nuevo."""
    if request.method == "POST":
        datos, errores, fecha_nacimiento, id_carrera = _leer_formulario_estudiante()
        if errores:
            for error in errores:
                flash(error, "danger")
            return render_template("estudiante_form.html", titulo="Nuevo estudiante",
                                   form=datos, carreras=_carreras_para_formulario()), 400

        try:
            nuevo_id = ejecutar(
                """INSERT INTO ESTUDIANTE
                   (PrimerNombre, SegundoNombre, PrimerApellido, SegundoApellido,
                    NumeroTel, CorreoElectronico, Direccion, FechaNacimiento, IdCarrera)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    datos["PrimerNombre"], datos["SegundoNombre"] or None,
                    datos["PrimerApellido"], datos["SegundoApellido"] or None,
                    datos["NumeroTel"] or None, datos["CorreoElectronico"],
                    datos["Direccion"] or None, fecha_nacimiento, id_carrera,
                ),
            )
        except IntegrityError:
            flash("Ya existe un estudiante registrado con ese correo electrónico.",
                  "danger")
            return render_template("estudiante_form.html", titulo="Nuevo estudiante",
                                   form=datos, carreras=_carreras_para_formulario()), 409

        registrar_log(
            session["username"], "estudiante_creado",
            f"Estudiante #{nuevo_id}: {datos['PrimerNombre']} "
            f"{datos['PrimerApellido']} ({datos['CorreoElectronico']})",
            ip_cliente(),
        )
        flash(f"Estudiante {datos['PrimerNombre']} {datos['PrimerApellido']} "
              "registrado correctamente.", "success")
        return redirect(url_for("listar_estudiantes"))

    return render_template(
        "estudiante_form.html",
        titulo="Nuevo estudiante",
        form={},
        carreras=_carreras_para_formulario(),
    )


@app.route("/estudiantes/<int:estudiante_id>/editar", methods=["GET", "POST"])
@login_required
def editar_estudiante(estudiante_id):
    """Edita los datos de un estudiante existente."""
    estudiante = consultar(
        """SELECT IdEstudiante, PrimerNombre, SegundoNombre, PrimerApellido,
                  SegundoApellido, NumeroTel, CorreoElectronico, Direccion,
                  FechaNacimiento, IdCarrera
           FROM ESTUDIANTE WHERE IdEstudiante = %s""",
        (estudiante_id,), uno=True,
    )
    if not estudiante:
        abort(404)

    if request.method == "POST":
        datos, errores, fecha_nacimiento, id_carrera = _leer_formulario_estudiante()
        if errores:
            for error in errores:
                flash(error, "danger")
            return render_template(
                "estudiante_form.html", titulo="Editar estudiante",
                form=datos, estudiante_id=estudiante_id,
                carreras=_carreras_para_formulario(),
            ), 400

        try:
            ejecutar(
                """UPDATE ESTUDIANTE
                   SET PrimerNombre = %s, SegundoNombre = %s,
                       PrimerApellido = %s, SegundoApellido = %s,
                       NumeroTel = %s, CorreoElectronico = %s,
                       Direccion = %s, FechaNacimiento = %s, IdCarrera = %s
                   WHERE IdEstudiante = %s""",
                (
                    datos["PrimerNombre"], datos["SegundoNombre"] or None,
                    datos["PrimerApellido"], datos["SegundoApellido"] or None,
                    datos["NumeroTel"] or None, datos["CorreoElectronico"],
                    datos["Direccion"] or None, fecha_nacimiento, id_carrera,
                    estudiante_id,
                ),
            )
        except IntegrityError:
            flash("Otro estudiante ya tiene ese correo electrónico.", "danger")
            return render_template(
                "estudiante_form.html", titulo="Editar estudiante",
                form=datos, estudiante_id=estudiante_id,
                carreras=_carreras_para_formulario(),
            ), 409

        registrar_log(
            session["username"], "estudiante_editado",
            f"Estudiante #{estudiante_id}: {datos['PrimerNombre']} "
            f"{datos['PrimerApellido']}",
            ip_cliente(),
        )
        flash("Datos del estudiante actualizados.", "success")
        return redirect(url_for("listar_estudiantes"))

    return render_template(
        "estudiante_form.html",
        titulo="Editar estudiante",
        form=estudiante,
        estudiante_id=estudiante_id,
        carreras=_carreras_para_formulario(),
    )


@app.route("/estudiantes/<int:estudiante_id>/eliminar", methods=["POST"])
@login_required
def eliminar_estudiante(estudiante_id):
    """Elimina un estudiante si no tiene matrículas asociadas."""
    estudiante = consultar(
        """SELECT IdEstudiante, PrimerNombre, PrimerApellido
           FROM ESTUDIANTE WHERE IdEstudiante = %s""",
        (estudiante_id,), uno=True,
    )
    if not estudiante:
        abort(404)

    try:
        ejecutar("DELETE FROM ESTUDIANTE WHERE IdEstudiante = %s", (estudiante_id,))
    except IntegrityError:
        # La llave foránea usa ON DELETE RESTRICT: primero hay que eliminar
        # las matrículas del estudiante (demostración de integridad referencial).
        flash("No se puede eliminar el estudiante porque tiene matrículas "
              "registradas. Elimina primero sus matrículas.", "danger")
        return redirect(url_for("listar_estudiantes"))

    registrar_log(
        session["username"], "estudiante_eliminado",
        f"Estudiante #{estudiante_id}: {estudiante['PrimerNombre']} "
        f"{estudiante['PrimerApellido']}",
        ip_cliente(),
    )
    flash("Estudiante eliminado correctamente.", "success")
    return redirect(url_for("listar_estudiantes"))


# ---------------------------------------------------------------------------
# Carreras
# ---------------------------------------------------------------------------
@app.route("/carreras", methods=["GET", "POST"])
@login_required
def carreras():
    """Lista las carreras y permite crear una nueva."""
    if request.method == "POST":
        nombre = request.form.get("NombreCarrera", "").strip()[:100]
        if len(nombre) < 3:
            flash("El nombre de la carrera es obligatorio (mínimo 3 caracteres).",
                  "danger")
            return redirect(url_for("carreras"))

        existente = consultar(
            "SELECT IdCarrera FROM CARRERA WHERE LOWER(NombreCarrera) = LOWER(%s)",
            (nombre,), uno=True,
        )
        if existente:
            flash("Ya existe una carrera con ese nombre.", "warning")
            return redirect(url_for("carreras"))

        nuevo_id = ejecutar(
            "INSERT INTO CARRERA (NombreCarrera) VALUES (%s)", (nombre,)
        )
        registrar_log(session["username"], "carrera_creada",
                      f"Carrera #{nuevo_id}: {nombre}", ip_cliente())
        flash(f"Carrera «{nombre}» creada correctamente.", "success")
        return redirect(url_for("carreras"))

    listado = consultar(
        """SELECT c.IdCarrera, c.NombreCarrera,
                  COUNT(e.IdEstudiante) AS Estudiantes
           FROM CARRERA c
           LEFT JOIN ESTUDIANTE e ON e.IdCarrera = c.IdCarrera
           GROUP BY c.IdCarrera, c.NombreCarrera
           ORDER BY c.NombreCarrera"""
    )
    return render_template("carreras.html", carreras=listado)


# ---------------------------------------------------------------------------
# Cursos
# ---------------------------------------------------------------------------
@app.route("/cursos", methods=["GET", "POST"])
@login_required
def cursos():
    """Lista los cursos y permite registrar uno nuevo."""
    if request.method == "POST":
        nombre = request.form.get("NombreCurso", "").strip()[:100]
        periodo = request.form.get("PeriodoAcademico", "").strip()[:10]
        cupos = entero(request.form.get("Cupos"), 0)
        id_materia = entero(request.form.get("IdMateria"), 0)
        aula = request.form.get("Aula", "").strip()[:30]
        horario = request.form.get("Horario", "").strip()[:100]
        id_profesor = entero(request.form.get("IdProfesor"), 0)

        errores = []
        if len(nombre) < 3:
            errores.append("El nombre del curso es obligatorio (mínimo 3 caracteres).")
        if not (len(periodo) == 6 and periodo[4] == "-" and periodo[:4].isdigit()
                and periodo[5] in "12"):
            errores.append("El periodo debe tener el formato AAAA-1 o AAAA-2.")
        if not 1 <= cupos <= 200:
            errores.append("Los cupos deben estar entre 1 y 200.")
        if not consultar("SELECT IdMateria FROM MATERIA WHERE IdMateria = %s",
                         (id_materia,), uno=True):
            errores.append("Debes seleccionar una materia válida.")
        if not aula:
            errores.append("El aula es obligatoria.")
        if len(horario) < 3:
            errores.append("El horario es obligatorio.")
        if id_profesor and not consultar(
            "SELECT IdProfesor FROM PROFESOR WHERE IdProfesor = %s",
            (id_profesor,), uno=True,
        ):
            errores.append("El profesor seleccionado no existe.")

        if errores:
            for error in errores:
                flash(error, "danger")
            return redirect(url_for("cursos"))

        # CURSO y PROFESOR_CURSO deben insertarse juntos (transacción).
        with transaccion() as conexion:
            nuevo_id = ejecutar_en(
                conexion,
                """INSERT INTO CURSO
                   (NombreCurso, PeriodoAcademico, Cupos, IdMateria, Aula, Horario)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (nombre, periodo, cupos, id_materia, aula, horario),
            )
            if id_profesor:
                ejecutar_en(
                    conexion,
                    "INSERT INTO PROFESOR_CURSO (IdProfesor, IdCurso) VALUES (%s, %s)",
                    (id_profesor, nuevo_id),
                )

        registrar_log(session["username"], "curso_creado",
                      f"Curso #{nuevo_id}: {nombre} ({periodo})", ip_cliente())
        flash(f"Curso «{nombre}» creado correctamente.", "success")
        return redirect(url_for("cursos"))

    listado = consultar(
        """SELECT cu.IdCurso, cu.NombreCurso, cu.PeriodoAcademico, cu.Cupos,
                  cu.Aula, cu.Horario, ma.NombreMateria, ma.Creditos,
                  ca.NombreCarrera,
                  GROUP_CONCAT(DISTINCT CONCAT(p.PrimerNombre, ' ',
                                               p.PrimerApellido)
                               SEPARATOR ', ') AS Profesores,
                  (SELECT COUNT(*)
                     FROM DETALLE_MATRICULA d
                     JOIN MATRICULA m ON m.IdMatricula = d.IdMatricula
                    WHERE d.IdCurso = cu.IdCurso
                      AND m.Estado = 'ACTIVA') AS Inscritos
           FROM CURSO cu
           JOIN MATERIA ma ON ma.IdMateria = cu.IdMateria
           JOIN CARRERA ca ON ca.IdCarrera = ma.IdCarrera
           LEFT JOIN PROFESOR_CURSO pc ON pc.IdCurso = cu.IdCurso
           LEFT JOIN PROFESOR p ON p.IdProfesor = pc.IdProfesor
           GROUP BY cu.IdCurso, cu.NombreCurso, cu.PeriodoAcademico, cu.Cupos,
                    cu.Aula, cu.Horario, ma.NombreMateria, ma.Creditos,
                    ca.NombreCarrera
           ORDER BY cu.PeriodoAcademico DESC, cu.NombreCurso"""
    )
    for curso in listado:
        curso["Disponibles"] = max(0, curso["Cupos"] - curso["Inscritos"])
        curso["Ocupacion"] = (
            round((curso["Inscritos"] / curso["Cupos"]) * 100)
            if curso["Cupos"] else 0
        )

    materias = consultar(
        """SELECT m.IdMateria, m.NombreMateria, m.Creditos, m.Semestre,
                  c.NombreCarrera
           FROM MATERIA m
           JOIN CARRERA c ON c.IdCarrera = m.IdCarrera
           ORDER BY c.NombreCarrera, m.Semestre, m.NombreMateria"""
    )
    profesores = consultar(
        """SELECT IdProfesor, PrimerNombre, PrimerApellido
           FROM PROFESOR ORDER BY PrimerApellido, PrimerNombre"""
    )
    return render_template(
        "cursos.html", cursos=listado, materias=materias, profesores=profesores
    )


# ---------------------------------------------------------------------------
# Matrículas (relación N:M entre estudiantes y cursos)
# ---------------------------------------------------------------------------
@app.route("/matriculas")
@login_required
def matriculas():
    """Lista las matrículas con sus cursos (JOIN de varias tablas)."""
    busqueda = request.args.get("q", "").strip()[:100]
    estado = request.args.get("estado", "").strip().upper()
    if estado not in ESTADOS_MATRICULA:
        estado = ""
    patron = patron_like(busqueda)
    por_pagina = preferencias_actuales()["registros_por_pagina"]
    pagina = entero(request.args.get("pagina"), 1, minimo=1)

    # Filtros fijos con marcadores %s; nada de texto del usuario en el SQL.
    filtro = """WHERE (%s = ''
                     OR CONCAT_WS(' ', e.PrimerNombre, e.SegundoNombre,
                                     e.PrimerApellido, e.SegundoApellido) LIKE %s
                     OR e.CorreoElectronico LIKE %s)
                     AND (%s = '' OR m.Estado = %s)"""
    params = (busqueda, patron, patron, estado, estado)

    total = consultar(
        f"""SELECT COUNT(*) AS total
            FROM MATRICULA m
            JOIN ESTUDIANTE e ON e.IdEstudiante = m.IdEstudiante
            {filtro}""",
        params, uno=True,
    )["total"]
    paginacion = paginar(total, pagina, por_pagina)

    listado = consultar(
        f"""SELECT m.IdMatricula, m.Fecha, m.Estado, m.Valor, m.IdEstudiante,
                   CONCAT_WS(' ', e.PrimerNombre, e.SegundoNombre,
                                  e.PrimerApellido, e.SegundoApellido) AS Estudiante,
                   e.CorreoElectronico
            FROM MATRICULA m
            JOIN ESTUDIANTE e ON e.IdEstudiante = m.IdEstudiante
            {filtro}
            ORDER BY m.Fecha DESC, m.IdMatricula DESC
            LIMIT %s OFFSET %s""",
        params + (paginacion["por_pagina"], paginacion["offset"]),
    )

    # Segunda consulta para los cursos de las matrículas de esta página
    # (evita el problema N+1 de consultar dentro de un bucle).
    detalles = {}
    if listado:
        ids = [fila["IdMatricula"] for fila in listado]
        marcadores = ", ".join(["%s"] * len(ids))  # solo marcadores, no valores
        filas = consultar(
            f"""SELECT d.IdMatricula, d.IdCurso, d.NotaFinal,
                       d.Estado AS EstadoDetalle, cu.NombreCurso,
                       cu.PeriodoAcademico, ma.NombreMateria, ma.Creditos
                FROM DETALLE_MATRICULA d
                JOIN CURSO cu ON cu.IdCurso = d.IdCurso
                JOIN MATERIA ma ON ma.IdMateria = cu.IdMateria
                WHERE d.IdMatricula IN ({marcadores})
                ORDER BY cu.NombreCurso""",
            tuple(ids),
        )
        for fila in filas:
            detalles.setdefault(fila["IdMatricula"], []).append(fila)

    for matricula in listado:
        matricula["Detalles"] = detalles.get(matricula["IdMatricula"], [])

    estudiantes = consultar(
        """SELECT IdEstudiante, PrimerNombre, PrimerApellido, CorreoElectronico
           FROM ESTUDIANTE ORDER BY PrimerApellido, PrimerNombre"""
    )
    cursos = consultar(
        """SELECT cu.IdCurso, cu.NombreCurso, cu.Cupos, cu.PeriodoAcademico,
                  ma.NombreMateria, ma.Creditos, ca.NombreCarrera,
                  (SELECT COUNT(*)
                     FROM DETALLE_MATRICULA d
                     JOIN MATRICULA m ON m.IdMatricula = d.IdMatricula
                    WHERE d.IdCurso = cu.IdCurso
                      AND m.Estado = 'ACTIVA') AS Inscritos
           FROM CURSO cu
           JOIN MATERIA ma ON ma.IdMateria = cu.IdMateria
           JOIN CARRERA ca ON ca.IdCarrera = ma.IdCarrera
           ORDER BY ca.NombreCarrera, cu.NombreCurso"""
    )

    return render_template(
        "matriculas.html",
        matriculas=listado,
        estudiantes=estudiantes,
        cursos=cursos,
        busqueda=busqueda,
        estado=estado,
        estados=ESTADOS_MATRICULA,
        paginacion=paginacion,
    )


@app.route("/matriculas/nueva", methods=["POST"])
@login_required
def crear_matricula():
    """Registra una matrícula (MATRICULA + DETALLE_MATRICULA) con validaciones."""
    id_estudiante = entero(request.form.get("IdEstudiante"), 0)
    id_curso = entero(request.form.get("IdCurso"), 0)
    estado = request.form.get("Estado", "ACTIVA").strip().upper()
    fecha_texto = request.form.get("Fecha", "").strip()
    valor_texto = request.form.get("Valor", "").strip()

    if estado not in ESTADOS_MATRICULA:
        estado = "ACTIVA"
    try:
        fecha = datetime.strptime(fecha_texto, "%Y-%m-%d").date()
    except ValueError:
        flash("La fecha de la matrícula no es válida.", "danger")
        return redirect(url_for("matriculas"))

    # ----------------------- Validaciones de negocio -----------------------
    estudiante = consultar(
        """SELECT IdEstudiante, CONCAT_WS(' ', PrimerNombre, PrimerApellido) AS Nombre
           FROM ESTUDIANTE WHERE IdEstudiante = %s""",
        (id_estudiante,), uno=True,
    )
    if not estudiante:
        flash("El estudiante seleccionado no existe.", "danger")
        return redirect(url_for("matriculas"))

    curso = consultar(
        """SELECT cu.IdCurso, cu.NombreCurso, cu.Cupos, ma.Creditos,
                  (SELECT COUNT(*)
                     FROM DETALLE_MATRICULA d
                     JOIN MATRICULA m ON m.IdMatricula = d.IdMatricula
                    WHERE d.IdCurso = cu.IdCurso
                      AND m.Estado = 'ACTIVA') AS Inscritos
           FROM CURSO cu
           JOIN MATERIA ma ON ma.IdMateria = cu.IdMateria
           WHERE cu.IdCurso = %s""",
        (id_curso,), uno=True,
    )
    if not curso:
        flash("El curso seleccionado no existe.", "danger")
        return redirect(url_for("matriculas"))

    duplicada = consultar(
        """SELECT m.IdMatricula
           FROM MATRICULA m
           JOIN DETALLE_MATRICULA d ON d.IdMatricula = m.IdMatricula
           WHERE m.IdEstudiante = %s AND d.IdCurso = %s
             AND m.Estado = 'ACTIVA'
           LIMIT 1""",
        (id_estudiante, id_curso), uno=True,
    )
    if duplicada:
        flash("El estudiante ya tiene una matrícula activa en ese curso.", "warning")
        return redirect(url_for("matriculas"))

    if curso["Inscritos"] >= curso["Cupos"]:
        flash(f"El curso «{curso['NombreCurso']}» no tiene cupos disponibles.", "warning")
        return redirect(url_for("matriculas"))

    # Si no se envía valor, se sugiere según los créditos de la materia.
    if valor_texto:
        valor = entero(valor_texto.replace(".", "").replace(",", ""), -1)
        if valor < 0:
            flash("El valor de la matrícula no es válido.", "danger")
            return redirect(url_for("matriculas"))
    else:
        valor = curso["Creditos"] * Config.VALOR_CREDITO

    # ------------------ Inserción atómica (transacción) --------------------
    with transaccion() as conexion:
        id_matricula = ejecutar_en(
            conexion,
            """INSERT INTO MATRICULA (Fecha, Estado, IdEstudiante, Valor)
               VALUES (%s, %s, %s, %s)""",
            (fecha, estado, id_estudiante, valor),
        )
        ejecutar_en(
            conexion,
            """INSERT INTO DETALLE_MATRICULA
               (IdMatricula, IdCurso, NotaFinal, Estado)
               VALUES (%s, %s, NULL, 'PENDIENTE')""",
            (id_matricula, id_curso),
        )

    registrar_log(
        session["username"], "matricula_creada",
        f"Matrícula #{id_matricula}: {estudiante['Nombre']} -> "
        f"{curso['NombreCurso']} ({formatear_moneda(valor)})",
        ip_cliente(),
    )
    flash(f"Matrícula #{id_matricula} registrada: {estudiante['Nombre']} en "
          f"«{curso['NombreCurso']}».", "success")
    return redirect(url_for("matriculas"))


@app.route("/matriculas/<int:matricula_id>/nota", methods=["POST"])
@login_required
def actualizar_nota(matricula_id):
    """Actualiza la nota final de un curso dentro de una matrícula."""
    id_curso = entero(request.form.get("IdCurso"), 0)
    nota_texto = request.form.get("Nota", "").strip().replace(",", ".")

    try:
        nota = round(float(nota_texto), 2)
    except ValueError:
        flash("La nota debe ser un número entre 0.0 y 5.0.", "danger")
        return redirect(url_for("matriculas"))
    if not 0.0 <= nota <= 5.0:
        flash("La nota debe estar entre 0.0 y 5.0.", "danger")
        return redirect(url_for("matriculas"))

    estado = "APROBADO" if nota >= 3.0 else "REPROBADO"
    afectadas = ejecutar(
        """UPDATE DETALLE_MATRICULA
           SET NotaFinal = %s, Estado = %s
           WHERE IdMatricula = %s AND IdCurso = %s""",
        (nota, estado, matricula_id, id_curso),
    )
    if not afectadas:
        flash("No se encontró el curso indicado dentro de la matrícula.", "warning")
        return redirect(url_for("matriculas"))

    registrar_log(
        session["username"], "nota_actualizada",
        f"Matrícula #{matricula_id}, curso #{id_curso}: nota {nota:.2f} ({estado})",
        ip_cliente(),
    )
    flash(f"Nota actualizada a {nota:.2f}. Estado: {estado.lower()}.", "success")
    return redirect(url_for("matriculas"))


@app.route("/matriculas/<int:matricula_id>/eliminar", methods=["POST"])
@login_required
def eliminar_matricula(matricula_id):
    """Elimina una matrícula. El DETALLE se borra en cascada (ON DELETE CASCADE)."""
    matricula = consultar(
        """SELECT m.IdMatricula, m.Valor,
                  CONCAT_WS(' ', e.PrimerNombre, e.PrimerApellido) AS Estudiante
           FROM MATRICULA m
           JOIN ESTUDIANTE e ON e.IdEstudiante = m.IdEstudiante
           WHERE m.IdMatricula = %s""",
        (matricula_id,), uno=True,
    )
    if not matricula:
        abort(404)

    ejecutar("DELETE FROM MATRICULA WHERE IdMatricula = %s", (matricula_id,))

    registrar_log(
        session["username"], "matricula_eliminada",
        f"Matrícula #{matricula_id} de {matricula['Estudiante']} "
        f"({formatear_moneda(matricula['Valor'])})",
        ip_cliente(),
    )
    flash(f"Matrícula #{matricula_id} eliminada junto con su detalle "
          "(borrado en cascada).", "success")
    return redirect(url_for("matriculas"))


# ---------------------------------------------------------------------------
# Preferencias (MongoDB)
# ---------------------------------------------------------------------------
@app.route("/preferencias", methods=["GET", "POST"])
@login_required
def preferencias():
    """Lee y actualiza las preferencias del usuario en MongoDB."""
    if request.method == "POST":
        tema = request.form.get("tema", "claro").strip().lower()
        idioma = request.form.get("idioma", "es").strip().lower()
        registros = entero(request.form.get("registros_por_pagina"), 0)

        if tema not in ("claro", "oscuro"):
            tema = "claro"
        if idioma not in ("es", "en"):
            idioma = "es"
        if not 5 <= registros <= 100:
            flash("Los registros por página deben estar entre 5 y 100.", "danger")
            return redirect(url_for("preferencias"))

        if guardar_preferencias(session["username"], tema, idioma, registros):
            registrar_log(
                session["username"], "preferencias_actualizadas",
                f"tema={tema}, idioma={idioma}, registros_por_pagina={registros}",
                ip_cliente(),
            )
            flash("Preferencias guardadas en MongoDB.", "success")
        else:
            flash("No se pudo conectar a MongoDB. Intenta de nuevo.", "danger")

        # El tema se aplica al recargar; se invalida la caché de la petición.
        g.pop("prefs", None)
        return redirect(url_for("preferencias"))

    return render_template(
        "preferencias.html",
        documento=obtener_documento_preferencias(session["username"]),
    )


# ---------------------------------------------------------------------------
# Logs de actividad (MongoDB)
# ---------------------------------------------------------------------------
@app.route("/logs")
@login_required
def ver_logs():
    """Muestra los últimos eventos registrados en MongoDB."""
    accion = request.args.get("accion", "").strip()
    if accion not in ACCIONES_LOG:
        accion = ""
    limite = entero(request.args.get("limite"), 50, minimo=10, maximo=200)
    if limite not in (10, 25, 50, 100, 200):
        limite = 50

    logs = obtener_logs(limite=limite, accion=accion or None)
    conteos = {fila["accion"]: fila["total"] for fila in contar_por_accion()}

    return render_template(
        "logs.html",
        logs=logs,
        accion=accion,
        limite=limite,
        conteos=conteos,
        total_eventos=contar_logs(),
        tonos=TONOS_LOG,
    )


# ---------------------------------------------------------------------------
# Perfil del usuario (demuestra que la contraseña está cifrada)
# ---------------------------------------------------------------------------
@app.route("/perfil")
@login_required
def perfil():
    """Muestra los datos de la cuenta y el hash almacenado en MySQL."""
    usuario = consultar(
        """SELECT IdUsuario, Username, NombreCompleto, PasswordHash, CreadoEn
           FROM USUARIO WHERE IdUsuario = %s""",
        (session["usuario_id"],), uno=True,
    )
    if not usuario:
        session.clear()
        flash("Tu cuenta ya no existe. Inicia sesión nuevamente.", "warning")
        return redirect(url_for("auth.login"))

    accesos = obtener_logs(limite=10, usuario=session["username"])
    return render_template("perfil.html", usuario=usuario, accesos=accesos,
                           tonos=TONOS_LOG)


# ---------------------------------------------------------------------------
# Manejo de errores
# ---------------------------------------------------------------------------
@app.errorhandler(404)
def no_encontrado(error):
    """Página mostrada cuando una ruta o un registro no existe."""
    return render_template(
        "error.html", codigo=404, titulo="Página no encontrada",
        mensaje="La dirección que buscas no existe o el registro fue eliminado.",
    ), 404


@app.errorhandler(500)
def error_interno(error):
    """Página mostrada ante un error inesperado del servidor."""
    return render_template(
        "error.html", codigo=500, titulo="Error interno",
        mensaje="Ocurrió un error inesperado. Revisa la consola del servidor.",
    ), 500


@app.errorhandler(ErrorBaseDatos)
def error_base_datos(error):
    """Captura los errores de MySQL y muestra una página amigable.

    Esto cumple el requisito de manejo de errores: la aplicación no se cae si
    la base de datos está apagada o mal configurada.
    """
    return render_template(
        "error.html", codigo=503, titulo="Sin conexión con MySQL",
        mensaje=str(error),
        sugerencia="Verifica que XAMPP/MySQL esté iniciado y que las "
                   "credenciales del archivo .env sean correctas.",
    ), 503


if __name__ == "__main__":
    # host 127.0.0.1: la aplicación solo escucha en el equipo local.
    app.run(host="127.0.0.1", port=5000, debug=Config.DEBUG)
