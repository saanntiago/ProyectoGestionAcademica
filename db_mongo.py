"""db_mongo.py
-----------
Propósito:
    Guardar los datos NO estructurados del sistema en MongoDB Atlas:
      - Colección "logs": registro de actividad (login, creación, eliminación...).
      - Colección "preferencias": configuración personal de cada usuario
        (tema claro/oscuro, idioma y registros por página).

¿Por qué MongoDB y no MySQL para esto?
    Los logs crecen rápido, no tienen un esquema fijo y no necesitan
    transacciones ACID ni relaciones. Un modelo de documentos es más flexible
    para este tipo de información.

SEGURIDAD (inyección NoSQL):
    Los valores se convierten con str() antes de usarlos en los filtros. Así se
    evita que un atacante envíe un objeto como {"$ne": ""} en lugar de un texto
    y altere la consulta.

Autor:  Santiago Duque
Curso:  Teoría de Bases de Datos
"""

from datetime import datetime, timezone

from pymongo import DESCENDING, MongoClient
from pymongo.errors import PyMongoError

from config import Config

# Preferencias que se usan cuando el usuario todavía no ha guardado las suyas.
PREFERENCIAS_POR_DEFECTO = {"tema": "claro", "idioma": "es", "registros_por_pagina": 10}

# serverSelectionTimeoutMS evita que la aplicación se quede esperando si
# MongoDB no responde. Si la conexión falla, la app sigue funcionando y solo
# muestra una advertencia (degradación controlada).
try:
    _cliente = MongoClient(Config.MONGO_URI, serverSelectionTimeoutMS=4000)
    _db = _cliente[Config.MONGO_DB]
    _logs = _db["logs"]
    _preferencias = _db["preferencias"]
except Exception as error:  # configuración inválida de la URI
    print(f"[ADVERTENCIA] MongoDB no está configurado: {error}")
    _cliente = None
    _db = None
    _logs = None
    _preferencias = None


def mongo_disponible():
    """Comprueba con un ping si MongoDB responde. Se usa en el diagnóstico."""
    if _cliente is None:
        return False
    try:
        _cliente.admin.command("ping")
        return True
    except PyMongoError:
        return False


def registrar_log(usuario, accion, detalle="", ip=""):
    """Inserta un documento de log en MongoDB.

    Si MongoDB no está disponible solo se muestra una advertencia en consola;
    la operación principal (por ejemplo crear un estudiante) no se detiene.

    Parámetros:
        usuario (str): nombre del usuario que ejecutó la acción.
        accion (str): código corto de la acción (login, estudiante_creado...).
        detalle (str): texto descriptivo de lo ocurrido.
        ip (str): dirección desde la que se realizó la acción.
    """
    if _logs is None:
        print("[ADVERTENCIA] MongoDB no configurado; no se registró el log.")
        return
    try:
        _logs.insert_one({
            # str() neutraliza objetos maliciosos tipo {"$ne": ""} (inyección NoSQL)
            "usuario": str(usuario)[:80],
            "accion": str(accion)[:50],
            "detalle": str(detalle)[:500],
            "ip": str(ip)[:45],
            "fecha": datetime.now(timezone.utc),  # siempre en UTC
        })
    except PyMongoError as error:
        print(f"[ADVERTENCIA] No se pudo registrar el log en MongoDB: {error}")


def obtener_logs(limite=100, accion=None, usuario=None):
    """Devuelve los últimos logs, del más reciente al más antiguo.

    Parámetros:
        limite (int): cantidad máxima de documentos.
        accion (str|None): filtra por tipo de acción.
        usuario (str|None): filtra por usuario.
    """
    if _logs is None:
        return []

    filtro = {}
    if accion:
        filtro["accion"] = str(accion)  # valor validado en la ruta
    if usuario:
        filtro["usuario"] = str(usuario)

    try:
        cursor = (
            _logs.find(filtro, {"_id": 0})
            .sort("fecha", DESCENDING)
            .limit(int(limite))
        )
        return list(cursor)
    except PyMongoError as error:
        print(f"[ADVERTENCIA] No se pudieron leer los logs: {error}")
        return []


def contar_logs():
    """Devuelve el total de eventos registrados (0 si MongoDB no responde)."""
    if _logs is None:
        return 0
    try:
        return _logs.count_documents({})
    except PyMongoError as error:
        print(f"[ADVERTENCIA] No se pudieron contar los logs: {error}")
        return 0


def contar_por_accion():
    """Agrupa los logs por acción: [{'accion': 'login', 'total': 12}, ...]."""
    if _logs is None:
        return []
    try:
        filas = list(_logs.aggregate([
            {"$group": {"_id": "$accion", "total": {"$sum": 1}}},
            {"$sort": {"total": -1}},
        ]))
    except PyMongoError as error:
        print(f"[ADVERTENCIA] No se pudo agrupar los logs: {error}")
        return []

    # Se normaliza la salida: _id -> accion (nombre más claro para la vista).
    return [
        {"accion": fila.get("_id", "desconocida"), "total": fila.get("total", 0)}
        for fila in filas
    ]


def obtener_preferencias(usuario):
    """Lee el documento de preferencias del usuario y lo mezcla con los valores
    por defecto (así siempre devuelve las tres claves).
    """
    preferencias = dict(PREFERENCIAS_POR_DEFECTO)
    if _preferencias is None:
        return preferencias

    try:
        documento = _preferencias.find_one({"usuario": str(usuario)})
        if documento:
            preferencias.update({
                "tema": documento.get("tema", preferencias["tema"]),
                "idioma": documento.get("idioma", preferencias["idioma"]),
                "registros_por_pagina": documento.get(
                    "registros_por_pagina", preferencias["registros_por_pagina"]
                ),
            })
    except PyMongoError as error:
        print(f"[ADVERTENCIA] No se pudieron leer las preferencias: {error}")

    # Saneamiento por si el documento fue editado manualmente en Compass.
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
    """Devuelve el documento de preferencias tal como está en MongoDB.

    Se usa en la vista de preferencias para mostrar el documento real
    (incluidos los campos "usuario" y "actualizado").
    """
    documento = {"usuario": str(usuario), **PREFERENCIAS_POR_DEFECTO}
    if _preferencias is not None:
        try:
            guardado = _preferencias.find_one({"usuario": str(usuario)}, {"_id": 0})
            if guardado:
                documento.update(guardado)
        except PyMongoError as error:
            print(f"[ADVERTENCIA] No se pudo leer el documento: {error}")

    # Las fechas se convierten a texto para poder mostrarlas como JSON.
    if hasattr(documento.get("actualizado"), "isoformat"):
        documento["actualizado"] = documento["actualizado"].isoformat()
    return documento


def guardar_preferencias(usuario, tema, idioma, registros_por_pagina):
    """Crea o actualiza el documento de preferencias del usuario.

    update_one(..., upsert=True) inserta el documento si no existe y lo
    actualiza si ya existe. Es la operación típica de MongoDB para este caso.
    """
    if _preferencias is None:
        return False
    try:
        _preferencias.update_one(
            {"usuario": str(usuario)},
            {"$set": {
                "tema": str(tema),
                "idioma": str(idioma),
                "registros_por_pagina": int(registros_por_pagina),
                "actualizado": datetime.now(timezone.utc),
            }},
            upsert=True,
        )
        return True
    except PyMongoError as error:
        print(f"[ADVERTENCIA] No se pudieron guardar las preferencias: {error}")
        return False
