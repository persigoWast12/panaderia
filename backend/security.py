"""Hash de contraseñas, tokens de sesión y dependencias de autenticación."""

import bcrypt


def hash_password(password: str) -> str:
    """Devuelve el hash bcrypt de una contraseña, listo para guardar."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Compara una contraseña con su hash. Nunca lanza excepción por un hash roto."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False
