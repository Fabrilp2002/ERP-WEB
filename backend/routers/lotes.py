"""
Router v7.1 — endpoints de lotes de inventario.

Listar / crear lotes, listar próximos vencimientos.
La integración con ventas (consumo FEFO automático al facturar) queda para v7.2.
"""
from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..core.security import get_current_user, require_escritura
from ..services.lotes import (
    LoteError,
    crear_lote,
    listar_lotes_item,
    listar_todos_los_lotes,
    proximos_vencimientos,
)


router = APIRouter(prefix="/inventario/lotes", tags=["Inventario - Lotes"])


# ── Schemas ──────────────────────────────────────────────────────────────────

class LoteCreate(BaseModel):
    inventario_id: UUID
    numero_lote: str = Field(min_length=1, max_length=50)
    cantidad: Decimal = Field(gt=0)
    costo_unitario: Decimal = Field(ge=0)
    fecha_ingreso: date | None = None
    fecha_vencimiento: date | None = None
    proveedor_id: UUID | None = None
    comprobante_id: UUID | None = None
    notas: str | None = None


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/", summary="Listar todos los lotes vivos")
async def listar_lotes(
    solo_con_vencimiento: bool = Query(False),
    limit: int = Query(200, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return await listar_todos_los_lotes(
        db,
        empresa_id=current_user["empresa_id"],
        solo_con_vencimiento=solo_con_vencimiento,
        limit=limit,
    )


@router.get("/por-item/{inventario_id}", summary="Lotes de un item específico")
async def lotes_por_item(
    inventario_id: UUID,
    incluir_agotados: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return await listar_lotes_item(
        db,
        empresa_id=current_user["empresa_id"],
        inventario_id=str(inventario_id),
        incluir_agotados=incluir_agotados,
    )


@router.get("/vencimientos", summary="Lotes próximos a vencer (o ya vencidos)")
async def vencimientos(
    dias: int | None = Query(None, description="Override del default de la empresa."),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return await proximos_vencimientos(
        db,
        empresa_id=current_user["empresa_id"],
        dias=dias,
    )


@router.post("/", status_code=201, summary="Registrar un lote nuevo (ingreso de mercadería)")
async def crear_lote_endpoint(
    data: LoteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_escritura),
):
    try:
        resultado = await crear_lote(
            db,
            empresa_id=current_user["empresa_id"],
            inventario_id=str(data.inventario_id),
            numero_lote=data.numero_lote,
            cantidad=data.cantidad,
            costo_unitario=data.costo_unitario,
            fecha_ingreso=data.fecha_ingreso,
            fecha_vencimiento=data.fecha_vencimiento,
            proveedor_id=str(data.proveedor_id) if data.proveedor_id else None,
            comprobante_id=str(data.comprobante_id) if data.comprobante_id else None,
            usuario_id=current_user.get("sub"),
            notas=data.notas,
        )
        await db.commit()
        return resultado
    except LoteError as exc:
        await db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)
