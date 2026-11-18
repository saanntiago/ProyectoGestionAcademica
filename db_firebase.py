"""db_firebase.py
--------------
Propósito:
    Alternativa a db_mongo.py usando Firebase (Cloud Firestore).

    Se activa poniendo NOSQL_BACKEND=firebase en el archivo .env. Ofrece
    exactamente las mismas funciones que db_mongo.py, por lo que el resto de la
    aplicación no cambia.

Requisitos:
    pip install firebase-admin
    Descargar la llave de servicio (JSON) desde la consola de Firebase:
    Configuración del proyecto > Cuentas de servicio > Generar nueva clave privada.
    Guardarla como firebase-key.json en la raíz del proyecto.

Autor:  Santiago Duque
Curso:  Teoría de Bases de Datos
"""

from datetime import datetime, timezone

import firebase_admin
from firebase_admin import credentials, firestore

from config import Config

PREFERENCIAS_POR_DEFECTO = {"tema": "claro", "idioma": "es", "registros_por_pagina": 10}

# Inicializa Firebase una sola vez aunque el módulo se importe varias veces.
if not firebase_admin._apps:  # atributo interno estable de firebase-admin
    firebase_admin.initialize_app(credentials.Certificate(Config.FIREBASE_CREDENTIALS))

_db = firestore.client()


def mongo_disponible():
    """Nombre conservado por compatibilidad: indica si la base NoSQL responde."""
    try:
        next(_db.collection("logs").limit(1).stream(), None)
        return True
    except Exception as error:
        print(f"[ADVERTENCIA] Firebase no responde: {error}")
        return False


def registrar_log(usuario, accion, detalle="", ip=""):
    """Agrega un documento a la colección "logs" de Firestore."""
    try:
        _db.collection("logs").add({
            "usuario": str(usuario)[:80],
            "accion": str(accion)[:50],
            "detalle": str(detalle)[:500],
            "ip": str(ip)[:45],
            "fecha": firestore.SERVER_TIMESTAMP,  # hora asignada por el servidor
        })
    except Exception as error:
        print(f"[ADVERTENCIA] No se pudo registrar el log en Firebase: {error}")


def obtener_logs(limite=100, accion=None, usuario=None):
    """Devuelve los últimos logs ordenados por fecha descendente.

    Firestore exige índices compuestos cuando se combinan filtros y order_by,
    por eso se filtra en Python sobre los últimos documentos leídos. Para el
    volumen de este proyecto (decenas de eventos) es más que suficiente.
    """
    try:
        consulta = (
            _db.collection("logs")
            .order_by("fecha", direction=firestore.Query.DESCENDING)
            .limit(int(limite) if not (accion or usuario) else 500)
        )
        registros = [documento.to_dict() for documento in consulta.stream()]
    except Exception as error:
        print(f"[ADVERTENCIA] No se pudieron leer los logs: {error}")
        return []

    registros = [r for r in registros if r.get("fecha") is not None]
    if accion:
        registros = [r for r in registros if r.get("accion") == str(accion)]
    if usuario:
        registros = [r for r in registros if r.get("usuario") == str(usuario)]
    return registros[:int(limite)]


def contar_logs():
    """Cuenta los documentos de la colección logs."""
    try:
        return sum(1 for _ in _db.collection("logs").stream())
    except Exception as error:
        print(f"[ADVERTENCIA] No se pudieron contar los logs: {error}")
        return 0


def contar_por_accion():
    """Agrupa los logs por acción (se hace en Python para evitar índices)."""
    totales = {}
    try:
        for documento in _db.collection("logs").stream():
            accion = documento.to_dict().get("accion", "desconocida")
            totales[accion] = totales.get(accion, 0) + 1
    except Exception as error:
        print(f"[ADVERTENCIA] No se pudo agrupar los logs: {error}")
        return []

    return [
        {"accion": accion, "total": total}
        for accion, total in sorted(totales.items(), key=lambda x: x[1], reverse=True)
    ]


def obtener_preferencias(usuario):
    """Lee preferencias/<usuario> y las mezcla con los valores por defecto."""
    preferencias = dict(PREFERENCIAS_POR_DEFECTO)
    try:
        documento = _db.collection("preferencias").document(str(usuario)).get()
        if documento.exists:
            datos = documento.to_dict()
            preferencias.update({
                "tema": datos.get("tema", preferencias["tema"]),
                "idioma": datos.get("idioma", preferencias["idioma"]),
                "registros_por_pagina": datos.get(
                    "registros_por_pagina", preferencias["registros_por_pagina"]
                ),
            })
    except Exception as error:
        print(f"[ADVERTENCIA] No se pudieron leer las preferencias: {error}")

    if preferencias["tema"] not in ("claro", "oscuro"):
        preferencias["tema"] = "claro"
    if preferencias["idioma"] not in ("es", "en"):
        preferencias["idioma"] = "es"
    try:
        registros = int(preferencias["registros_por_pagina"])
    except (TypeError, ValueError):
        registros = PREFERENCIAS_POR_DEFECTO["registros_por_pagina"]
    preferencias["registros_por_pagina"] = max(5, min(100, registros))
    return preferencias


def obtener_documento_preferencias(usuario):
    """Devuelve el documento de preferencias tal como está en Firestore."""
    documento = {"usuario": str(usuario), **PREFERENCIAS_POR_DEFECTO}
    try:
        guardado = _db.collection("preferencias").document(str(usuario)).get()
        if guardado.exists:
            documento.update(guardado.to_dict())
    except Exception as error:
        print(f"[ADVERTENCIA] No se pudo leer el documento: {error}")

    actualizado = documento.get("actualizado")
    if actualizado is not None:
        documento["actualizado"] = (
            actualizado.isoformat() if hasattr(actualizado, "isoformat") else str(actualizado)
        )
    return documento


def guardar_preferencias(usuario, tema, idioma, registros_por_pagina):
    """Crea o actualiza el documento de preferencias del usuario."""
    try:
        _db.collection("preferencias").document(str(usuario)).set(
            {
                "usuario": str(usuario),
                "tema": str(tema),
                "idioma": str(idioma),
                "registros_por_pagina": int(registros_por_pagina),
                "actualizado": datetime.now(timezone.utc),
            },
            merge=True,
        )
        return True
    except Exception as error:
        print(f"[ADVERTENCIA] No se pudieron guardar las preferencias: {error}")
        return False
