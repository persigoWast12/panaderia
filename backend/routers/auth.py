"""Endpoints de login, logout y datos de la sesión actual."""

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import Empleado, Sesion
from schemas import LoginIn, MeOut
from security import (
    COOKIE_SECURE,
    NOMBRE_COOKIE,
    SESSION_HOURS,
    crear_sesion,
    get_current_empleado,
    hash_token,
    verify_password,
)

router = APIRouter(tags=["Autenticación"])

# Mismo mensaje para usuario inexistente y contraseña incorrecta.
MENSAJE_LOGIN = "usuario o contraseña incorrectos"


def _setear_cookie(response: Response, token: str) -> None:
    """Setea la cookie de sesión con la configuración acordada.

    - `httponly`: JavaScript no puede leer el token.
    - `samesite="lax"`: el navegador no la manda en POST desde otros sitios.
    - `secure`: controlado por `.env`; en la red local HTTP va en false.
    - `path="/"`: válida para toda la aplicación.
    """
    response.set_cookie(
        key=NOMBRE_COOKIE,
        value=token,
        max_age=SESSION_HOURS * 3600,
        httponly=True,
        samesite="lax",
        secure=COOKIE_SECURE,
        path="/",
    )


@router.post("/login", response_model=MeOut)
def login(datos: LoginIn, response: Response, db: Session = Depends(get_db)):
    """Valida usuario y contraseña y abre una sesión.

    El usuario se normaliza a minúsculas. Si no existe o la contraseña no
    coincide, se devuelve el mismo 401 para no revelar cuál de los dos falló.
    """
    usuario = datos.usuario.strip().lower()
    empleado = db.scalar(
        select(Empleado).where(
            Empleado.usuario == usuario, Empleado.activo.is_(True)
        )
    )
    if empleado is None or not verify_password(datos.password, empleado.password_hash):
        raise HTTPException(status_code=401, detail=MENSAJE_LOGIN)

    token = crear_sesion(db, empleado)
    _setear_cookie(response, token)
    return {
        "id": empleado.id,
        "nombre": empleado.nombre,
        "usuario": empleado.usuario,
        "rol": empleado.rol,
    }


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    _empleado: Empleado = Depends(get_current_empleado),
    db: Session = Depends(get_db),
):
    """Cierra la sesión actual: borra la fila y la cookie.

    Acepta cualquier rol activo, incluidos contador y dueño. Si la sesión ya
    estaba vencida, `get_current_empleado` responde 401 antes de llegar acá.
    """
    token = request.cookies.get(NOMBRE_COOKIE)
    if token:
        sesion = db.scalar(
            select(Sesion).where(Sesion.token_hash == hash_token(token))
        )
        if sesion is not None:
            db.delete(sesion)
            db.commit()

    response.delete_cookie(NOMBRE_COOKIE, path="/")
    return {"detail": "Sesión cerrada."}


@router.get("/me", response_model=MeOut)
def me(empleado: Empleado = Depends(get_current_empleado)):
    """Devuelve los datos del empleado autenticado.

    El frontend usa esta respuesta para saber quién entró, qué rol tiene y qué
    pantallas mostrarle.
    """
    return {
        "id": empleado.id,
        "nombre": empleado.nombre,
        "usuario": empleado.usuario,
        "rol": empleado.rol,
    }
