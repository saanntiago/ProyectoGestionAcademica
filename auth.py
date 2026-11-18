"""auth.py
-------
Propósito:
    Autenticación básica de usuarios:
      - Registro con contraseña cifrada mediante bcrypt (hash + salt).
      - Inicio y cierre de sesión usando la sesión firmada de Flask.
      - Decorador @login_required para proteger las rutas privadas.

SEGURIDAD:
    Las contraseñas NUNCA se guardan en texto plano. En la tabla USUARIO solo
    queda el hash bcrypt, que es irreversible y distinto para cada usuario
    aunque dos personas usen la misma contraseña (salt aleatorio).

Autor:  Santiago Duque
Curso:  Teoría de Bases de Datos
"""

import re
from functools import wraps

import bcrypt
from flask import (Blueprint, flash, redirect, render_template, request,
                   session, url_for)
from mysql.connector import IntegrityError

from db_mysql import consultar, ejecutar
from db_nosql import registrar_log
from utils import ip_cliente

auth_bp = Blueprint("auth", __name__)

# El nombre de usuario admite letras, números, punto, guion y guion bajo.
USUARIO_RE = re.compile(r"^[A-Za-z0-9._-]{3,30}$")

# Hash ficticio: cuando el usuario no existe se compara igual contra un hash
# para que el tiempo de respuesta sea similar y no se pueda deducir qué
# nombres de usuario están registrados (ataque de temporización).
_HASH_FICTICIO = bcrypt.hashpw(b"clave-ficticia-para-tiempo", bcrypt.gensalt())


def login_required(vista):
    """Decorador: si no hay sesión activa, redirige al formulario de login."""

    @wraps(vista)
    def envoltura(*args, **kwargs):
        if "usuario_id" not in session:
            flash("Debes iniciar sesión para continuar.", "warning")
            return redirect(url_for("auth.login"))
        return vista(*args, **kwargs)

    return envoltura


@auth_bp.route("/registro", methods=["GET", "POST"])
def registro():
    """Muestra el formulario de registro y crea la cuenta del usuario."""
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()[:100]
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirmacion = request.form.get("confirmacion", "")

        # ------------------------- Validaciones -------------------------
        if not USUARIO_RE.match(username):
            flash("El usuario debe tener entre 3 y 30 caracteres (letras, "
                  "números, punto, guion o guion bajo).", "danger")
            return render_template("registro.html"), 400

        # bcrypt solo considera los primeros 72 bytes de la contraseña.
        if len(password.encode("utf-8")) < 6:
            flash("La contraseña debe tener al menos 6 caracteres.", "danger")
            return render_template("registro.html"), 400

        if password != confirmacion:
            flash("Las contraseñas no coinciden.", "danger")
            return render_template("registro.html"), 400

        # bcrypt genera un salt aleatorio y lo incluye dentro del hash.
        password_hash = bcrypt.hashpw(
            password.encode("utf-8")[:72], bcrypt.gensalt(rounds=12)
        ).decode("utf-8")

        try:
            # Consulta parametrizada: los valores viajan separados del SQL.
            ejecutar(
                "INSERT INTO USUARIO (Username, PasswordHash, NombreCompleto) "
                "VALUES (%s, %s, %s)",
                (username, password_hash, nombre or username),
            )
        except IntegrityError:
            # La columna Username es UNIQUE en la base de datos.
            flash("Ese nombre de usuario ya está registrado. Elige otro.", "danger")
            return render_template("registro.html"), 409

        registrar_log(username, "registro", "Cuenta de usuario creada", ip_cliente())
        flash("Cuenta creada correctamente. Ya puedes iniciar sesión.", "success")
        return redirect(url_for("auth.login"))

    return render_template("registro.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Valida las credenciales y abre la sesión del usuario."""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        # Consulta parametrizada: aunque el usuario escriba  ' OR '1'='1  el
        # conector lo trata como texto y la consulta no devuelve filas.
        usuario = consultar(
            "SELECT IdUsuario, Username, PasswordHash, NombreCompleto "
            "FROM USUARIO WHERE Username = %s",
            (username,),
            uno=True,
        )

        password_bytes = password.encode("utf-8")[:72]
        if usuario:
            valido = bcrypt.checkpw(password_bytes, usuario["PasswordHash"].encode("utf-8"))
        else:
            # Comparación ficticia para mantener un tiempo de respuesta similar.
            bcrypt.checkpw(password_bytes, _HASH_FICTICIO)
            valido = False

        if not valido:
            registrar_log(
                username or "anónimo", "login_fallido",
                "Intento de inicio de sesión con credenciales incorrectas",
                ip_cliente(),
            )
            flash("Usuario o contraseña incorrectos.", "danger")
            return render_template("login.html"), 401

        # Evita fijación de sesión: se limpia cualquier dato anterior.
        session.clear()
        session.permanent = True
        session["usuario_id"] = usuario["IdUsuario"]
        session["username"] = usuario["Username"]
        session["nombre"] = usuario["NombreCompleto"] or usuario["Username"]

        registrar_log(usuario["Username"], "login", "Inicio de sesión correcto", ip_cliente())
        flash(f"Bienvenido, {session['nombre']}.", "success")
        return redirect(url_for("dashboard"))

    # Si ya hay sesión, no tiene sentido mostrar el formulario otra vez.
    if "usuario_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    """Cierra la sesión y registra el evento en MongoDB."""
    username = session.get("username")
    if username:
        registrar_log(username, "logout", "Cierre de sesión", ip_cliente())
    session.clear()
    flash("Sesión cerrada. ¡Hasta pronto!", "info")
    return redirect(url_for("auth.login"))
