"""
Política estricta de contraseñas para ERP_Web.

Reglas aprobadas por PM en `docs/roadmap/PLAN_SEGURIDAD.md`:
- 8+ caracteres
- al menos 1 mayúscula
- al menos 1 minúscula
- al menos 1 número
- al menos 1 símbolo
"""
from __future__ import annotations

import re

_SYMBOL_RE = re.compile(r"[^A-Za-z0-9]")


def validar_password(password: str) -> tuple[bool, list[str]]:
    """Devuelve `(ok, errores)` con mensajes listos para mostrar al usuario."""
    errores: list[str] = []
    password = password or ""

    if len(password) < 8:
        errores.append("Usá al menos 8 caracteres")
    if not any(c.isupper() for c in password):
        errores.append("Falta una mayúscula")
    if not any(c.islower() for c in password):
        errores.append("Falta una minúscula")
    if not any(c.isdigit() for c in password):
        errores.append("Agregá al menos un número")
    if not _SYMBOL_RE.search(password):
        errores.append("Agregá al menos un símbolo (!@#$%)")

    return not errores, errores


def assert_password_fuerte(password: str) -> None:
    """Lanza ValueError con detalle legible si la password no cumple la política."""
    ok, errores = validar_password(password)
    if not ok:
        raise ValueError("Contraseña débil: " + "; ".join(errores))
