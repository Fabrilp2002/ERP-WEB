"""
Store en memoria para la clave de Gemini API.

Prioridad de resolución (la primera no vacía gana):
  1. Override puesto vía UI (`set_key`) — vive sólo en memoria, se pierde al reiniciar.
  2. Variable de entorno `GEMINI_API_KEY` (configurar en Render / .env local).

Para rotar la clave: actualizar `GEMINI_API_KEY` en el panel de Render (o en `.env`
local) y reiniciar el servicio.
"""

import os

_gemini_key: str = ""


def set_key(key: str) -> None:
    global _gemini_key
    _gemini_key = key.strip()


def get_key() -> str:
    """Devuelve la clave activa: primero override de UI, después env var."""
    return _gemini_key or os.environ.get("GEMINI_API_KEY", "")


def is_configured() -> bool:
    return bool(get_key())
