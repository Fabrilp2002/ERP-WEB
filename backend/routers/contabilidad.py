"""
Router Contabilidad — Fase H.

Endpoints:
  GET /contabilidad/libro-diario          — listado de asientos
  POST /contabilidad/asientos             — asiento manual (solo admin)
  GET /contabilidad/mayor/{cuenta_id}     — libro mayor de una cuenta
  GET /contabilidad/balance-comprobacion  — sumas y saldos
  GET /contabilidad/estado-resultados     — ingresos vs egresos
  GET /contabilidad/balance-general       — activo = pasivo + patrimonio
"""
from __future__ import annotations
from datetime import date
from decimal import Decimal
from uuid import UUID
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from ..core.database import get_db
from ..core.security import get_current_user, require_admin
from ..services.contabilidad import (
    libro_mayor_cuenta,
    balance_comprobacion,
    estado_resultados,
    balance_general,
    _insertar_asiento,
)

router = APIRouter(prefix="/contabilidad", tags=["Contabilidad"])


# ── Libro Diario ───────────────────────────────────────────────────────────────

@router.get("/libro-diario", summary="Libro Diario — listado de asientos")
async def listar_libro_diario(
    desde: Optional[date] = Query(None),
    hasta: Optional[date] = Query(None),
    tipo: Optional[str] = Query(None, description="automatico|manual|ajuste|cierre"),
    limite: int = Query(200, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    empresa_id = current_user["empresa_id"]
    where = ["a.empresa_id = :e"]
    params: dict = {"e": empresa_id, "lim": limite}
    if desde:
        where.append("a.fecha >= :d"); params["d"] = desde
    if hasta:
        where.append("a.fecha <= :h"); params["h"] = hasta
    if tipo:
        where.append("a.tipo = :t"); params["t"] = tipo

    asientos = (await db.execute(
        text(f"""
            SELECT a.id, a.numero, a.fecha, a.concepto, a.tipo,
                   a.comprobante_id, a.pago_id, a.fecha_creacion,
                   NULLIF(TRIM(COALESCE(u.nombre,'') || ' ' || COALESCE(u.apellido,'')), '') AS usuario_nombre,
                   SUM(da.debe)  AS total_debe,
                   SUM(da.haber) AS total_haber
            FROM asientos_contables a
            LEFT JOIN usuarios u ON u.id = a.usuario_id
            LEFT JOIN detalle_asientos da ON da.asiento_id = a.id
            WHERE {' AND '.join(where)}
            GROUP BY a.id, a.numero, a.fecha, a.concepto, a.tipo,
                     a.comprobante_id, a.pago_id, a.fecha_creacion, u.nombre, u.apellido
            ORDER BY a.fecha DESC, a.numero DESC
            LIMIT :lim
        """),
        params,
    )).mappings().all()

    return [dict(r) for r in asientos]


@router.get("/libro-diario/{asiento_id}", summary="Detalle de un asiento")
async def detalle_asiento(
    asiento_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    empresa_id = current_user["empresa_id"]
    cabecera = (await db.execute(
        text("""
            SELECT a.id, a.numero, a.fecha, a.concepto, a.tipo,
                   a.comprobante_id, a.pago_id,
                   NULLIF(TRIM(COALESCE(u.nombre,'') || ' ' || COALESCE(u.apellido,'')), '') AS usuario_nombre
            FROM asientos_contables a
            LEFT JOIN usuarios u ON u.id = a.usuario_id
            WHERE a.id = :id AND a.empresa_id = :e
        """),
        {"id": str(asiento_id), "e": empresa_id},
    )).mappings().first()
    if not cabecera:
        raise HTTPException(404, "Asiento no encontrado")

    partidas = (await db.execute(
        text("""
            SELECT da.id, pc.codigo, pc.nombre AS cuenta_nombre, pc.tipo AS cuenta_tipo,
                   da.debe, da.haber
            FROM detalle_asientos da
            JOIN plan_cuentas pc ON pc.id = da.cuenta_id
            WHERE da.asiento_id = :a AND da.empresa_id = :e
            ORDER BY da.debe DESC
        """),
        {"a": str(asiento_id), "e": empresa_id},
    )).mappings().all()

    return {**dict(cabecera), "partidas": [dict(p) for p in partidas]}


# ── Asiento manual ─────────────────────────────────────────────────────────────

class PartidaIn(BaseModel):
    cuenta_id: UUID
    debe: Decimal = Decimal(0)
    haber: Decimal = Decimal(0)


class AsientoManualIn(BaseModel):
    fecha: date
    concepto: str = Field(..., max_length=500)
    partidas: List[PartidaIn] = Field(..., min_length=2)

    @model_validator(mode="after")
    def validar_partida_doble(self):
        total_debe  = sum(p.debe  for p in self.partidas)
        total_haber = sum(p.haber for p in self.partidas)
        if total_debe != total_haber:
            raise ValueError(
                f"Partida doble violada: debe={total_debe} ≠ haber={total_haber}"
            )
        return self


@router.post("/asientos", status_code=201, summary="Crear asiento manual (admin)")
async def crear_asiento_manual(
    data: AsientoManualIn,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    empresa_id = current_user["empresa_id"]
    usuario_id = current_user["sub"]

    partidas = [
        {"cuenta_id": str(p.cuenta_id), "debe": p.debe, "haber": p.haber}
        for p in data.partidas
    ]
    asiento_id = await _insertar_asiento(
        db, empresa_id, data.fecha, data.concepto,
        partidas=partidas, tipo="manual", usuario_id=usuario_id,
    )
    if not asiento_id:
        raise HTTPException(422, "No se pudo crear el asiento (cuentas no encontradas o desequilibrio)")

    from ..services.audit import registrar as _audit
    await _audit(db, usuario=current_user, accion="INSERT", tabla="asientos_contables",
                 registro_id=asiento_id,
                 datos_nuevos={"concepto": data.concepto, "fecha": str(data.fecha)})
    await db.commit()
    return {"id": asiento_id, "concepto": data.concepto}


# ── Libro Mayor ────────────────────────────────────────────────────────────────

@router.get("/mayor/{cuenta_id}", summary="Libro Mayor — movimientos de una cuenta")
async def mayor(
    cuenta_id: UUID,
    desde: Optional[date] = Query(None),
    hasta: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    resultado = await libro_mayor_cuenta(
        db, current_user["empresa_id"], str(cuenta_id), desde, hasta
    )
    if not resultado["cuenta"]:
        raise HTTPException(404, "Cuenta no encontrada")
    return resultado


# ── Estados financieros ────────────────────────────────────────────────────────

@router.get("/balance-comprobacion", summary="Balance de Comprobación (sumas y saldos)")
async def balance_comp(
    hasta: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return await balance_comprobacion(db, current_user["empresa_id"], hasta)


@router.get("/estado-resultados", summary="Estado de Resultados")
async def est_resultados(
    desde: date = Query(..., description="YYYY-MM-DD"),
    hasta: date = Query(..., description="YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if desde > hasta:
        raise HTTPException(422, "'desde' no puede ser posterior a 'hasta'")
    return await estado_resultados(db, current_user["empresa_id"], desde, hasta)


@router.get("/balance-general", summary="Balance General (Activo = Pasivo + Patrimonio)")
async def bal_general(
    hasta: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return await balance_general(db, current_user["empresa_id"], hasta)
