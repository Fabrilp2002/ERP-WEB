"""
Servicio de Contabilidad — Fase H.

Responsabilidades:
  1. Generar asientos automáticos al crear comprobantes (partida doble).
  2. Generar asientos automáticos al registrar pagos/cobros.
  3. Calcular Libro Mayor (movimientos por cuenta con saldo acumulado).
  4. Calcular Balance General y Estado de Resultados.

Reglas invariantes:
  - SUM(debe) == SUM(haber) en cada asiento — SIEMPRE.
  - DECIMAL(15,2) en todos los montos.
  - empresa_id en toda operación (multi-tenant).
  - Si no existe la cuenta necesaria para el asiento, se registra igualmente
    con la que sí existe (evita bloquear el flujo operativo).
"""
from __future__ import annotations
from decimal import Decimal
from datetime import date
from typing import Optional
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

logger = logging.getLogger(__name__)

# ── Códigos de cuentas estándar ────────────────────────────────────────────────
# Estos códigos deben existir en plan_cuentas seeded.
# Si una empresa los renombra o borra, el asiento se genera parcial y se loguea.
COD_CAJA_BANCOS        = "1.1.01"
COD_CXC_CLIENTES       = "1.1.02"
COD_INVENTARIO         = "1.1.03"
COD_IVA_CREDITO        = "1.1.04"
COD_CXP_PROVEEDORES    = "2.1.01"
COD_IVA_POR_PAGAR      = "2.1.02"
COD_IVA_DEBITO         = "2.1.03"
COD_VENTAS             = "4.1.01"
COD_COSTO_MERCADERIA   = "5.1.01"
COD_GASTOS_ADMIN       = "5.2.01"
COD_GASTOS_VENTA       = "5.2.02"


async def _codigo_a_id(
    db: AsyncSession, empresa_id: str, codigo: str
) -> Optional[str]:
    """Devuelve el UUID de una cuenta por su código. None si no existe."""
    row = (await db.execute(
        text("""
            SELECT id FROM plan_cuentas
            WHERE empresa_id = :e AND codigo = :c AND activa = TRUE
        """),
        {"e": empresa_id, "c": codigo},
    )).mappings().first()
    return str(row["id"]) if row else None


async def _siguiente_numero(db: AsyncSession, empresa_id: str) -> int:
    """Genera el número correlativo siguiente para los asientos de la empresa."""
    row = (await db.execute(
        text("""
            SELECT COALESCE(MAX(numero), 0) + 1 AS siguiente
            FROM asientos_contables
            WHERE empresa_id = :e
        """),
        {"e": empresa_id},
    )).mappings().first()
    return row["siguiente"] if row else 1


async def _insertar_asiento(
    db: AsyncSession,
    empresa_id: str,
    fecha: date,
    concepto: str,
    partidas: list[dict],            # [{"cuenta_id": str, "debe": Decimal, "haber": Decimal}]
    tipo: str = "automatico",
    comprobante_id: Optional[str] = None,
    pago_id: Optional[str] = None,
    usuario_id: Optional[str] = None,
) -> Optional[str]:
    """
    Inserta un asiento y sus partidas.  Valida partida doble antes de guardar.
    Devuelve el ID del asiento creado, o None si falló la validación.
    """
    # Filtrar partidas vacías (cuenta no encontrada = None)
    partidas_validas = [p for p in partidas if p.get("cuenta_id")]
    if not partidas_validas:
        logger.warning("Asiento descartado: ninguna cuenta encontrada [empresa=%s]", empresa_id)
        return None

    total_debe  = sum(Decimal(str(p["debe"]))  for p in partidas_validas)
    total_haber = sum(Decimal(str(p["haber"])) for p in partidas_validas)
    if total_debe != total_haber:
        logger.error(
            "Asiento desequilibrado: debe=%s haber=%s [empresa=%s concepto=%s]",
            total_debe, total_haber, empresa_id, concepto,
        )
        return None

    numero = await _siguiente_numero(db, empresa_id)

    row = (await db.execute(
        text("""
            INSERT INTO asientos_contables
                (empresa_id, numero, fecha, concepto, tipo, comprobante_id, pago_id, usuario_id)
            VALUES
                (:empresa_id, :numero, :fecha, :concepto, :tipo,
                 :comprobante_id, :pago_id, :usuario_id)
            RETURNING id
        """),
        {
            "empresa_id": empresa_id,
            "numero": numero,
            "fecha": fecha,
            "concepto": concepto,
            "tipo": tipo,
            "comprobante_id": comprobante_id,
            "pago_id": pago_id,
            "usuario_id": usuario_id,
        },
    )).mappings().first()

    asiento_id = str(row["id"])

    for p in partidas_validas:
        await db.execute(
            text("""
                INSERT INTO detalle_asientos (empresa_id, asiento_id, cuenta_id, debe, haber)
                VALUES (:e, :a, :c, :d, :h)
            """),
            {
                "e": empresa_id,
                "a": asiento_id,
                "c": p["cuenta_id"],
                "d": Decimal(str(p["debe"])),
                "h": Decimal(str(p["haber"])),
            },
        )

    return asiento_id


# ── Asientos automáticos ───────────────────────────────────────────────────────

async def asiento_comprobante_venta(
    db: AsyncSession,
    empresa_id: str,
    comprobante_id: str,
    numero_comprobante: str,
    fecha: date,
    monto_subtotal: Decimal,
    monto_iva: Decimal,
    monto_total: Decimal,
    cliente_nombre: str,
    usuario_id: Optional[str] = None,
) -> Optional[str]:
    """
    Factura de venta (ingreso):
      DEBE  1.1.02 Cuentas x Cobrar Clientes  = monto_total
      HABER 4.1.01 Ventas                      = monto_subtotal
      HABER 2.1.03 IVA Débito Fiscal           = monto_iva
    """
    cxc  = await _codigo_a_id(db, empresa_id, COD_CXC_CLIENTES)
    vta  = await _codigo_a_id(db, empresa_id, COD_VENTAS)
    iva  = await _codigo_a_id(db, empresa_id, COD_IVA_DEBITO)

    # Si IVA Débito no existe intentar IVA por Pagar
    if not iva:
        iva = await _codigo_a_id(db, empresa_id, COD_IVA_POR_PAGAR)

    partidas = [
        {"cuenta_id": cxc,  "debe": monto_total,    "haber": Decimal(0)},
        {"cuenta_id": vta,  "debe": Decimal(0),      "haber": monto_subtotal},
        {"cuenta_id": iva,  "debe": Decimal(0),      "haber": monto_iva} if monto_iva > 0 else None,
    ]
    partidas = [p for p in partidas if p]

    # Si IVA = 0 la partida no existe — rebalancear
    if monto_iva == 0:
        # Ventas = monto_total completo
        partidas = [
            {"cuenta_id": cxc, "debe": monto_total, "haber": Decimal(0)},
            {"cuenta_id": vta, "debe": Decimal(0),  "haber": monto_total},
        ]

    return await _insertar_asiento(
        db, empresa_id, fecha,
        concepto=f"Factura venta {numero_comprobante} — {cliente_nombre}",
        partidas=partidas,
        tipo="automatico",
        comprobante_id=comprobante_id,
        usuario_id=usuario_id,
    )


async def asiento_comprobante_compra(
    db: AsyncSession,
    empresa_id: str,
    comprobante_id: str,
    numero_comprobante: str,
    fecha: date,
    monto_subtotal: Decimal,
    monto_iva: Decimal,
    monto_total: Decimal,
    proveedor_nombre: str,
    usuario_id: Optional[str] = None,
) -> Optional[str]:
    """
    Factura de compra (egreso):
      DEBE  5.2.01 Gastos Administrativos  = monto_subtotal
      DEBE  1.1.04 IVA Crédito Fiscal      = monto_iva
      HABER 2.1.01 Cuentas x Pagar Prov.  = monto_total
    """
    gastos = await _codigo_a_id(db, empresa_id, COD_GASTOS_ADMIN)
    iva_cr = await _codigo_a_id(db, empresa_id, COD_IVA_CREDITO)
    cxp    = await _codigo_a_id(db, empresa_id, COD_CXP_PROVEEDORES)

    if monto_iva > 0 and iva_cr:
        partidas = [
            {"cuenta_id": gastos, "debe": monto_subtotal, "haber": Decimal(0)},
            {"cuenta_id": iva_cr, "debe": monto_iva,      "haber": Decimal(0)},
            {"cuenta_id": cxp,   "debe": Decimal(0),      "haber": monto_total},
        ]
    else:
        partidas = [
            {"cuenta_id": gastos, "debe": monto_total, "haber": Decimal(0)},
            {"cuenta_id": cxp,   "debe": Decimal(0),   "haber": monto_total},
        ]

    return await _insertar_asiento(
        db, empresa_id, fecha,
        concepto=f"Factura compra {numero_comprobante} — {proveedor_nombre}",
        partidas=partidas,
        tipo="automatico",
        comprobante_id=comprobante_id,
        usuario_id=usuario_id,
    )


async def asiento_cobro(
    db: AsyncSession,
    empresa_id: str,
    pago_id: str,
    comprobante_id: str,
    fecha: date,
    monto: Decimal,
    numero_recibo: Optional[str],
    cliente_nombre: str,
    usuario_id: Optional[str] = None,
) -> Optional[str]:
    """
    Cobro de cliente:
      DEBE  1.1.01 Caja y Bancos            = monto
      HABER 1.1.02 Cuentas x Cobrar Clien.  = monto
    """
    caja = await _codigo_a_id(db, empresa_id, COD_CAJA_BANCOS)
    cxc  = await _codigo_a_id(db, empresa_id, COD_CXC_CLIENTES)

    recibo_str = f" (recibo {numero_recibo})" if numero_recibo else ""
    return await _insertar_asiento(
        db, empresa_id, fecha,
        concepto=f"Cobro cliente {cliente_nombre}{recibo_str}",
        partidas=[
            {"cuenta_id": caja, "debe": monto,         "haber": Decimal(0)},
            {"cuenta_id": cxc,  "debe": Decimal(0),    "haber": monto},
        ],
        tipo="automatico",
        comprobante_id=comprobante_id,
        pago_id=pago_id,
        usuario_id=usuario_id,
    )


async def asiento_pago_proveedor(
    db: AsyncSession,
    empresa_id: str,
    pago_id: str,
    comprobante_id: str,
    fecha: date,
    monto: Decimal,
    numero_recibo: Optional[str],
    proveedor_nombre: str,
    usuario_id: Optional[str] = None,
) -> Optional[str]:
    """
    Pago a proveedor:
      DEBE  2.1.01 Cuentas x Pagar Prov.  = monto
      HABER 1.1.01 Caja y Bancos          = monto
    """
    cxp  = await _codigo_a_id(db, empresa_id, COD_CXP_PROVEEDORES)
    caja = await _codigo_a_id(db, empresa_id, COD_CAJA_BANCOS)

    recibo_str = f" (recibo {numero_recibo})" if numero_recibo else ""
    return await _insertar_asiento(
        db, empresa_id, fecha,
        concepto=f"Pago proveedor {proveedor_nombre}{recibo_str}",
        partidas=[
            {"cuenta_id": cxp,  "debe": monto,      "haber": Decimal(0)},
            {"cuenta_id": caja, "debe": Decimal(0),  "haber": monto},
        ],
        tipo="automatico",
        comprobante_id=comprobante_id,
        pago_id=pago_id,
        usuario_id=usuario_id,
    )


async def revertir_asiento_comprobante(
    db: AsyncSession, empresa_id: str, comprobante_id: str, usuario_id: Optional[str] = None
) -> None:
    """
    Genera un asiento inverso (anulación) cuando se anula un comprobante.
    Invierte todas las partidas de los asientos automáticos originales.
    """
    # Buscar asientos automáticos del comprobante
    rows = (await db.execute(
        text("""
            SELECT a.id, a.fecha, a.concepto
            FROM asientos_contables a
            WHERE a.empresa_id = :e AND a.comprobante_id = :c
              AND a.tipo = 'automatico'
            ORDER BY a.fecha
        """),
        {"e": empresa_id, "c": comprobante_id},
    )).mappings().all()

    for asiento in rows:
        # Obtener sus partidas
        partidas_orig = (await db.execute(
            text("SELECT cuenta_id, debe, haber FROM detalle_asientos WHERE asiento_id = :a"),
            {"a": str(asiento["id"])},
        )).mappings().all()

        # Invertir debe/haber
        partidas_inv = [
            {"cuenta_id": str(p["cuenta_id"]), "debe": Decimal(str(p["haber"])), "haber": Decimal(str(p["debe"]))}
            for p in partidas_orig
        ]

        await _insertar_asiento(
            db, empresa_id, date.today(),
            concepto=f"ANULACIÓN — {asiento['concepto']}",
            partidas=partidas_inv,
            tipo="ajuste",
            comprobante_id=comprobante_id,
            usuario_id=usuario_id,
        )


async def revertir_asiento_pago(
    db: AsyncSession, empresa_id: str, pago_id: str, usuario_id: Optional[str] = None
) -> None:
    """
    Genera un asiento inverso cuando se elimina un pago.
    Invierte todas las partidas de los asientos automáticos originales del pago.
    Debe llamarse ANTES de ejecutar DELETE FROM pagos para que la FK siga existiendo.
    """
    rows = (await db.execute(
        text("""
            SELECT a.id, a.fecha, a.concepto
            FROM asientos_contables a
            WHERE a.empresa_id = :e AND a.pago_id = :p
              AND a.tipo = 'automatico'
            ORDER BY a.fecha
        """),
        {"e": empresa_id, "p": pago_id},
    )).mappings().all()

    for asiento in rows:
        partidas_orig = (await db.execute(
            text("SELECT cuenta_id, debe, haber FROM detalle_asientos WHERE asiento_id = :a"),
            {"a": str(asiento["id"])},
        )).mappings().all()

        # Invertir debe↔haber
        partidas_inv = [
            {"cuenta_id": str(p["cuenta_id"]), "debe": Decimal(str(p["haber"])), "haber": Decimal(str(p["debe"]))}
            for p in partidas_orig
        ]

        await _insertar_asiento(
            db, empresa_id, date.today(),
            concepto=f"REVERSIÓN PAGO — {asiento['concepto']}",
            partidas=partidas_inv,
            tipo="ajuste",
            pago_id=pago_id,
            usuario_id=usuario_id,
        )


# ── Consultas contables ────────────────────────────────────────────────────────

async def libro_mayor_cuenta(
    db: AsyncSession,
    empresa_id: str,
    cuenta_id: str,
    desde: Optional[date] = None,
    hasta: Optional[date] = None,
) -> dict:
    """
    Movimientos de una cuenta con saldo acumulado cronológico.
    """
    filtros = ["da.empresa_id = :e", "da.cuenta_id = :c"]
    params: dict = {"e": empresa_id, "c": cuenta_id}
    if desde:
        filtros.append("a.fecha >= :d"); params["d"] = desde
    if hasta:
        filtros.append("a.fecha <= :h"); params["h"] = hasta

    cuenta = (await db.execute(
        text("""
            SELECT pc.codigo, pc.nombre, pc.naturaleza
            FROM plan_cuentas pc
            WHERE pc.id = :c AND pc.empresa_id = :e
        """),
        {"c": cuenta_id, "e": empresa_id},
    )).mappings().first()

    movimientos = (await db.execute(
        text(f"""
            SELECT a.numero, a.fecha, a.concepto, da.debe, da.haber,
                   SUM(da.debe - da.haber) OVER (
                       PARTITION BY da.cuenta_id ORDER BY a.fecha, a.numero
                   ) AS saldo_acumulado
            FROM detalle_asientos da
            JOIN asientos_contables a ON a.id = da.asiento_id
            WHERE {' AND '.join(filtros)}
            ORDER BY a.fecha, a.numero
        """),
        params,
    )).mappings().all()

    total_debe  = sum(Decimal(str(m["debe"]))  for m in movimientos)
    total_haber = sum(Decimal(str(m["haber"])) for m in movimientos)

    return {
        "cuenta": dict(cuenta) if cuenta else {},
        "movimientos": [
            {**dict(m), "saldo_acumulado": float(m["saldo_acumulado"])}
            for m in movimientos
        ],
        "total_debe": float(total_debe),
        "total_haber": float(total_haber),
        "saldo_final": float(total_debe - total_haber),
    }


async def balance_comprobacion(
    db: AsyncSession,
    empresa_id: str,
    hasta: Optional[date] = None,
) -> list[dict]:
    """
    Balance de comprobación: sumas y saldos por cuenta.
    """
    params: dict = {"e": empresa_id}
    filtro_fecha = "AND a.fecha <= :h" if hasta else ""
    if hasta:
        params["h"] = hasta

    rows = (await db.execute(
        text(f"""
            SELECT
                pc.codigo,
                pc.nombre,
                pc.tipo,
                pc.naturaleza,
                COALESCE(SUM(da.debe),  0) AS total_debe,
                COALESCE(SUM(da.haber), 0) AS total_haber,
                COALESCE(SUM(da.debe),  0) - COALESCE(SUM(da.haber), 0) AS saldo
            FROM plan_cuentas pc
            LEFT JOIN detalle_asientos da ON da.cuenta_id = pc.id
                AND da.empresa_id = pc.empresa_id
            LEFT JOIN asientos_contables a ON a.id = da.asiento_id {filtro_fecha}
            WHERE pc.empresa_id = :e AND pc.activa = TRUE AND pc.es_hoja = TRUE
            GROUP BY pc.codigo, pc.nombre, pc.tipo, pc.naturaleza
            ORDER BY pc.codigo
        """),
        params,
    )).mappings().all()

    return [dict(r) for r in rows]


async def estado_resultados(
    db: AsyncSession,
    empresa_id: str,
    desde: date,
    hasta: date,
) -> dict:
    """
    Estado de Resultados: Ingresos - Egresos = Utilidad del periodo.
    """
    rows = (await db.execute(
        text("""
            SELECT
                pc.tipo,
                pc.codigo,
                pc.nombre,
                COALESCE(SUM(da.haber - da.debe), 0) AS saldo
            FROM plan_cuentas pc
            JOIN detalle_asientos da ON da.cuenta_id = pc.id AND da.empresa_id = pc.empresa_id
            JOIN asientos_contables a ON a.id = da.asiento_id
            WHERE pc.empresa_id = :e
              AND pc.activa = TRUE
              AND pc.es_hoja = TRUE
              AND pc.tipo IN ('ingreso','egreso')
              AND a.fecha BETWEEN :d AND :h
            GROUP BY pc.tipo, pc.codigo, pc.nombre
            ORDER BY pc.codigo
        """),
        {"e": empresa_id, "d": desde, "h": hasta},
    )).mappings().all()

    ingresos = [dict(r) for r in rows if r["tipo"] == "ingreso"]
    egresos  = [dict(r) for r in rows if r["tipo"] == "egreso"]

    total_ingresos = sum(Decimal(str(r["saldo"])) for r in ingresos)
    total_egresos  = sum(abs(Decimal(str(r["saldo"]))) for r in egresos)
    utilidad = total_ingresos - total_egresos

    return {
        "desde": str(desde),
        "hasta": str(hasta),
        "ingresos": ingresos,
        "egresos": egresos,
        "total_ingresos": float(total_ingresos),
        "total_egresos": float(total_egresos),
        "utilidad_neta": float(utilidad),
    }


async def balance_general(
    db: AsyncSession,
    empresa_id: str,
    hasta: Optional[date] = None,
) -> dict:
    """
    Balance General: Activo = Pasivo + Patrimonio.
    """
    params: dict = {"e": empresa_id}
    filtro_fecha = "AND a.fecha <= :h" if hasta else ""
    if hasta:
        params["h"] = hasta

    rows = (await db.execute(
        text(f"""
            SELECT
                pc.tipo,
                pc.codigo,
                pc.nombre,
                COALESCE(SUM(da.debe - da.haber), 0) AS saldo
            FROM plan_cuentas pc
            LEFT JOIN detalle_asientos da ON da.cuenta_id = pc.id AND da.empresa_id = pc.empresa_id
            LEFT JOIN asientos_contables a ON a.id = da.asiento_id {filtro_fecha}
            WHERE pc.empresa_id = :e
              AND pc.activa = TRUE
              AND pc.es_hoja = TRUE
              AND pc.tipo IN ('activo','pasivo','patrimonio')
            GROUP BY pc.tipo, pc.codigo, pc.nombre
            ORDER BY pc.codigo
        """),
        params,
    )).mappings().all()

    activos    = [dict(r) for r in rows if r["tipo"] == "activo"]
    pasivos    = [dict(r) for r in rows if r["tipo"] == "pasivo"]
    patrimonio = [dict(r) for r in rows if r["tipo"] == "patrimonio"]

    total_activo    = sum(Decimal(str(r["saldo"])) for r in activos)
    total_pasivo    = sum(abs(Decimal(str(r["saldo"]))) for r in pasivos)
    total_patrimonio = sum(abs(Decimal(str(r["saldo"]))) for r in patrimonio)

    return {
        "hasta": str(hasta) if hasta else None,
        "activo": activos,
        "pasivo": pasivos,
        "patrimonio": patrimonio,
        "total_activo": float(total_activo),
        "total_pasivo": float(total_pasivo),
        "total_patrimonio": float(total_patrimonio),
        "diferencia": float(total_activo - (total_pasivo + total_patrimonio)),
    }
