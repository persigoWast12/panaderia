"""Endpoints para que el dueño administre a los empleados.

Reglas principales:
- Solo el rol `dueno` puede entrar a estos endpoints.
- El usuario se guarda en minúsculas y es único.
- La contraseña se guarda hasheada y nunca se devuelve.
- El dueño no puede desactivarse a sí mismo ni cambiarse el rol, y el sistema
  no se puede quedar sin un dueño activo.
- Al desactivar o resetear la contraseña se cierran las sesiones abiertas.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import get_db
from models import Empleado, Sesion
from schemas import EmpleadoIn, EmpleadoOut, EmpleadoUpdate, PasswordIn
from security import hash_password, require_rol

router = APIRouter(prefix="/empleados", tags=["Empleados"])

MENSAJE_USUARIO_REPETIDO = "Ya existe un empleado con ese usuario."
MENSAJE_ULTIMO_DUENO = "Tiene que quedar al menos un dueño activo."
MENSAJE_PASSWORD_LARGA = "La contraseña es demasiado larga."


def _empleado_out(empleado: Empleado) -> dict:
    """Devuelve los datos públicos del empleado, sin el hash."""
    return {
        "id": empleado.id,
        "nombre": empleado.nombre,
        "usuario": empleado.usuario,
        "rol": empleado.rol,
        "activo": empleado.activo,
    }


def _normalizar_usuario(usuario: str) -> str:
    """El usuario se guarda siempre en minúsculas y sin espacios extra."""
    normalizado = usuario.strip().lower()
    if len(normalizado) < 3:
        raise HTTPException(
            status_code=400,
            detail="El nombre de usuario tiene que tener al menos 3 caracteres.",
        )
    return normalizado


def _validar_password(password: str) -> None:
    """bcrypt no acepta contraseñas de más de 72 bytes."""
    if len(password.encode("utf-8")) > 72:
        raise HTTPException(status_code=400, detail=MENSAJE_PASSWORD_LARGA)


@router.get("", response_model=list[EmpleadoOut])
def listar_empleados(
    db: Session = Depends(get_db),
    _empleado: Empleado = Depends(require_rol("dueno")),
):
    """Lista todos los empleados, incluidos los inactivos.

    Los inactivos se muestran para poder reactivarlos; no se borran porque sus
    ventas y sesiones históricas dependen de ellos.
    """
    empleados = db.scalars(select(Empleado).order_by(Empleado.nombre)).all()
    return [_empleado_out(empleado) for empleado in empleados]


@router.post("", response_model=EmpleadoOut, status_code=201)
def crear_empleado(
    datos: EmpleadoIn,
    db: Session = Depends(get_db),
    _empleado: Empleado = Depends(require_rol("dueno")),
):
    """Crea un empleado con su contraseña hasheada.

    El nombre y el usuario se limpian de espacios. Se valida el usuario
    repetido antes del insert y se captura `IntegrityError` como respaldo.
    """
    nombre = datos.nombre.strip()
    if not nombre:
        raise HTTPException(status_code=400, detail="El nombre no puede estar vacío.")

    usuario = _normalizar_usuario(datos.usuario)
    repetido = db.scalar(select(Empleado).where(Empleado.usuario == usuario))
    if repetido is not None:
        raise HTTPException(status_code=400, detail=MENSAJE_USUARIO_REPETIDO)

    _validar_password(datos.password)

    empleado = Empleado(
        nombre=nombre,
        usuario=usuario,
        rol=datos.rol,
        password_hash=hash_password(datos.password),
        activo=datos.activo,
    )
    db.add(empleado)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400, detail=MENSAJE_USUARIO_REPETIDO
        ) from None

    db.refresh(empleado)
    return _empleado_out(empleado)


@router.put("/{empleado_id}", response_model=EmpleadoOut)
def actualizar_empleado(
    empleado_id: int,
    datos: EmpleadoUpdate | None = None,
    db: Session = Depends(get_db),
    actual: Empleado = Depends(require_rol("dueno")),
):
    """Actualiza nombre, usuario, rol o estado de un empleado.

    `exclude_unset` permite mandar solo los campos que cambian. Los permisos
    de edición son solo para el dueño.
    """
    empleado = db.get(Empleado, empleado_id)
    if empleado is None:
        raise HTTPException(status_code=404, detail="Empleado no encontrado.")

    cambios = (
        datos.model_dump(exclude_unset=True, exclude_none=True) if datos else {}
    )
    if not cambios:
        raise HTTPException(
            status_code=400, detail="No se enviaron campos para actualizar."
        )

    # El dueño no puede sacarse a sí mismo el acceso: ni desactivarse ni
    # cambiarse el rol. Así siempre queda alguien que pueda administrar.
    if empleado.id == actual.id:
        if "rol" in cambios and cambios["rol"] != empleado.rol:
            raise HTTPException(
                status_code=400, detail="No podés cambiar tu propio rol."
            )
        if cambios.get("activo") is False:
            raise HTTPException(
                status_code=400, detail="No podés desactivar tu propio usuario."
            )

    if "nombre" in cambios:
        cambios["nombre"] = cambios["nombre"].strip()
        if not cambios["nombre"]:
            raise HTTPException(
                status_code=400, detail="El nombre no puede estar vacío."
            )

    if "usuario" in cambios:
        cambios["usuario"] = _normalizar_usuario(cambios["usuario"])
        repetido = db.scalar(
            select(Empleado).where(
                Empleado.usuario == cambios["usuario"],
                Empleado.id != empleado_id,
            )
        )
        if repetido is not None:
            raise HTTPException(status_code=400, detail=MENSAJE_USUARIO_REPETIDO)

    # No se puede quedar el sistema sin ningún dueño activo. Cubre el caso de
    # que un dueño desactive o degrade a otro dueño.
    rol_nuevo = cambios.get("rol", empleado.rol)
    activo_nuevo = cambios.get("activo", empleado.activo)
    if empleado.rol == "dueno" and not (rol_nuevo == "dueno" and activo_nuevo):
        otros_duenos = db.scalar(
            select(func.count())
            .select_from(Empleado)
            .where(
                Empleado.rol == "dueno",
                Empleado.activo.is_(True),
                Empleado.id != empleado.id,
            )
        )
        if otros_duenos == 0:
            raise HTTPException(status_code=400, detail=MENSAJE_ULTIMO_DUENO)

    for campo, valor in cambios.items():
        setattr(empleado, campo, valor)

    # Si se desactiva, sus sesiones abiertas dejan de servir.
    if empleado.activo is False:
        db.execute(delete(Sesion).where(Sesion.empleado_id == empleado.id))

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400, detail=MENSAJE_USUARIO_REPETIDO
        ) from None

    db.refresh(empleado)
    return _empleado_out(empleado)


@router.put("/{empleado_id}/password")
def resetear_password(
    empleado_id: int,
    datos: PasswordIn,
    db: Session = Depends(get_db),
    _empleado: Empleado = Depends(require_rol("dueno")),
):
    """Asigna una contraseña nueva y cierra las sesiones del empleado.

    Cerrar las sesiones evita que una sesión abierta con la clave vieja siga
    funcionando después del reseteo.
    """
    empleado = db.get(Empleado, empleado_id)
    if empleado is None:
        raise HTTPException(status_code=404, detail="Empleado no encontrado.")

    _validar_password(datos.password)
    empleado.password_hash = hash_password(datos.password)
    db.execute(delete(Sesion).where(Sesion.empleado_id == empleado.id))
    db.commit()

    return {
        "detail": "Contraseña actualizada. Se cerraron las sesiones de ese empleado."
    }
