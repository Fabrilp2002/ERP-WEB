"""
Store en memoria para la clave de Gemini API.

Prioridad de resolución (la primera no vacía gana):
  1. Override puesto vía UI (`set_key`) — vive sólo en memoria, se pierde al reiniciar.
  2. Clave hardcodeada en este archivo (`_HARDCODED_KEY`).

La env var `GEMINI_API_KEY` queda **ignorada a propósito**: en producción Render tenía
una env var apuntando a una clave revocada que se imponía sobre el hardcode y rompía
el chat. El repo es privado — se acepta el trade-off de mantener la clave en código
a cambio de no depender del panel de Render.

Para rotar: reemplazar `_HARDCODED_KEY` por la nueva clave + commit + push.
"""

# Clave Gemini activa. Para rotar: cambiar acá y pushear.
_HARDCODED_KEY: str = "AIzaSyBw7Y0TSaupOMCMHegSI5ldWwG3gOA4VkY"

_gemini_key: str = ""


def set_key(key: str) -> None:
    global _gemini_key
    _gemini_key = key.strip()


def get_key() -> str:
    """Devuelve la clave activa: primero override de UI, después hardcode."""
    return _gemini_key or _HARDCODED_KEY


def is_configured() -> bool:
    return bool(get_key())
