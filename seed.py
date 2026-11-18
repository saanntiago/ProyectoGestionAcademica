"""seed.py
-------
Propósito:
    Crear el usuario administrador de prueba la primera vez que se instala el
    proyecto. Es idempotente: si el usuario ya existe, no lo duplica.

    La contraseña se guarda con hash bcrypt, igual que en el formulario de
    registro. Nunca se almacena en texto plano.

Uso:
    python seed.py

Requisito:
    Haber ejecutado antes schema.sql (crea la tabla USUARIO).

Autor:  Santiago Duque
Curso:  Teoría de Bases de Datos
"""

import sys

import bcrypt

from db_mysql import ErrorBaseDatos, consultar, ejecutar

USUARIO = "admin"
CONTRASENA = "Admin123"
NOMBRE = "Administrador del sistema"


def main():
    """Crea el usuario admin si no existe y muestra las credenciales."""
    try:
        existente = consultar(
            "SELECT IdUsuario FROM USUARIO WHERE Username = %s",
            (USUARIO,), uno=True,
        )
        if existente:
            print(f"El usuario '{USUARIO}' ya existe. No se creó de nuevo.")
            return 0

        # gensalt(rounds=12) genera un salt aleatorio (12 iteraciones).
        password_hash = bcrypt.hashpw(
            CONTRASENA.encode("utf-8"), bcrypt.gensalt(rounds=12)
        ).decode("utf-8")

        ejecutar(
            "INSERT INTO USUARIO (Username, PasswordHash, NombreCompleto) "
            "VALUES (%s, %s, %s)",
            (USUARIO, password_hash, NOMBRE),
        )
    except ErrorBaseDatos as error:
        print(f"[ERROR] {error}")
        print("Verifica que XAMPP/MySQL esté iniciado y que hayas ejecutado "
              "schema.sql.")
        return 1

    print("=" * 58)
    print("  Usuario administrador creado correctamente")
    print("=" * 58)
    print(f"  Usuario:    {USUARIO}")
    print(f"  Contraseña: {CONTRASENA}")
    print("  (La contraseña queda guardada como hash bcrypt en MySQL)")
    print("=" * 58)
    return 0


if __name__ == "__main__":
    sys.exit(main())
