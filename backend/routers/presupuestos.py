"""
Router de Presupuestos — Fase J.3
CRUD de presupuestos por período + comparativo real vs presupuestado.
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

router = APIRouter(prefix="/presupuestos", tags=["Presupuestos"])


class PresupuestoCreate(BaseModel):
    nombre: str = Field(..., min_length=3, max_length=200)
    periodo_inicio: str = Field(..., description="YYYY-MM-DD")
    periodo_fin: str = Field(..., description="YYYY-MM-DD")
    notas: Optional[str] = Field(None, max_length=1000)
    detalle: list[dict] = Field(default_factory=list,
        description="[{cuenta_id, monto_presupuestado, notas?}]")


class PresupuestoUpdate(BaseModel):
    nombre: Optional[str] = None
    estado: Optional[str] = Field(None, pattern="^(borrador|activo|cerrado)$")
    notas: Optional[str] = None


@router.get("/", summary="Listar presupuestos")
async def listar_presupuestos(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    empresa_id = current_user["empresa_id"]
    result = await db.execute(
        text("""
            SELECT p.id, p.nombre, p.periodo_inicio, p.periodo_fin, p.estado,
                   p.notas, p.fecha_creacion,
                   COALESCE(SUM(dp.monto_presupuestado), 0) AS total_presupuestado,
                   COUNT(dp.id) AS total_cuentas
            FROM presupuestos p
            LEFT JOIN detalle_presupuesto dp ON dp.presupuesto_id = p.id
            WHERE p.empresa_id = :eid
            GROUP BY p.id
            ORDER BY p.periodo_inicio DESC, p.nombre
        """),
        {"eid": empresa_id},
    )
    return result.mappings().all()


@router.post("/", status_code=status.HTTP_201_CREATED, summary="Crear presupuesto")
async def crear_presupuesto(
    data: PresupuestoCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_escritura),
):
    empresa_id = current_user["empresa_id"]

    result = await db.execute(
        text("""
            INSERT INTO presupuestos
                (empresa_id, nombre, periodo_inicio, periodo_fin, notas, usuario_id)
            VALUES (:eid, :nombre, :inicio, :fin, :notas, :uid)
            RETURNING id, nombre, periodo_inicio, periodo_fin, estado, fecha_creacion
        """),
        {
            "eid": empresa_id, "nombre": data.nombre.strip(),
            "inicio": data.periodo_inicio, "fin": data.periodo_fin,
            "notas": data.notas, "uid": current_user["sub"],
        },
    )
    pres = result.mappings().first()
    pres_id = str(pres["id"])

    # Insertar líneas
    for item in data.detalle:
        if not item.get("cuenta_id") or not item.get("monto_presupuestado"):
            continue
        await db.execute(
            text("""
                INSERT INTO detalle_presupuesto
                    (empresa_id, presupuesto_id, cuenta_id, monto_presupuestado, notas)
                VALUES (:eid, :pid, :cid, :monto, :notas)
                ON CONFLICT (presupuesto_id, cuenta_id) DO UPDATE
                    SET monto_presupuestado = EXCLUDED.monto_presupuestado
            """),
            {
                "eid": empresa_id, "pid": pres_id,
                "cid": str(item["cuenta_id"]),
                "monto": Decimal(str(item["monto_presupuestado"])),
                "notas": item.get("notas"),
            },
        )

    await audit(db, usuario=current_user, accion="INSERT", tabla="presupuestos",
                registro_id=pres_id, datos_nuevos={"nombre": data.nombre})
    await db.commit()
    return dict(pres)


@router.patch("/{presupuesto_id}", summary="Editar presupuesto")
async def editar_presupuesto(
    presupuesto_id: UUID,
    data: PresupuestoUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_escritura),
):
    empresa_id = current_user["empresa_id"]
    sets, params = [], {"id": str(presupuesto_id), "eid": empresa_id}

    if data.nombre is not None:
        sets.append("nombre = :nombre"); params["nombre"] = data.nombre.strip()
    if data.estado is not None:
        sets.append("estado = :estado"); params["estado"] = data.estado
    if data.notas is not None:
        sets.append("notas = :notas"); params["notas"] = data.notas
    if not sets:
        raise HTTPException(status_code=422, detail="Nada que actualizar")

    await db.execute(
        text(f"UPDATE presupuestos SET {', '.join(sets)} WHERE id = :id AND empresa_id = :eid"),
        params,
    )
    await audit(db, usuario=current_user, accion="UPDATE", tabla="presupuestos",
                registro_id=str(presupuesto_id),
                datos_nuevos=data.model_dump(exclude_none=True))
    await db.commit()
    return {"mensaje": "Presupuesto actualizado"}


@router.get("/{presupuesto_id}/comparativo", summary="Comparativo real vs presupuestado")
async def comparativo(
    presupuesto_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Para cada cuenta del presupuesto, muestra:
      monto_presupuestado vs movimiento_real (SUM del libro mayor en el período).
    El real se obtiene de los asientos contables (detalle_asientos) en el rango del presupuesto.
    """
    empresa_id = current_user["empresa_id"]

    # Datos del presupuesto
    pres = (await db.execute(
        text("""
            SELECT id, nombre, periodo_inicio, periodo_fin, estado
            FROM presupuestos WHERE id = :id AND empresa_id = :eid
        """),
        {"id": str(presupuesto_id), "eid": empresa_id},
    )).mappings().first()
    if not pres:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado")

    # Comparativo por cuenta
    result = await db.execute(
        text("""
            SELECT
                pc.codigo,
                pc.nombre                           AS cuenta_nombre,
                pc.tipo,
                pc.naturaleza,
                dp.monto_presupuestado,
                COALESCE(SUM(
                    CASE
                        WHEN a.fecha BETWEEN :inicio AND :fin THEN
                            CASE pc.naturaleza
                                WHEN 'deudora' THEN da.debe - da.haber
                                ELSE da.haber - da.debe
                            END
                        ELSE 0
                    END
                ), 0) AS monto_real,
                COALESCE(SUM(
                    CASE
                        WHEN a.fecha BETWEEN :inicio AND :fin THEN
                            CASE pc.naturaleza
                                WHEN 'deudora' THEN da.debe - da.haber
                                ELSE da.haber - da.debe
                            END
                        ELSE 0
                    END
                ), 0) - dp.monto_presupuestado AS diferencia
            FROM detalle_presupuesto dp
            JOIN plan_cuentas pc ON pc.id = dp.cuenta_id
            LEFT JOIN detalle_asientos da ON da.cuenta_id = dp.cuenta_id
                AND da.empresa_id = :eid
            LEFT JOIN asientos_contables a ON a.id = da.asiento_id
                AND a.empresa_id = :eid
            WHERE dp.presupuesto_id = :pid
              AND dp.empresa_id = :eid
            GROUP BY pc.codigo, pc.nombre, pc.tipo, pc.naturaleza, dp.monto_presupuestado
            ORDER BY pc.codigo
        """),
        {
            "pid": str(presupuesto_id), "eid": empresa_id,
            "inicio": pres["periodo_inicio"], "fin": pres["periodo_fin"],
        },
    )
    lineas = result.mappings().all()

    total_presupuestado = sum(l["monto_presupuestado"] for l in lineas)
    total_real = sum(l["monto_real"] for l in lineas)

    return {
        "presupuesto": dict(pres),
        "lineas": lineas,
        "totales": {
            "presupuestado": total_presupuestado,
            "real": total_real,
            "diferencia": total_real - total_presupuestado,
            "ejecucion_pct": round((float(total_real) / float(total_presupuestado) * 100), 1) if total_presupuestado else 0,
        },
    }


@router.delete("/{presupuesto_id}", summary="Eliminar presupuesto (solo borrador)")
async def eliminar_presupuesto(
    presupuesto_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_escritura),
):
    empresa_id = current_user["empresa_id"]
    row = (await db.execute(
        text("SELECT estado FROM presupuestos WHERE id = :id AND empresa_id = :eid"),
        {"id": str(presupuesto_id), "eid": empresa_id},
    )).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado")
    if row["estado"] != "borrador":
        raise HTTPException(status_code=409, detail="Solo se pueden eliminar presupuestos en estado 'borrador'")

    await db.execute(
        text("DELETE FROM presupuestos WHERE id = :id AND empresa_id = :eid"),
        {"id": str(presupuesto_id), "eid": empresa_id},
    )
    await audit(db, usuario=current_user, accion="DELETE", tabla="presupuestos",
                registro_id=str(presupuesto_id), datos_nuevos={})
    await db.commit()
    return {"mensaje": "Presupuesto eliminado"}
