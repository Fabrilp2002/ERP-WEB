"""
Router de Cuentas Bancarias y Movimientos de Banco — Fase I.
Gestiona el efectivo/saldos de las cuentas bancarias de la empresa.
"""
from decimal import Decimal
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from datetime import date
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from ..core.database import get_db
from ..core.security import get_current_user, require_escritura, require_admin
from ..services.audit import registrar as audit

router = APIRouter(prefix="/bancos", tags=["Bancos"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class CuentaBancoCreate(BaseModel):
    banco: str = Field(..., min_length=2, max_length=100)
    numero_cuenta: Optional[str] = Field(None, max_length=50)
    tipo: str = Field("corriente", pattern="^(corriente|ahorro|caja_chica)$")
    moneda: str = Field("PYG", max_length=10)
    saldo_inicial: Decimal = Field(Decimal("0"), ge=0)

class CuentaBancoUpdate(BaseModel):
    banco: Optional[str] = None
    numero_cuenta: Optional[str] = None
    activa: Optional[bool] = None

class MovimientoManualCreate(BaseModel):
    fecha: str = Field(..., description="YYYY-MM-DD")
    tipo: str = Field(..., pattern="^(debito|credito)$")
    monto: Decimal = Field(..., gt=0)
    descripcion: str = Field(..., min_length=3, max_length=300)
    referencia: Optional[str] = Field(None, max_length=100)


# ── Cuentas ───────────────────────────────────────────────────────────────────

@router.get("/", summary="Listar cuentas bancarias")
async def listar_cuentas(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    empresa_id = current_user["empresa_id"]
    result = await db.execute(
        text("""
            SELECT cb.id, cb.banco, cb.numero_cuenta, cb.tipo, cb.moneda,
                   cb.saldo_actual, cb.activa, cb.fecha_creacion,
                   COUNT(mb.id) AS total_movimientos
            FROM cuentas_banco cb
            LEFT JOIN movimientos_banco mb ON mb.cuenta_banco_id = cb.id
            WHERE cb.empresa_id = :empresa_id
            GROUP BY cb.id
            ORDER BY cb.banco, cb.tipo
        """),
        {"empresa_id": empresa_id},
    )
    return result.mappings().all()


@router.post("/", status_code=status.HTTP_201_CREATED, summary="Crear cuenta bancaria")
async def crear_cuenta(
    data: CuentaBancoCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_escritura),
):
    empresa_id = current_user["empresa_id"]
    result = await db.execute(
        text("""
            INSERT INTO cuentas_banco (empresa_id, banco, numero_cuenta, tipo, moneda, saldo_actual)
            VALUES (:empresa_id, :banco, :numero, :tipo, :moneda, :saldo)
            RETURNING id, banco, numero_cuenta, tipo, moneda, saldo_actual, activa, fecha_creacion
        """),
        {
            "empresa_id": empresa_id,
            "banco": data.banco.strip(),
            "numero": data.numero_cuenta,
            "tipo": data.tipo,
            "moneda": data.moneda,
            "saldo": data.saldo_inicial,
        },
    )
    cuenta = result.mappings().first()

    # Si tiene saldo inicial, registrar movimiento de apertura
    if data.saldo_inicial > 0:
        await db.execute(
            text("""
                INSERT INTO movimientos_banco
                    (empresa_id, cuenta_banco_id, fecha, tipo, monto, descripcion, usuario_id)
                VALUES (:eid, :cid, :fecha, 'credito', :monto, 'Saldo inicial de apertura', :uid)
            """),
            {"eid": empresa_id, "cid": str(cuenta["id"]),
             "fecha": date.today().isoformat(),
             "monto": data.saldo_inicial, "uid": current_user["sub"]},
        )

    await audit(db, usuario=current_user, accion="INSERT", tabla="cuentas_banco",
                registro_id=str(cuenta["id"]),
                datos_nuevos={"banco": data.banco, "tipo": data.tipo})
    await db.commit()
    return cuenta


@router.patch("/{cuenta_id}", summary="Editar cuenta bancaria")
async def editar_cuenta(
    cuenta_id: UUID,
    data: CuentaBancoUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_escritura),
):
    empresa_id = current_user["empresa_id"]
    sets = []
    params: dict = {"id": str(cuenta_id), "empresa_id": empresa_id}
    if data.banco is not None:
        sets.append("banco = :banco"); params["banco"] = data.banco.strip()
    if data.numero_cuenta is not None:
        sets.append("numero_cuenta = :numero"); params["numero"] = data.numero_cuenta
    if data.activa is not None:
        sets.append("activa = :activa"); params["activa"] = data.activa
    if not sets:
        raise HTTPException(status_code=422, detail="Nada que actualizar")

    await db.execute(
        text(f"UPDATE cuentas_banco SET {', '.join(sets)} WHERE id = :id AND empresa_id = :empresa_id"),
        params,
    )
    await audit(db, usuario=current_user, accion="UPDATE", tabla="cuentas_banco",
                registro_id=str(cuenta_id), datos_nuevos=dict(data.model_dump(exclude_none=True)))
    await db.commit()
    return {"mensaje": "Cuenta actualizada"}


# ── Movimientos ───────────────────────────────────────────────────────────────

@router.get("/{cuenta_id}/movimientos", summary="Movimientos de una cuenta")
async def listar_movimientos(
    cuenta_id: UUID,
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    limite: int = Query(200, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    empresa_id = current_user["empresa_id"]

    # Verificar que la cuenta pertenece a la empresa
    row = (await db.execute(
        text("SELECT id, banco, saldo_actual FROM cuentas_banco WHERE id = :id AND empresa_id = :eid"),
        {"id": str(cuenta_id), "eid": empresa_id},
    )).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")

    filtros = ""
    params: dict = {"eid": empresa_id, "cid": str(cuenta_id), "limite": limite}
    if desde:
        filtros += " AND mb.fecha >= :desde"; params["desde"] = desde
    if hasta:
        filtros += " AND mb.fecha <= :hasta"; params["hasta"] = hasta

    result = await db.execute(
        text(f"""
            SELECT mb.id, mb.fecha, mb.tipo, mb.monto, mb.descripcion, mb.referencia,
                   mb.comprobante_id,
                   NULLIF(TRIM(COALESCE(u.nombre,'') || ' ' || COALESCE(u.apellido,'')), '') AS registrado_por,
                   c.numero_comprobante,
                   SUM(CASE mb2.tipo WHEN 'credito' THEN mb2.monto ELSE -mb2.monto END)
                       OVER (PARTITION BY mb.cuenta_banco_id ORDER BY mb.fecha, mb.fecha_creacion
                             ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS saldo_acumulado
            FROM movimientos_banco mb
            LEFT JOIN usuarios u ON u.id = mb.usuario_id
            LEFT JOIN comprobantes c ON c.id = mb.comprobante_id
            LEFT JOIN movimientos_banco mb2 ON mb2.cuenta_banco_id = mb.cuenta_banco_id
                AND mb2.empresa_id = mb.empresa_id
            WHERE mb.empresa_id = :eid AND mb.cuenta_banco_id = :cid
            {filtros}
            ORDER BY mb.fecha DESC, mb.fecha_creacion DESC
            LIMIT :limite
        """),
        params,
    )
    movs = result.mappings().all()

    return {
        "cuenta": dict(row),
        "movimientos": movs,
        "total_creditos": sum(m["monto"] for m in movs if m["tipo"] == "credito"),
        "total_debitos":  sum(m["monto"] for m in movs if m["tipo"] == "debito"),
    }


@router.post("/{cuenta_id}/movimientos", status_code=status.HTTP_201_CREATED,
             summary="Registrar movimiento manual (depósito, retiro, comisión)")
async def crear_movimiento(
    cuenta_id: UUID,
    data: MovimientoManualCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_escritura),
):
    empresa_id = current_user["empresa_id"]

    # Verificar cuenta activa
    row = (await db.execute(
        text("SELECT id, saldo_actual, activa FROM cuentas_banco WHERE id = :id AND empresa_id = :eid"),
        {"id": str(cuenta_id), "eid": empresa_id},
    )).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")
    if not row["activa"]:
        raise HTTPException(status_code=409, detail="La cuenta está inactiva")

    # Insertar movimiento
    await db.execute(
        text("""
            INSERT INTO movimientos_banco
                (empresa_id, cuenta_banco_id, fecha, tipo, monto, descripcion, referencia, usuario_id)
            VALUES (:eid, :cid, :fecha, :tipo, :monto, :desc, :ref, :uid)
        """),
        {
            "eid": empresa_id, "cid": str(cuenta_id),
            "fecha": data.fecha, "tipo": data.tipo,
            "monto": data.monto, "desc": data.descripcion.strip(),
            "ref": data.referencia, "uid": current_user["sub"],
        },
    )

    # Actualizar saldo
    delta = data.monto if data.tipo == "credito" else -data.monto
    await db.execute(
        text("UPDATE cuentas_banco SET saldo_actual = saldo_actual + :delta WHERE id = :id"),
        {"delta": delta, "id": str(cuenta_id)},
    )

    await audit(db, usuario=current_user, accion="INSERT", tabla="movimientos_banco",
                registro_id=str(cuenta_id),
                datos_nuevos={"tipo": data.tipo, "monto": str(data.monto), "fecha": data.fecha})
    await db.commit()
    return {"mensaje": "Movimiento registrado", "delta_saldo": float(delta)}
