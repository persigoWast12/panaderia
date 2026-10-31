"""Hash de contraseñas, tokens de sesión y dependencias de autenticación."""

import hashlib
import os
import secrets
from datetime import datetime, timedelta

import bcrypt
from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import Empleado, Sesion

NOMBRE_COOKIE = "session"
SESSION_HOURS = int(os.getenv("SESSION_HOURS", "12"))
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"


def hash_password(password: str) -> str:
    """Devuelve el hash bcrypt de una contraseña, listo para guardar."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Compara una contraseña con su hash. Nunca lanza excepción por un hash roto."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def hash_token(token: str) -> str:
    """Devuelve el SHA-256 del token; en la base se guarda solo este hash."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def crear_sesion(db: Session, empleado: Empleado) -> str:
    """Crea una sesión para el empleado y devuelve el token en claro."""
    token = secrets.token_urlsafe(32)
    db.add(
        Sesion(
            token_hash=hash_token(token),
            empleado_id=empleado.id,
            vence=datetime.now() + timedelta(hours=SESSION_HOURS),
        )
    )
    db.commit()
    return token


def get_current_empleado(request: Request, db: Session = Depends(get_db)) -> Empleado:
    """Devuelve el empleado de la sesión actual o responde 401."""
    token = request.cookies.get(NOMBRE_COOKIE)
    if not token:
        raise HTTPException(status_code=401, detail="No hay sesión iniciada.")

    sesion = db.scalar(select(Sesion).where(Sesion.token_hash == hash_token(token)))
    if sesion is None or sesion.vence < datetime.now():
        raise HTTPException(
            status_code=401, detail="La sesión no es válida o venció."
        )

    empleado = sesion.empleado
    if empleado is None or not empleado.activo:
        raise HTTPException(
            status_code=401, detail="La sesión no es válida o venció."
        )

    return empleado


def require_rol(*roles: str):
    """Devuelve una dependencia que exige uno de los roles indicados."""

    def dependencia(empleado: Empleado = Depends(get_current_empleado)) -> Empleado:
        if empleado.rol not in roles:
            raise HTTPException(
                status_code=403, detail="No tenés permiso para esta acción."
            )
        return empleado

    return dependencia
