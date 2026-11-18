"""db_nosql.py
-----------
Propósito:
    Punto único de acceso a la base NoSQL. Según la variable NOSQL_BACKEND del
    archivo .env se importan las funciones de MongoDB o de Firebase.

    El resto de la aplicación (app.py, auth.py) solo importa desde este módulo,
    así que cambiar de motor no obliga a modificar las rutas ni las plantillas.

Autor:  Santiago Duque
Curso:  Teoría de Bases de Datos
"""

from config import Config

if Config.NOSQL_BACKEND == "firebase":
    from db_firebase import (contar_logs, contar_por_accion,  # noqa: F401
                             guardar_preferencias, mongo_disponible,
                             obtener_documento_preferencias, obtener_logs,
                             obtener_preferencias, registrar_log)
else:
    from db_mongo import (contar_logs, contar_por_accion,  # noqa: F401
                          guardar_preferencias, mongo_disponible,
                          obtener_documento_preferencias, obtener_logs,
                          obtener_preferencias, registrar_log)
