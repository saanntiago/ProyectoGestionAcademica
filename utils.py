"""utils.py
--------
Propósito:
    Funciones pequeñas compartidas por las rutas, la autenticación y las
    plantillas: validación de correos, conversión segura de números, formato de
    moneda y preparación de patrones LIKE.

Autor:  Santiago Duque
Curso:  Teoría de Bases de Datos
"""

import re

from flask import request

CORREO_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")
TELEFONO_RE = re.compile(r"^[0-9+\-()\s]{7,20}$")


def ip_cliente():
    """Devuelve la IP del visitante (útil para los logs de auditoría)."""
    reenviada = request.headers.get("X-Forwarded-For", "")
    ip = reenviada.split(",")[0].strip() if reenviada else (request.remote_addr or "")
    return ip[:45]


def correo_valido(correo):
    """Valida de forma básica el formato de un correo electrónico."""
    return bool(CORREO_RE.match(correo or "")) and len(correo) <= 100


def telefono_valido(telefono):
    """Permite números, espacios, paréntesis, '+' y '-'."""
    return bool(TELEFONO_RE.match(telefono or ""))


def entero(valor, por_defecto=0, minimo=None, maximo=None):
    """Convierte un valor a int sin lanzar excepciones y lo limita al rango.

    Se usa para parámetros de la URL (página, límite) que no son confiables.
    """
    try:
        numero = int(str(valor).strip())
    except (TypeError, ValueError):
        numero = por_defecto
    if minimo is not None:
        numero = max(minimo, numero)
    if maximo is not None:
        numero = min(maximo, numero)
    return numero


def patron_like(texto):
    """Escapa los comodines de LIKE (% y _) para que el texto del usuario se
    busque de forma literal y no como patrón.

    Ejemplo: si el usuario escribe "%' OR 1=1 --" se busca ese texto exacto y
    la consulta sigue siendo parametrizada (nunca se concatena al SQL).
    """
    limpio = texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{limpio}%"


def formatear_moneda(valor):
    """Devuelve un valor numérico como pesos colombianos: 4300000 -> $4.300.000."""
    if valor is None or valor == "":
        return "—"
    try:
        return "$" + f"{int(valor):,}".replace(",", ".")
    except (TypeError, ValueError):
        return "—"
