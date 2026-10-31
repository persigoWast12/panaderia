"""Esquemas (Pydantic) que definen lo que entra y sale de la API."""

from pydantic import BaseModel


class LoginIn(BaseModel):
    """Datos que manda el formulario de login."""

    usuario: str
    password: str


class MeOut(BaseModel):
    """Datos públicos del empleado autenticado."""

    nombre: str
    rol: str
