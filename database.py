import sqlite3
import hashlib
import os

DB_NAME = "viggo_usuarios.db"

def hash_password(password):
    """Convierte la contraseña en un hash seguro"""
    return hashlib.sha256(password.encode()).hexdigest()

def crear_base_datos():
    """Crea la base de datos y la tabla de usuarios si no existe"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre   TEXT    NOT NULL,
            email    TEXT    UNIQUE NOT NULL,
            password TEXT    NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def registrar_usuario(nombre, email, password):
    """
    Registra un nuevo usuario.
    Retorna: 'ok' si se registró, 'existe' si el email ya está en uso
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO usuarios (nombre, email, password) VALUES (?, ?, ?)",
            (nombre.strip(), email.strip().lower(), hash_password(password))
        )
        conn.commit()
        return "ok"
    except sqlite3.IntegrityError:
        return "existe"
    finally:
        conn.close()

def verificar_login(email, password):
    """
    Verifica si el email y contraseña son correctos.
    Retorna el nombre del usuario si es correcto, None si no.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT nombre FROM usuarios WHERE email = ? AND password = ?",
        (email.strip().lower(), hash_password(password))
    )
    resultado = cursor.fetchone()
    conn.close()
    if resultado:
        return resultado[0]  # Retorna el nombre del usuario
    return None

# Crear la base de datos automáticamente al importar este archivo
crear_base_datos()