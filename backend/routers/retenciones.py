"""
Router de Retenciones — Fase J.1
Retenciones de IVA y Renta paraguayas vinculadas a comprobantes de compra.
"""
from decimal import Decimal
from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from ..core.database import get_db
from ..core.security import get_current_user, require_escritura
from ..services.audit import registrar as audit

router = APIRouter(prefix="/retenciones", tags=["Retenciones"])


class RetencioCreate(BaseModel):
    comprobante_id: Optional[UUID] = None
    proveedor_id: Optional[UUID] = None
    tipo: str = Field(..., pattern="^(iva|renta|ambos)$")
    porcentaje: Decimal = Field(..., gt=0, le=100, decimal_places=2)
    monto_base: Decimal = Field(..., ge=0, decimal_places=2)
    monto_retenido: Decimal = Field(..., ge=0, decimal_places=2)
    numero_certificado: Optional[str] = Field(None, max_length=50)
    fecha: str = Field(..., description="YYYY-MM-DD")
    notas: Optional[str] = Field(None, max_length=500)


@router.get("/", summary="Listar retenciones")
async def listar_retenciones(
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    tipo: Optional[str] = None,
    proveedor_id: Optional[UUID] = None,
    limite: int = Query(200, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    empresa_id = current_user["empresa_id"]
    filtros, params = "", {"eid": empresa_id, "limite": limite}

    if desde:
        filtros += " AND r.fecha >= :desde"; params["desde"] = desde
    if hasta:
        filtros += " AND r.fecha <= :hasta"; params["hasta"] = hasta
    if tipo:
        filtros += " AND r.tipo = :tipo"; params["tipo"] = tipo
    if proveedor_id:
        filtros += " AND r.proveedor_id = :prov_id"; params["prov_id"] = str(proveedor_id)

    result = await db.execute(
        text(f"""
            SELECT r.id, r.tipo, r.porcentaje, r.monto_base, r.monto_retenido,
                   r.numero_certificado, r.fecha, r.notas, r.fecha_creacion,
                   r.comprobante_id, c.numero_comprobante,
                   r.proveedor_id, pr.nombre AS proveedor_nombre,
                   TRIM(COALESCE(u.nombre,'') || ' ' || COALESCE(u.apellido,'')) AS registrado_por
            FROM retenciones r
            LEFT JOIN comprobantes c ON c.id = r.comprobante_id
            LEFT JOIN proveedores pr ON pr.id = r.proveedor_id
            LEFT JOIN usuarios u ON u.id = r.usuario_id
            WHERE r.empresa_id = :eid
            {filtros}
            ORDER BY r.fecha DESC, r.fecha_creacion DESC
            LIMIT :limite
        """),
        params,
    )
    filas = result.mappings().all()

    total_iva    = sum(r["monto_retenido"] for r in filas if r["tipo"] in ("iva", "ambos"))
    total_renta  = sum(r["monto_retenido"] for r in filas if r["tipo"] in ("renta", "ambos"))

    return {
        "retenciones": filas,
        "total_iva_retenido": total_iva,
        "total_renta_retenido": total_renta,
        "total_retenido": sum(r["monto_retenido"] for r in filas),
        "cantidad": len(filas),
    }


@router.post("/", status_code=status.HTTP_201_CREATED, summary="Registrar retención")
async def crear_retencion(
    data: RetencioCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_escritura),
):
    empresa_id = current_user["empresa_id"]

    # Verificar comprobante si se proporcionó
    if data.comprobante_id:
        row = (await db.execute(
            text("SELECT id, proveedor_id FROM comprobantes WHERE id = :id AND empresa_id = :eid"),
            {"id": str(data.comprobante_id), "eid": empresa_id},
        )).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail="Comprobante no encontrado")
        # Auto-asociar proveedor del comprobante si no se especificó
        if not data.proveedor_id and row["proveedor_id"]:
            data = data.model_copy(update={"proveedor_id": row["proveedor_id"]})

    result = await db.execute(
        text("""
            INSERT INTO retenciones
                (empresa_id, comprobante_id, proveedor_id, tipo, porcentaje,
                 monto_base, monto_retenido, numero_certificado, fecha, notas, usuario_id)
            VALUES
                (:eid, :comp_id, :prov_id, :tipo, :pct,
                 :base, :retenido, :cert, :fecha, :notas, :uid)
            RETURNING id, tipo, porcentaje, monto_base, monto_retenido,
                      numero_certificado, fecha, fecha_creacion
        """),
        {
            "eid": empresa_id,
            "comp_id": str(data.comprobante_id) if data.comprobante_id else None,
            "prov_id": str(data.proveedor_id) if data.proveedor_id else None,
            "tipo": data.tipo, "pct": data.porcentaje,
            "base": data.monto_base, "retenido": data.monto_retenido,
            "cert": data.numero_certificado, "fecha": data.fecha,
            "notas": data.notas, "uid": current_user["sub"],
        },
    )
    ret = result.mappings().first()
    await audit(db, usuario=current_user, accion="INSERT", tabla="retenciones",
                registro_id=str(ret["id"]),
                datos_nuevos={"tipo": data.tipo, "monto_retenido": str(data.monto_retenido)})
    await db.commit()
    return ret


@router.delete("/{retencion_id}", summary="Eliminar retención")
async def eliminar_retencion(
    retencion_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_escritura),
):
    empresa_id = current_user["empresa_id"]
    row = (await db.execute(
        text("SELECT id FROM retenciones WHERE id = :id AND empresa_id = :eid"),
        {"id": str(retencion_id), "eid": empresa_id},
    )).first()
    if not row:
        raise HTTPException(status_code=404, detail="Retención no encontrada")

    await db.execute(
        text("DELETE FROM retenciones WHERE id = :id AND empresa_id = :eid"),
        {"id": str(retencion_id), "eid": empresa_id},
    )
    await audit(db, usuario=current_user, accion="DELETE", tabla="retenciones",
                registro_id=str(retencion_id), datos_nuevos={})
    await db.commit()
    return {"mensaje": "Retención eliminada"}
