"""Helper compartido para registrar cobros / pagos.

Tanto el endpoint REST `POST /pagos` como las tools del chatbot
(`registrar_cobro`, `registrar_pago`) llaman a `registrar_pago_core`
para no duplicar las validaciones de saldo, estado del comprobante,
auditoría y asiento contable.
"""
from __future__ import annotations

import logging
from datetime import date as _date
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .audit import registrar as audit_registrar
from .contabilidad import asiento_cobro, asiento_pago_proveedor

_LOG = logging.getLogger(__name__)


class RegistrarPagoError(Exception):
    """Error de negocio al registrar un pago (saldo insuficiente, etc.)."""

    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


async def registrar_pago_core(
    *,
    db: AsyncSession,
    empresa_id: str,
    usuario: dict,
    comprobante_id: str,
    monto_pagado: Decimal,
    medio_pago: str,
    fecha_pago: Optional[_date] = None,
    numero_recibo: Optional[str] = None,
    notas: Optional[str] = None,
    cuenta_banco_id: Optional[str] = None,
    commit: bool = True,
    audit_origen: str = "ui",
) -> dict:
    """Inserta un pago, actualiza saldo, registra auditoría y asiento contable.

    Devuelve dict con los campos del pago creado + saldo_restante + tipo_movimiento
    ('cobro' si imputa a venta, 'pago' si imputa a compra).
    """
    usuario_id = usuario["sub"]

    comp = (await db.execute(
        text("""
            SELECT id, saldo_pendiente, estado_validacion, monto_total,
                   numero_comprobante, cliente_id, proveedor_id
            FROM comprobantes
            WHERE id = :id AND empresa_id = :empresa_id
        """),
        {"id": str(comprobante_id), "empresa_id": empresa_id},
    )).mappings().first()
    if not comp:
        raise RegistrarPagoError(404, "Comprobante no encontrado")
    if comp["estado_validacion"] == "anulado":
        raise RegistrarPagoError(409, "No se puede registrar pago sobre un comprobante anulado")
    if comp["estado_validacion"] == "rechazado":
        raise RegistrarPagoError(409, "No se puede registrar pago sobre un comprobante rechazado")

    saldo = Decimal(comp["saldo_pendiente"])
    if saldo <= 0:
        raise RegistrarPagoError(409, "Este comprobante ya está totalmente cancelado")

    monto = Decimal(monto_pagado)
    if monto <= 0:
        raise RegistrarPagoError(422, "El monto debe ser mayor a cero")
    if monto > saldo:
        formateado = f"{saldo:,.0f}".replace(",", ".")
        raise RegistrarPagoError(
            422,
            f"El monto supera el saldo pendiente (₲ {formateado}). Ajustá el monto.",
        )

    fecha_pago = fecha_pago or _date.today()

    pago = (await db.execute(
        text("""
            INSERT INTO pagos (
                empresa_id, comprobante_id, numero_recibo, fecha_pago,
                monto_pagado, medio_pago, cuenta_banco_id, notas, usuario_id
            ) VALUES (
                :empresa_id, :comprobante_id, :numero_recibo, :fecha_pago,
                :monto_pagado, :medio_pago, :cuenta_banco_id, :notas, :usuario_id
            )
            RETURNING id, comprobante_id, fecha_pago, monto_pagado,
                      medio_pago, fecha_creacion
        """),
        {
            "empresa_id": empresa_id,
            "comprobante_id": str(comprobante_id),
            "numero_recibo": numero_recibo,
            "fecha_pago": fecha_pago,
            "monto_pagado": monto,
            "medio_pago": medio_pago,
            "cuenta_banco_id": str(cuenta_banco_id) if cuenta_banco_id else None,
            "notas": notas,
            "usuario_id": usuario_id,
        },
    )).mappings().first()

    nuevo_saldo = saldo - monto
    await db.execute(
        text("""
            UPDATE comprobantes
            SET saldo_pendiente = :saldo, fecha_modificacion = NOW()
            WHERE id = :id AND empresa_id = :empresa_id
        """),
        {"saldo": nuevo_saldo, "id": str(comprobante_id), "empresa_id": empresa_id},
    )

    await audit_registrar(
        db, usuario=usuario, accion="INSERT", tabla="pagos",
        registro_id=str(pago["id"]),
        datos_nuevos={
            "comprobante_id": str(comprobante_id),
            "monto": float(monto),
            "medio_pago": medio_pago,
            "numero_recibo": numero_recibo,
        },
        origen=audit_origen,
    )

    contraparte_row = (await db.execute(
        text("""
            SELECT COALESCE(cl.nombre, pr.nombre, '—') AS contraparte
            FROM comprobantes c
            LEFT JOIN clientes cl ON cl.id = c.cliente_id
            LEFT JOIN proveedores pr ON pr.id = c.proveedor_id
            WHERE c.id = :id AND c.empresa_id = :e
        """),
        {"id": str(comprobante_id), "e": empresa_id},
    )).mappings().first()
    contraparte = (contraparte_row or {}).get("contraparte", "—")

    tipo_mov = "cobro" if comp["cliente_id"] else "pago"
    try:
        if tipo_mov == "cobro":
            await asiento_cobro(
                db, empresa_id, str(pago["id"]), str(comprobante_id),
                fecha_pago, monto, numero_recibo, contraparte, usuario_id,
            )
        else:
            await asiento_pago_proveedor(
                db, empresa_id, str(pago["id"]), str(comprobante_id),
                fecha_pago, monto, numero_recibo, contraparte, usuario_id,
            )
    except Exception as exc:
        _LOG.warning("Asiento pago falló (no crítico): %s", exc)

    if commit:
        await db.commit()

    return {
        **dict(pago),
        "saldo_restante": float(nuevo_saldo),
        "totalmente_cancelado": nuevo_saldo == 0,
        "numero_comprobante": comp["numero_comprobante"],
        "contraparte": contraparte,
        "tipo_movimiento": tipo_mov,
    }


async def resolver_comprobante_pendiente(
    *,
    db: AsyncSession,
    empresa_id: str,
    factura_numero: str,
    contraparte_texto: Optional[str] = None,
    es_venta: bool,
) -> list[dict]:
    """Busca facturas pendientes que coincidan parcialmente con el número.

    Filtra por tipo (venta=cliente / compra=proveedor) y, si se indica,
    por nombre/RUC de la contraparte. Devuelve hasta 5 candidatos.
    """
    fk_filtro = "c.cliente_id IS NOT NULL" if es_venta else "c.proveedor_id IS NOT NULL"
    contra_filtro = ""
    params: dict = {
        "empresa_id": empresa_id,
        "numero": f"%{factura_numero.strip()}%",
    }
    if contraparte_texto:
        contra_filtro = (
            "AND (cl.nombre ILIKE :ctx OR cl.ruc ILIKE :ctx "
            "OR pr.nombre ILIKE :ctx OR pr.ruc ILIKE :ctx)"
        )
        params["ctx"] = f"%{contraparte_texto.strip()}%"

    result = await db.execute(
        text(f"""
            SELECT c.id, c.numero_comprobante, c.fecha_emision, c.monto_total,
                   c.saldo_pendiente, c.estado_validacion,
                   COALESCE(cl.nombre, pr.nombre) AS contraparte
            FROM comprobantes c
            LEFT JOIN clientes cl ON cl.id = c.cliente_id
            LEFT JOIN proveedores pr ON pr.id = c.proveedor_id
            WHERE c.empresa_id = :empresa_id
              AND c.estado_validacion = 'confirmado'
              AND c.saldo_pendiente > 0
              AND {fk_filtro}
              AND c.numero_comprobante ILIKE :numero
              {contra_filtro}
            ORDER BY c.fecha_emision DESC
            LIMIT 5
        """),
        params,
    )
    return [dict(r) for r in result.mappings().all()]
