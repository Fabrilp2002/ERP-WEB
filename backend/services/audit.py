"""
Servicio de Auditoría — registra toda accion de escritura en auditoria_log.

Uso:
    from ..services.audit import registrar

    await registrar(
        db, usuario=current_user, accion="INSERT",
        tabla="comprobantes", registro_id=str(nuevo_id),
        datos_nuevos={"numero": ...},
    )

NO hace commit — el router que llama se encarga.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Optional
from decimal import Decimal
from datetime import date, datetime
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from fastapi import Request


logger = logging.getLogger(__name__)
_SENSITIVE = re.compile(r'(password|token|secret|key)["\']?\s*[:=]\s*["\']?[^"\'\s,}]+', re.IGNORECASE)


def sanitizar(msg: str) -> str:
    """Enmascara secretos antes de escribir logs técnicos."""
    return _SENSITIVE.sub(r'\1=***', msg)


def _jsonable(obj):
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, dict):
        return {k: _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    return str(obj)


async def _columnas_auditoria(db: AsyncSession) -> set[str]:
    rows = (await db.execute(
        text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'auditoria_log'
        """)
    )).scalars().all()
    return set(rows)


async def registrar(
    db: AsyncSession,
    *,
    usuario: Optional[dict] = None,
    empresa_id: Optional[str] = None,
    accion: str,  # INSERT | UPDATE | DELETE | IA_ACTION | SELECT
    tabla: str,
    registro_id: Optional[str] = None,
    datos_anteriores: Optional[dict] = None,
    datos_nuevos: Optional[dict] = None,
    origen: str = "ui",  # ui | chatbot | api | sync
    ip_origen: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    """Inserta una fila en auditoria_log. Silencioso: no rompe el flujo si falla."""
    try:
        emp = empresa_id or (usuario.get("empresa_id") if usuario else None)
        usr = usuario.get("sub") if usuario else None
        columnas = await _columnas_auditoria(db)
        insert_cols = [
            "empresa_id", "usuario_id", "accion", "tabla_afectada", "registro_id",
            "datos_anteriores", "datos_nuevos", "origen",
        ]
        value_cols = [
            ":e", ":u", ":a", ":t", ":r",
            "CAST(:da AS JSONB)", "CAST(:dn AS JSONB)", ":o",
        ]
        params = {
            "e": str(emp) if emp else None,
            "u": str(usr) if usr else None,
            "a": accion,
            "t": tabla,
            "r": str(registro_id) if registro_id else None,
            "da": json.dumps(_jsonable(datos_anteriores)) if datos_anteriores else None,
            "dn": json.dumps(_jsonable(datos_nuevos)) if datos_nuevos else None,
            "o": origen,
        }

        if "ip_origen" in columnas:
            insert_cols.append("ip_origen")
            value_cols.append(":ip")
            params["ip"] = ip_origen
        if "user_agent" in columnas:
            insert_cols.append("user_agent")
            value_cols.append(":ua")
            params["ua"] = user_agent[:255] if user_agent else None

        await db.execute(
            text(f"""
                INSERT INTO auditoria_log ({', '.join(insert_cols)})
                VALUES ({', '.join(value_cols)})
            """),
            params,
        )
    except Exception as e:
        # Si la tabla auditoria_log no existe o falla, no queremos tumbar el request.
        # El router ya hizo el trabajo principal.
        logger.error("[audit] no se pudo registrar: %s", sanitizar(str(e)))


def extraer_ip(request: Request) -> str | None:
    """Obtiene IP real considerando proxies de Render/Railway/Vercel."""
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",", 1)[0].strip() or None
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else None


async def audit_with_request(request: Request, db: AsyncSession, **kwargs) -> None:
    """Registra auditoría incluyendo IP origen y User-Agent del request."""
    await registrar(
        db,
        ip_origen=extraer_ip(request),
        user_agent=request.headers.get("user-agent", "")[:255] or None,
        **kwargs,
    )
