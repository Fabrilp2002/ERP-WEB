"""Action tokens persistidos para confirmaciones del chatbot."""
from __future__ import annotations

import hashlib
import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


TTL_SECONDS = 60


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def crear_action_token(
    db: AsyncSession,
    *,
    empresa_id: str,
    usuario_id: str,
    accion: str,
    payload: dict[str, Any],
    ttl_seconds: int = TTL_SECONDS,
) -> tuple[str, datetime]:
    """Guarda payload validado y devuelve token plano de un solo uso."""
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
    await db.execute(
        text("""
            INSERT INTO chatbot_action_tokens (
                empresa_id, usuario_id, token_hash, accion, payload, expires_at
            ) VALUES (
                :empresa_id, :usuario_id, :token_hash, :accion, CAST(:payload AS jsonb), :expires_at
            )
        """),
        {
            "empresa_id": empresa_id,
            "usuario_id": usuario_id,
            "token_hash": _hash_token(token),
            "accion": accion,
            "payload": json.dumps(payload),
            "expires_at": expires_at,
        },
    )
    await db.commit()
    return token, expires_at


async def consumir_action_token(
    db: AsyncSession,
    *,
    token: str,
    empresa_id: str,
    usuario_id: str,
) -> dict[str, Any]:
    """Valida tenant/usuario/TTL/uso unico y marca el token como usado."""
    row = (await db.execute(
        text("""
            SELECT id, accion, payload, expires_at, used_at
            FROM chatbot_action_tokens
            WHERE token_hash = :token_hash
              AND empresa_id = :empresa_id
              AND usuario_id = :usuario_id
            FOR UPDATE
        """),
        {
            "token_hash": _hash_token(token),
            "empresa_id": empresa_id,
            "usuario_id": usuario_id,
        },
    )).mappings().first()

    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Accion no encontrada o no pertenece a esta sesion")
    if row["used_at"] is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Esta accion ya fue confirmada")
    if row["expires_at"] <= datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="La confirmacion expiro. Genera el preview nuevamente")

    await db.execute(
        text("UPDATE chatbot_action_tokens SET used_at = NOW() WHERE id = :id"),
        {"id": str(row["id"])},
    )
    return {
        "accion": row["accion"],
        "payload": dict(row["payload"] or {}),
    }


async def limpiar_tokens_expirados(db: AsyncSession) -> None:
    await db.execute(
        text("""
            DELETE FROM chatbot_action_tokens
            WHERE expires_at < NOW() - INTERVAL '1 day'
               OR used_at < NOW() - INTERVAL '1 day'
        """)
    )
