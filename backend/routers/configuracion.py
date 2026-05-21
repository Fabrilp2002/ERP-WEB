"""
Router de configuración del sistema.
Permite guardar la clave de Gemini API desde la UI sin tocar el .env.
"""
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from ..core.security import get_current_user, require_escritura
from ..core import key_store

router = APIRouter(prefix="/configuracion", tags=["Configuración"])


class GeminiKeyIn(BaseModel):
    api_key: str


ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


def _persistir_en_env(key: str) -> None:
    """Escribe la clave en el .env para que sobreviva reinicios."""
    try:
        texto = ENV_FILE.read_text(encoding="utf-8")
        if "GEMINI_API_KEY=" in texto:
            import re
            texto = re.sub(r"GEMINI_API_KEY=.*", f"GEMINI_API_KEY={key}", texto)
        else:
            texto += f"\nGEMINI_API_KEY={key}\n"
        ENV_FILE.write_text(texto, encoding="utf-8")
    except Exception:
        pass  # Si no puede escribir el .env, al menos queda en memoria


@router.post("/gemini-key", summary="Guardar clave Gemini API")
async def guardar_gemini_key(
    body: GeminiKeyIn,
    current_user: dict = Depends(require_escritura),
):
    """Guarda la clave en memoria Y en el .env (persiste entre reinicios)."""
    if not body.api_key.strip():
        raise HTTPException(status_code=422, detail="La clave no puede estar vacía")
    key_store.set_key(body.api_key)
    _persistir_en_env(body.api_key)
    return {"ok": True, "configurado": True}


@router.get("/gemini-key", summary="Estado de clave Gemini API")
async def estado_gemini_key(
    current_user: dict = Depends(get_current_user),
):
    """Indica si hay una clave configurada (sin revelarla)."""
    return {"configurado": key_store.is_configured()}
