"""
Router Plan de Cuentas — Fase H.

CRUD del plan de cuentas jerárquico por empresa.
  GET    /plan-cuentas           — árbol de cuentas
  POST   /plan-cuentas           — crear cuenta (solo admin)
  PATCH  /plan-cuentas/{id}      — editar nombre/estado (solo admin)
  DELETE /plan-cuentas/{id}      — desactivar (solo si es hoja sin movimientos, solo admin)
"""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from ..core.database import get_db
from ..core.security import get_current_user, require_admin

router = APIRouter(prefix="/plan-cuentas", tags=["Plan de Cuentas"])


class CuentaCreate(BaseModel):
    codigo: str = Field(..., max_length=20, description="Ej: '1.1.05'")
    nombre: str = Field(..., max_length=200)
    tipo: str = Field(..., description="activo|pasivo|patrimonio|ingreso|egreso")
    naturaleza: str = Field(default="deudora", description="deudora|acreedora")
    cuenta_padre_id: UUID | None = None
    es_hoja: bool = True


class CuentaPatch(BaseModel):
    nombre: str | None = None
    activa: bool | None = None
    es_hoja: bool | None = None


@router.get("/", summary="Árbol de cuentas contables")
async def listar_plan(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    solo_hojas: bool = False,
):
    empresa_id = current_user["empresa_id"]
    filtro = "AND pc.es_hoja = TRUE" if solo_hojas else ""
    result = await db.execute(
        text(f"""
            SELECT pc.id, pc.codigo, pc.nombre, pc.tipo, pc.naturaleza,
                   pc.cuenta_padre_id, pc.es_hoja, pc.activa,
                   padre.codigo AS padre_codigo, padre.nombre AS padre_nombre,
                   COALESCE(SUM(da.debe),  0) AS total_debe,
                   COALESCE(SUM(da.haber), 0) AS total_haber
            FROM plan_cuentas pc
            LEFT JOIN plan_cuentas padre ON padre.id = pc.cuenta_padre_id
            LEFT JOIN detalle_asientos da ON da.cuenta_id = pc.id AND da.empresa_id = pc.empresa_id
            WHERE pc.empresa_id = :e {filtro}
            GROUP BY pc.id, pc.codigo, pc.nombre, pc.tipo, pc.naturaleza,
                     pc.cuenta_padre_id, pc.es_hoja, pc.activa,
                     padre.codigo, padre.nombre
            ORDER BY pc.codigo
        """),
        {"e": empresa_id},
    )
    rows = [dict(r) for r in result.mappings().all()]
    for r in rows:
        r["saldo"] = float(Decimal(str(r["total_debe"])) - Decimal(str(r["total_haber"])))
        r["total_debe"] = float(r["total_debe"])
        r["total_haber"] = float(r["total_haber"])
    return rows


@router.post("/", status_code=201, summary="Crear cuenta contable (admin)")
async def crear_cuenta(
    data: CuentaCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    empresa_id = current_user["empresa_id"]

    # Validar tipo y naturaleza
    if data.tipo not in ("activo","pasivo","patrimonio","ingreso","egreso","resultado"):
        raise HTTPException(400, "tipo inválido")
    if data.naturaleza not in ("deudora","acreedora"):
        raise HTTPException(400, "naturaleza inválida")

    # Verificar código único
    existe = (await db.execute(
        text("SELECT 1 FROM plan_cuentas WHERE empresa_id = :e AND codigo = :c"),
        {"e": empresa_id, "c": data.codigo},
    )).first()
    if existe:
        raise HTTPException(409, f"Ya existe una cuenta con código {data.codigo}")

    # Si tiene padre, marcar padre como no-hoja
    if data.cuenta_padre_id:
        await db.execute(
            text("UPDATE plan_cuentas SET es_hoja = FALSE WHERE id = :id AND empresa_id = :e"),
            {"id": str(data.cuenta_padre_id), "e": empresa_id},
        )

    row = (await db.execute(
        text("""
            INSERT INTO plan_cuentas
                (empresa_id, codigo, nombre, tipo, naturaleza, cuenta_padre_id, es_hoja)
            VALUES (:e, :codigo, :nombre, :tipo, :naturaleza, :padre, :es_hoja)
            RETURNING id, codigo, nombre, tipo, naturaleza, cuenta_padre_id, es_hoja, activa
        """),
        {
            "e": empresa_id,
            "codigo": data.codigo,
            "nombre": data.nombre,
            "tipo": data.tipo,
            "naturaleza": data.naturaleza,
            "padre": str(data.cuenta_padre_id) if data.cuenta_padre_id else None,
            "es_hoja": data.es_hoja,
        },
    )).mappings().first()

    await db.commit()
    return dict(row)


@router.patch("/{cuenta_id}", summary="Editar cuenta contable (admin)")
async def editar_cuenta(
    cuenta_id: UUID,
    data: CuentaPatch,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    empresa_id = current_user["empresa_id"]
    sets, params = [], {"id": str(cuenta_id), "e": empresa_id}
    if data.nombre is not None:
        sets.append("nombre = :nombre"); params["nombre"] = data.nombre
    if data.activa is not None:
        sets.append("activa = :activa"); params["activa"] = data.activa
    if data.es_hoja is not None:
        sets.append("es_hoja = :es_hoja"); params["es_hoja"] = data.es_hoja
    if not sets:
        raise HTTPException(422, "Sin campos para actualizar")
    await db.execute(
        text(f"UPDATE plan_cuentas SET {', '.join(sets)} WHERE id = :id AND empresa_id = :e"),
        params,
    )
    await db.commit()
    return {"ok": True}


@router.delete("/{cuenta_id}", summary="Desactivar cuenta (admin)")
async def desactivar_cuenta(
    cuenta_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    empresa_id = current_user["empresa_id"]

    # Verificar que no tenga movimientos
    tiene_movs = (await db.execute(
        text("SELECT 1 FROM detalle_asientos WHERE cuenta_id = :id AND empresa_id = :e LIMIT 1"),
        {"id": str(cuenta_id), "e": empresa_id},
    )).first()
    if tiene_movs:
        raise HTTPException(409, "No se puede desactivar: la cuenta tiene movimientos registrados")

    await db.execute(
        text("UPDATE plan_cuentas SET activa = FALSE WHERE id = :id AND empresa_id = :e"),
        {"id": str(cuenta_id), "e": empresa_id},
    )
    await db.commit()
    return {"ok": True}


# Import necesario para cálculos
from decimal import Decimal
