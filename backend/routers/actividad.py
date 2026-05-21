"""
Actividad reciente — feed visible para TODOS los usuarios (admin/operador/viewer).

A diferencia de /admin/auditoria (que expone payloads JSON completos con
datos_anteriores / datos_nuevos y requiere rol admin), este endpoint devuelve
solo metadata segura: quien hizo que, sobre que tabla, y cuando. No expone
contenido de campos. Sirve para responder "¿quien actuo en el sistema?" desde
cualquier rol sin filtrar informacion sensible.
"""
from __future__ import annotations
from datetime import date
from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from ..core.database import get_db
from ..core.security import get_current_user


router = APIRouter(prefix="/actividad", tags=["Actividad"])


# Etiquetas humanas — evitan que el frontend tenga que mapear nombres tecnicos
_TABLA_LABEL = {
    "comprobantes": "Comprobante",
    "pagos": "Pago/Cobro",
    "clientes": "Cliente",
    "proveedores": "Proveedor",
    "inventario": "Inventario",
    "usuarios": "Usuario",
    "empresas": "Empresa",
    "auditoria_log": "Auditoria",
    "configuracion_empresa": "Configuracion",
}

_ACCION_LABEL = {
    "INSERT": "Creado",
    "UPDATE": "Modificado",
    "DELETE": "Eliminado",
    "LOGIN": "Inicio de sesion",
    "LOGOUT": "Cierre de sesion",
    "EXPORT": "Exportado",
    "BACKUP": "Respaldo",
}


@router.get("/", summary="Actividad reciente (quien actuo en el sistema)")
async def actividad_reciente(
    tabla: Optional[str] = Query(None, description="Filtrar por tabla (comprobantes, pagos, ...)"),
    accion: Optional[str] = Query(None, description="INSERT, UPDATE, DELETE, LOGIN, ..."),
    usuario_id: Optional[UUID] = Query(None),
    desde: Optional[date] = Query(None),
    hasta: Optional[date] = Query(None),
    limite: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Devuelve quien hizo que (sin payloads). Accesible a admin/operador/viewer:
    transparencia de actividad sin filtrar informacion sensible de campos.
    """
    empresa_id = current_user["empresa_id"]
    where = ["a.empresa_id = :e"]
    params: dict = {"e": empresa_id, "lim": limite}

    if tabla:
        where.append("a.tabla_afectada = :t"); params["t"] = tabla
    if accion:
        where.append("a.accion = :ac"); params["ac"] = accion
    if usuario_id:
        where.append("a.usuario_id = :u"); params["u"] = str(usuario_id)
    if desde:
        where.append("a.fecha >= :d"); params["d"] = desde
    if hasta:
        # "fin de día" = día siguiente, calculado en Python para Postgres + SQLite
        from datetime import date as _date, timedelta as _td
        h_obj = hasta if hasattr(hasta, "year") else _date.fromisoformat(str(hasta))
        where.append("a.fecha < :h"); params["h"] = (h_obj + _td(days=1)).isoformat()

    result = await db.execute(
        text(f"""
            SELECT a.id, a.fecha, a.accion, a.tabla_afectada, a.registro_id,
                   a.usuario_id,
                   NULLIF(TRIM(COALESCE(u.nombre,'') || ' ' || COALESCE(u.apellido,'')), '') AS usuario_nombre,
                   u.email AS usuario_email
            FROM auditoria_log a
            LEFT JOIN usuarios u ON u.id = a.usuario_id
            WHERE {' AND '.join(where)}
            ORDER BY a.fecha DESC
            LIMIT :lim
        """),
        params,
    )

    filas = []
    for r in result.mappings().all():
        filas.append({
            "id": str(r["id"]),
            "fecha": (r["fecha"].isoformat() if hasattr(r["fecha"], "isoformat") else r["fecha"]) if r["fecha"] else None,
            "accion": r["accion"],
            "accion_label": _ACCION_LABEL.get(r["accion"] or "", r["accion"] or "—"),
            "tabla": r["tabla_afectada"],
            "tabla_label": _TABLA_LABEL.get(r["tabla_afectada"] or "", r["tabla_afectada"] or "—"),
            "registro_id": str(r["registro_id"]) if r["registro_id"] else None,
            "usuario_id": str(r["usuario_id"]) if r["usuario_id"] else None,
            "usuario_nombre": r["usuario_nombre"] or "—",
            "usuario_email": r["usuario_email"] or "",
        })
    return {"actividad": filas, "cantidad": len(filas)}
