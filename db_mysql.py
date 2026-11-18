"""db_mysql.py
-----------
Propósito:
    Conexión a MySQL (XAMPP/MariaDB) y funciones auxiliares para ejecutar SQL
    sobre la base de datos transaccional "bd_universidad".

REGLA DE SEGURIDAD DEL PROYECTO (prevención de inyección SQL, OWASP A03):
    Todas las consultas reciben los valores del usuario por separado en
    "params" (consultas parametrizadas con %s). El conector escapa cada valor,
    por lo que un texto como  ' OR '1'='1  se trata como un dato y nunca como
    código SQL.

    NUNCA se debe construir SQL concatenando texto del usuario:
        f"SELECT * FROM ESTUDIANTE WHERE CorreoElectronico = '{correo}'"  # ❌
        "SELECT * FROM ESTUDIANTE WHERE CorreoElectronico = %s", (correo,)  # ✅

Autor:  Santiago Duque
Curso:  Teoría de Bases de Datos
"""

from contextlib import contextmanager

import mysql.connector
from mysql.connector import errorcode

from config import Config


class ErrorBaseDatos(Exception):
    """Error controlado de MySQL con un mensaje listo para mostrar al usuario."""


# Mensajes amigables para los errores más comunes de conexión.
_MENSAJES = {
    errorcode.ER_ACCESS_DENIED_ERROR: (
        "Acceso denegado para el usuario de MySQL. "
        "Revisa MYSQL_USER y MYSQL_PASSWORD en el archivo .env."
    ),
    errorcode.ER_BAD_DB_ERROR: (
        "La base de datos indicada no existe. "
        "Ejecuta schema.sql o revisa MYSQL_DB en el archivo .env."
    ),
    errorcode.CR_CONN_HOST_ERROR: (
        "No se pudo conectar al servidor MySQL. "
        "Verifica que XAMPP/MySQL esté iniciado y que el puerto sea el correcto."
    ),
    errorcode.CR_CONNECTION_ERROR: (
        "No se pudo conectar al servidor MySQL. "
        "Verifica que XAMPP/MySQL esté iniciado."
    ),
    errorcode.CR_UNKNOWN_HOST: (
        "El servidor MySQL indicado no existe. Revisa MYSQL_HOST en el archivo .env."
    ),
}


def _mensaje(error):
    """Traduce un error del conector a un mensaje entendible para el usuario."""
    if isinstance(error, mysql.connector.IntegrityError):
        # Los errores de integridad se manejan en cada ruta para dar un
        # mensaje específico (correo duplicado, matrícula duplicada, etc.).
        return str(error)

    mensaje = _MENSAJES.get(error.errno)
    if mensaje:
        return mensaje

    if error.errno == errorcode.ER_NO_SUCH_TABLE:
        return ("Falta una tabla en la base de datos. "
                "Ejecuta nuevamente el archivo schema.sql.")

    return f"Error de MySQL ({error.errno}): {error.msg}"


def get_connection():
    """Abre y devuelve una nueva conexión a MySQL.

    Se usa una conexión por operación para no compartir cursores entre hilos
    (Flask puede atender varias peticiones al mismo tiempo).
    """
    try:
        return mysql.connector.connect(
            host=Config.MYSQL_HOST,
            port=Config.MYSQL_PORT,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            database=Config.MYSQL_DB,
            charset="utf8mb4",
            connection_timeout=5,
            autocommit=False,
        )
    except mysql.connector.Error as error:
        raise ErrorBaseDatos(_mensaje(error)) from error


def consultar(sql, params=(), uno=False):
    """Ejecuta un SELECT parametrizado y devuelve las filas.

    Parámetros:
        sql (str): sentencia con marcadores %s (nunca texto concatenado).
        params (tuple): valores que reemplazan cada %s.
        uno (bool): si es True devuelve solo la primera fila.

    Retorna:
        dict | None cuando uno=True; list[dict] en caso contrario.
    """
    conexion = get_connection()
    cursor = conexion.cursor(dictionary=True)
    try:
        cursor.execute(sql, params)
        return cursor.fetchone() if uno else cursor.fetchall()
    except mysql.connector.Error as error:
        raise ErrorBaseDatos(_mensaje(error)) from error
    finally:
        cursor.close()
        conexion.close()


def ejecutar(sql, params=()):
    """Ejecuta un INSERT, UPDATE o DELETE parametrizado y confirma (commit).

    Si ocurre un error revierte la transacción (rollback) y lo propaga para
    que la ruta decida qué mensaje mostrar.

    Retorna:
        int: id generado en un INSERT o número de filas afectadas.
    """
    conexion = get_connection()
    cursor = conexion.cursor()
    try:
        cursor.execute(sql, params)
        conexion.commit()
        return cursor.lastrowid or cursor.rowcount
    except mysql.connector.IntegrityError:
        # Se relanza sin envolver para que la ruta muestre un mensaje
        # específico (por ejemplo "ese correo ya está registrado").
        conexion.rollback()
        raise
    except mysql.connector.Error as error:
        conexion.rollback()
        raise ErrorBaseDatos(_mensaje(error)) from error
    finally:
        cursor.close()
        conexion.close()


def ejecutar_en(conexion, sql, params=()):
    """Ejecuta una sentencia dentro de una transacción ya abierta.

    Se usa junto con el context manager transaccion() para operaciones que
    deben ser atómicas, como registrar una MATRICULA y su DETALLE_MATRICULA.
    """
    cursor = conexion.cursor()
    try:
        cursor.execute(sql, params)
        return cursor.lastrowid or cursor.rowcount
    finally:
        cursor.close()


@contextmanager
def transaccion():
    """Context manager que agrupa varias sentencias en una sola transacción.

    Si todas terminan bien hace commit; si alguna falla hace rollback y
    propaga el error. Así nunca queda una matrícula sin su detalle.
    """
    conexion = get_connection()
    try:
        yield conexion
        conexion.commit()
    except mysql.connector.IntegrityError:
        conexion.rollback()
        raise
    except mysql.connector.Error as error:
        conexion.rollback()
        raise ErrorBaseDatos(_mensaje(error)) from error
    except Exception:
        conexion.rollback()
        raise
    finally:
        conexion.close()
