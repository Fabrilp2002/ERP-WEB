"""
Router Chatbot IA — Fase 4
Endpoints para el asistente conversacional del ERP.
"""
import json
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from ..core.database import get_db
from ..core.security import get_current_user
from ..services.chatbot import chat, chat_stream, confirmar_accion_chatbot, verificar_estado

router = APIRouter(prefix="/chat", tags=["Asistente IA"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class MensajeEntrada(BaseModel):
    mensaje: str
    historial: list[dict] = []
    forzar_gemini: bool = False


class AccionEjecutada(BaseModel):
    funcion: str
    argumentos: dict
    resultado: dict


class RespuestaChat(BaseModel):
    respuesta: str
    acciones: list[AccionEjecutada] = []
    motor_usado: str


class ConfirmarAccionIn(BaseModel):
    action_token: str
    historial: list[dict] = []


class ConfirmarAccionOut(BaseModel):
    ok: bool
    accion: str
    resultado: dict
    mensaje: str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post(
    "/mensaje",
    response_model=RespuestaChat,
    summary="Enviar mensaje al asistente IA",
)
async def enviar_mensaje(
    entrada: MensajeEntrada,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Procesa un mensaje del usuario y devuelve la respuesta del asistente.

    El asistente puede:
    - Consultar saldos de clientes/proveedores
    - Verificar stock
    - Listar facturas pendientes
    - Dar un resumen financiero

    El historial debe enviarse desde el frontend para mantener el contexto
    de la conversación (el backend es stateless).
    """
    empresa_id = str(current_user["empresa_id"])
    rol = str(current_user.get("rol") or "operador")
    usuario_id = str(current_user.get("sub") or "")

    resultado = await chat(
        mensaje=entrada.mensaje,
        historial=entrada.historial,
        empresa_id=empresa_id,
        db=db,
        rol=rol,
        usuario_id=usuario_id,
        forzar_gemini=entrada.forzar_gemini,
    )

    return RespuestaChat(**resultado)


@router.post(
    "/mensaje-stream",
    summary="Enviar mensaje al asistente IA (Server-Sent Events)",
)
async def enviar_mensaje_stream(
    entrada: MensajeEntrada,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Variante streaming del chatbot. Devuelve text/event-stream con eventos JSON.

    Eventos producidos (un `data:` por línea, JSON):
        {"type": "token",   "text": "..."}      # chunk de texto
        {"type": "accion",  "accion": {...}}    # function call ejecutada
        {"type": "done",    "acciones": [...]}  # fin
        {"type": "error",   "message": "..."}   # error
    """
    empresa_id = str(current_user["empresa_id"])
    rol = str(current_user.get("rol") or "operador")
    usuario_id = str(current_user.get("sub") or "")

    async def event_stream():
        async for ev in chat_stream(
            mensaje=entrada.mensaje,
            historial=entrada.historial,
            empresa_id=empresa_id,
            db=db,
            rol=rol,
            usuario_id=usuario_id,
        ):
            yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # evita buffering en proxies (Render/nginx)
            "Connection": "keep-alive",
        },
    )


@router.post(
    "/confirmar-accion",
    response_model=ConfirmarAccionOut,
    summary="Confirmar una accion preview del chatbot",
)
async def confirmar_accion(
    entrada: ConfirmarAccionIn,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    empresa_id = str(current_user["empresa_id"])
    rol = str(current_user.get("rol") or "operador")
    usuario_id = str(current_user.get("sub") or "")

    resultado = await confirmar_accion_chatbot(
        action_token=entrada.action_token,
        empresa_id=empresa_id,
        usuario_id=usuario_id,
        rol=rol,
        db=db,
    )
    return ConfirmarAccionOut(**resultado)


@router.get(
    "/estado",
    summary="Estado del motor IA",
)
async def estado_ia(
    current_user: dict = Depends(get_current_user),
):
    """
    Devuelve si Gemini (motor IA unico) esta configurado.
    """
    return await verificar_estado()
