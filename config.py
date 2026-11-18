"""config.py
---------
Propósito:
    Centralizar la configuración de la aplicación. Todas las credenciales se
    leen del archivo .env para no escribirlas dentro del código fuente
    (buena práctica de seguridad: el .env está en .gitignore).

Autor:  Santiago Duque
Curso:  Teoría de Bases de Datos
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Ruta absoluta de la carpeta del proyecto. Así el .env se encuentra sin
# importar desde qué directorio se ejecute "python app.py".
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


class Config:
    """Parámetros de configuración leídos desde variables de entorno."""

    # ------------------------------ Flask ----------------------------------
    # Clave usada para firmar la cookie de sesión (evita que sea manipulada).
    SECRET_KEY = os.getenv("SECRET_KEY", "clave-de-desarrollo-cambiar-en-.env")
    DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"

    # --------------- MySQL: datos transaccionales (ACID) -------------------
    MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
    MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
    MYSQL_USER = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
    MYSQL_DB = os.getenv("MYSQL_DB", "bd_universidad")

    # --------- Base NoSQL: datos no estructurados (logs/preferencias) ------
    # Valores posibles: "mongo" (por defecto) o "firebase".
    NOSQL_BACKEND = os.getenv("NOSQL_BACKEND", "mongo").lower()

    # MongoDB (local o MongoDB Atlas)
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    MONGO_DB = os.getenv("MONGO_DB", "gestion_academica")

    # Firebase (solo si NOSQL_BACKEND=firebase)
    FIREBASE_CREDENTIALS = os.getenv("FIREBASE_CREDENTIALS", "firebase-key.json")

    # --------------------------- Reglas de negocio -------------------------
    # Valor sugerido por crédito al crear una matrícula (pesos colombianos).
    VALOR_CREDITO = int(os.getenv("VALOR_CREDITO", "1000000"))
