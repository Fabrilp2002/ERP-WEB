"""
Router de pagos / recibos — Fase C.

Registra cobros (pagos recibidos de clientes) y pagos (a proveedores).
Cada pago referencia a un comprobante y actualiza su saldo_pendiente.
"""
from datetime import date
from decimal import Decimal
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from ..core.database import get_db
from ..core.security import get_current_user, require_admin, require_escritura
from ..models.schemas import PagoCreate
import logging as _logging
from ..services.contabilidad import revertir_asiento_pago
from ..services.pagos_service import registrar_pago_core, RegistrarPagoError
from ..services.analisis_contraparte import analizar_contraparte

router = APIRouter(prefix="/pagos", tags=["Pagos / Recibos"])


@router.get("/", summary="Listar pagos (opcionalmente filtrados por comprobante)")
async def listar_pagos(
    comprobante_id: UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    empresa_id = current_user["empresa_id"]
    filtro = "AND p.comprobante_id = :comprobante_id" if comprobante_id else ""
    params = {"empresa_id": empresa_id}
    if comprobante_id:
        params["comprobante_id"] = str(comprobante_id)

    result = await db.execute(
        text(f"""
            SELECT p.id, p.comprobante_id, p.numero_recibo, p.fecha_pago,
                   p.monto_pagado, p.medio_pago, p.notas, p.ruta_adjunto, p.fecha_creacion,
                   TRIM(COALESCE(u.nombre, '') || ' ' || COALESCE(u.apellido, '')) AS usuario_nombre
            FROM pagos p
            LEFT JOIN usuarios u ON u.id = p.usuario_id
            WHERE p.empresa_id = :empresa_id {filtro}
            ORDER BY p.fecha_pago DESC, p.fecha_creacion DESC
        """),
        params,
    )
    return result.mappings().all()


@router.get("/movimientos", summary="Todos los movimientos (cobros + pagos) con contraparte")
async def listar_movimientos(
    tipo: str | None = Query(None, description="'cobro' (venta), 'pago' (compra) o None para todos"),
    desde: str | None = Query(None, description="YYYY-MM-DD inclusive"),
    hasta: str | None = Query(None, description="YYYY-MM-DD inclusive"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Devuelve todos los pagos de la empresa con el nombre de la contraparte
    (cliente o proveedor), el numero del comprobante al que imputa, y el tipo
    del movimiento (cobro de cliente = ingreso / pago a proveedor = egreso).
    """
    empresa_id = current_user["empresa_id"]
    filtros = []
    params: dict = {"empresa_id": empresa_id}
    if tipo == "cobro":
        filtros.append("c.cliente_id IS NOT NULL")
    elif tipo == "pago":
        filtros.append("c.proveedor_id IS NOT NULL")
    # Convertimos a `date` Python para que asyncpg infiera el tipo correctamente
    # (mezclar CAST(:bind AS DATE) con valores TEXT confunde la inferencia y rompe
    # con 500). Si la fecha viene mal formada, ignoramos el filtro.
    if desde:
        try:
            params["desde"] = date.fromisoformat(desde)
            filtros.append("p.fecha_pago >= :desde")
        except ValueError:
            pass
    if hasta:
        try:
            params["hasta"] = date.fromisoformat(hasta)
            filtros.append("p.fecha_pago <= :hasta")
        except ValueError:
            pass
    where_extra = (" AND " + " AND ".join(filtros)) if filtros else ""

    result = await db.execute(
        text(f"""
            SELECT
                p.id,
                p.comprobante_id,
                c.numero_comprobante,
                c.cliente_id,
                c.proveedor_id,
                CASE WHEN c.cliente_id IS NOT NULL THEN 'cobro' ELSE 'pago' END AS tipo,
                COALESCE(cl.nombre, pr.nombre, '—') AS contraparte,
                COALESCE(cl.ruc, pr.ruc, '') AS contraparte_ruc,
                p.numero_recibo,
                p.fecha_pago,
                p.monto_pagado,
                p.medio_pago,
                p.notas,
                p.ruta_adjunto,
                p.fecha_creacion,
                TRIM(COALESCE(u.nombre, '') || ' ' || COALESCE(u.apellido, '')) AS usuario_nombre
            FROM pagos p
            JOIN comprobantes c    ON c.id = p.comprobante_id
            LEFT JOIN clientes cl  ON cl.id = c.cliente_id
            LEFT JOIN proveedores pr ON pr.id = c.proveedor_id
            LEFT JOIN usuarios u   ON u.id = p.usuario_id
            WHERE p.empresa_id = :empresa_id {where_extra}
            ORDER BY p.fecha_pago DESC, p.fecha_creacion DESC
        """),
        params,
    )
    filas = [dict(r) for r in result.mappings().all()]

    total_cobros = sum((Decimal(str(r["monto_pagado"])) for r in filas if r["tipo"] == "cobro"), Decimal(0))
    total_pagos = sum((Decimal(str(r["monto_pagado"])) for r in filas if r["tipo"] == "pago"), Decimal(0))
    return {
        "movimientos": filas,
        "total_cobros": float(total_cobros),
        "total_pagos": float(total_pagos),
        "balance": float(total_cobros - total_pagos),
        "cantidad": len(filas),
    }


@router.post("/", status_code=201, summary="Registrar un pago / cobro")
async def registrar_pago(
    data: PagoCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_escritura),
):
    """Registra un pago contra un comprobante y actualiza su saldo_pendiente."""
    try:
        return await registrar_pago_core(
            db=db,
            empresa_id=current_user["empresa_id"],
            usuario=current_user,
            comprobante_id=str(data.comprobante_id),
            monto_pagado=data.monto_pagado,
            medio_pago=data.medio_pago,
            fecha_pago=data.fecha_pago,
            numero_recibo=data.numero_recibo,
            notas=data.notas,
            cuenta_banco_id=str(data.cuenta_banco_id) if data.cuenta_banco_id else None,
        )
    except RegistrarPagoError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)


@router.delete("/{pago_id}", summary="Eliminar un pago (revierte el saldo)")
async def eliminar_pago(
    pago_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    """
    Elimina un pago y devuelve su monto al saldo pendiente del comprobante.
    Útil cuando se registró un pago por error.
    """
    empresa_id = current_user["empresa_id"]

    pago = (await db.execute(
        text("""
            SELECT comprobante_id, monto_pagado FROM pagos
            WHERE id = :id AND empresa_id = :empresa_id
        """),
        {"id": str(pago_id), "empresa_id": empresa_id},
    )).mappings().first()
    if not pago:
        raise HTTPException(status_code=404, detail="Pago no encontrado")

    # Revertir asiento contable ANTES de eliminar el pago (la FK aún existe)
    try:
        await revertir_asiento_pago(db, empresa_id, str(pago_id), current_user["sub"])
    except Exception as exc:
        _logging.getLogger(__name__).warning(
            "Reversión asiento pago falló (no crítico): %s", exc
        )

    await db.execute(
        text("DELETE FROM pagos WHERE id = :id AND empresa_id = :empresa_id"),
        {"id": str(pago_id), "empresa_id": empresa_id},
    )
    # Revertir el saldo
    await db.execute(
        text("""
            UPDATE comprobantes
            SET saldo_pendiente = saldo_pendiente + :monto, fecha_modificacion = NOW()
            WHERE id = :id AND empresa_id = :empresa_id
        """),
        {
            "id": str(pago["comprobante_id"]),
            "empresa_id": empresa_id,
            "monto": pago["monto_pagado"],
        },
    )
    from ..services.audit import registrar as _audit
    await _audit(db, usuario=current_user, accion="DELETE", tabla="pagos",
                 registro_id=str(pago_id),
                 datos_anteriores={"comprobante_id": str(pago["comprobante_id"]),
                                   "monto": float(pago["monto_pagado"])})
    await db.commit()
    return {"mensaje": "Pago eliminado y saldo restituido"}


# ── Análisis histórico por cliente / proveedor ───────────────────────────────


@router.get("/analisis-cliente/{cliente_id}", summary="Análisis histórico de un cliente")
async def analisis_cliente(
    cliente_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    try:
        return await analizar_contraparte(
            db=db,
            empresa_id=current_user["empresa_id"],
            rol="cliente",
            contraparte_id=str(cliente_id),
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/analisis-proveedor/{proveedor_id}", summary="Análisis histórico de un proveedor")
async def analisis_proveedor(
    proveedor_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    try:
        return await analizar_contraparte(
            db=db,
            empresa_id=current_user["empresa_id"],
            rol="proveedor",
            contraparte_id=str(proveedor_id),
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ── Saldos de cuentas corrientes ──────────────────────────────────────────────

@router.get("/saldos/clientes", summary="Saldos pendientes por cliente")
async def saldos_clientes(
    solo_con_deuda: bool = Query(False, description="Si True, solo clientes con saldo > 0"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Resumen de cuentas corrientes por cliente usando la vista v_saldo_clientes."""
    empresa_id = current_user["empresa_id"]
    filtro = "AND saldo_pendiente > 0" if solo_con_deuda else ""
    result = await db.execute(
        text(f"""
            SELECT cliente_id, cliente, total_facturado, total_cobrado, saldo_pendiente
            FROM v_saldo_clientes
            WHERE empresa_id = :empresa_id {filtro}
            ORDER BY saldo_pendiente DESC, cliente ASC
        """),
        {"empresa_id": empresa_id},
    )
    return result.mappings().all()


@router.get("/saldos/proveedores", summary="Saldos pendientes por proveedor")
async def saldos_proveedores(
    solo_con_deuda: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Resumen de cuentas corrientes por proveedor usando la vista v_saldo_proveedores."""
    empresa_id = current_user["empresa_id"]
    filtro = "AND saldo_pendiente > 0" if solo_con_deuda else ""
    result = await db.execute(
        text(f"""
            SELECT proveedor_id, proveedor, total_facturado, total_pagado, saldo_pendiente
            FROM v_saldo_proveedores
            WHERE empresa_id = :empresa_id {filtro}
            ORDER BY saldo_pendiente DESC, proveedor ASC
        """),
        {"empresa_id": empresa_id},
    )
    return result.mappings().all()


@router.get("/cliente/{cliente_id}/historial", summary="Historial completo de un cliente")
async def historial_cliente(
    cliente_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Estado de cuenta detallado: todas las facturas del cliente + todos sus pagos,
    ordenados cronológicamente para ver la evolución del saldo.
    """
    empresa_id = current_user["empresa_id"]

    facturas = (await db.execute(
        text("""
            SELECT id, numero_comprobante, fecha_emision, fecha_vencimiento,
                   monto_total, saldo_pendiente, estado_validacion,
                   CASE
                     WHEN estado_validacion = 'anulado' THEN 'anulado'
                     WHEN estado_validacion = 'rechazado' THEN 'rechazado'
                     WHEN monto_total <= 0 THEN 'no_aplica'
                     WHEN saldo_pendiente >= monto_total THEN 'no_pagado'
                     WHEN saldo_pendiente <= 0 THEN 'pagado'
                     ELSE 'pago_parcial'
                   END AS estado_pago,
                   condicion, medio_pago_contado,
                   ruta_archivo
            FROM comprobantes
            WHERE cliente_id = :cliente_id AND empresa_id = :empresa_id
            ORDER BY fecha_emision DESC
        """),
        {"cliente_id": str(cliente_id), "empresa_id": empresa_id},
    )).mappings().all()

    nombre = (await db.execute(
        text("SELECT nombre FROM clientes WHERE id = :id AND empresa_id = :e"),
        {"id": str(cliente_id), "e": empresa_id},
    )).scalar() or "—"

    pagos = (await db.execute(
        text("""
            SELECT p.id, p.comprobante_id, p.numero_recibo, p.fecha_pago,
                   p.monto_pagado, p.medio_pago, p.notas, p.ruta_adjunto,
                   c.numero_comprobante
            FROM pagos p
            JOIN comprobantes c ON c.id = p.comprobante_id
            WHERE c.cliente_id = :cliente_id AND p.empresa_id = :empresa_id
            ORDER BY p.fecha_pago DESC
        """),
        {"cliente_id": str(cliente_id), "empresa_id": empresa_id},
    )).mappings().all()

    total_facturado = sum((f["monto_total"] for f in facturas), Decimal(0))
    total_cobrado = sum((p["monto_pagado"] for p in pagos), Decimal(0))
    saldo = sum((f["saldo_pendiente"] for f in facturas if f["estado_validacion"] not in ("anulado", "rechazado")), Decimal(0))

    return {
        "cliente_id": str(cliente_id),
        "nombre": nombre,
        "total_facturado": float(total_facturado),
        "total_cobrado": float(total_cobrado),
        "saldo_pendiente": float(saldo),
        "facturas": [dict(f) for f in facturas],
        "pagos": [dict(p) for p in pagos],
    }


@router.get("/proveedor/{proveedor_id}/historial", summary="Historial completo de un proveedor")
async def historial_proveedor(
    proveedor_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Estado de cuenta detallado del proveedor: todas las facturas recibidas + pagos emitidos."""
    empresa_id = current_user["empresa_id"]

    facturas = (await db.execute(
        text("""
            SELECT id, numero_comprobante, fecha_emision, fecha_vencimiento,
                   monto_total, saldo_pendiente, estado_validacion,
                   CASE
                     WHEN estado_validacion = 'anulado' THEN 'anulado'
                     WHEN estado_validacion = 'rechazado' THEN 'rechazado'
                     WHEN monto_total <= 0 THEN 'no_aplica'
                     WHEN saldo_pendiente >= monto_total THEN 'no_pagado'
                     WHEN saldo_pendiente <= 0 THEN 'pagado'
                     ELSE 'pago_parcial'
                   END AS estado_pago,
                   condicion, medio_pago_contado,
                   ruta_archivo
            FROM comprobantes
            WHERE proveedor_id = :proveedor_id AND empresa_id = :empresa_id
            ORDER BY fecha_emision DESC
        """),
        {"proveedor_id": str(proveedor_id), "empresa_id": empresa_id},
    )).mappings().all()

    pagos = (await db.execute(
        text("""
            SELECT p.id, p.comprobante_id, p.numero_recibo, p.fecha_pago,
                   p.monto_pagado, p.medio_pago, p.notas, p.ruta_adjunto,
                   c.numero_comprobante
            FROM pagos p
            JOIN comprobantes c ON c.id = p.comprobante_id
            WHERE c.proveedor_id = :proveedor_id AND p.empresa_id = :empresa_id
            ORDER BY p.fecha_pago DESC
        """),
        {"proveedor_id": str(proveedor_id), "empresa_id": empresa_id},
    )).mappings().all()

    nombre = (await db.execute(
        text("SELECT nombre FROM proveedores WHERE id = :id AND empresa_id = :e"),
        {"id": str(proveedor_id), "e": empresa_id},
    )).scalar() or "—"

    total_facturado = sum((f["monto_total"] for f in facturas), Decimal(0))
    total_pagado = sum((p["monto_pagado"] for p in pagos), Decimal(0))
    saldo = sum((f["saldo_pendiente"] for f in facturas if f["estado_validacion"] not in ("anulado", "rechazado")), Decimal(0))

    return {
        "proveedor_id": str(proveedor_id),
        "nombre": nombre,
        "total_facturado": float(total_facturado),
        "total_pagado": float(total_pagado),
        "saldo_pendiente": float(saldo),
        "facturas": [dict(f) for f in facturas],
        "pagos": [dict(p) for p in pagos],
    }
