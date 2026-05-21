"""
Router de Reportes Fiscales y de Gestión — Fase I.
  - Libro de Ventas IVA (RG 90 DNIT)
  - Libro de Compras IVA (RG 90 DNIT)
  - Liquidación mensual de IVA
  - Antigüedad de saldos (Aging Report) — clientes y proveedores
"""
from fastapi import APIRouter, Depends, Query
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from ..core.database import get_db
from ..core.security import get_current_user

router = APIRouter(prefix="/reportes", tags=["Reportes"])


# ── IVA ───────────────────────────────────────────────────────────────────────

@router.get("/iva/ventas", summary="Libro de Ventas IVA (RG 90)")
async def libro_ventas_iva(
    mes: Optional[str] = Query(None, description="YYYY-MM — filtra por mes; si omite, todos"),
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Libro de Ventas según RG 90 / DNIT paraguayo.
    Columnas: RUC comprador, Razón Social, N° Comprobante, Fecha,
              Gravadas 10%, IVA 10%, Gravadas 5%, IVA 5%, Exentas, Total.
    Solo comprobantes de venta (cliente_id IS NOT NULL), confirmados.
    """
    empresa_id = current_user["empresa_id"]
    filtros, params = _build_date_filter(mes, desde, hasta, "c.fecha_emision")
    params["empresa_id"] = empresa_id

    result = await db.execute(
        text(f"""
            SELECT
                cl.ruc                                        AS ruc_comprador,
                cl.nombre                                     AS razon_social,
                c.numero_comprobante,
                c.fecha_emision,
                tc.nombre                                     AS tipo_comprobante,
                -- subtotal e iva_monto se guardan como NETO al crear cada detalle:
                --   subtotal  = cantidad * precio_unitario   (NETO)
                --   iva_monto = subtotal * porcentaje_iva/100 (NETO * tasa)
                -- Por eso aqui usamos los valores directamente, sin extracciones.
                COALESCE(SUM(CASE WHEN d.porcentaje_iva = 10
                    THEN d.subtotal ELSE 0 END), 0)                   AS base_gravada_10,
                COALESCE(SUM(CASE WHEN d.porcentaje_iva = 10
                    THEN d.iva_monto ELSE 0 END), 0)                  AS iva_10,
                COALESCE(SUM(CASE WHEN d.porcentaje_iva = 5
                    THEN d.subtotal ELSE 0 END), 0)                   AS base_gravada_5,
                COALESCE(SUM(CASE WHEN d.porcentaje_iva = 5
                    THEN d.iva_monto ELSE 0 END), 0)                  AS iva_5,
                COALESCE(SUM(CASE WHEN d.porcentaje_iva = 0
                    THEN d.subtotal ELSE 0 END), 0)                   AS exentas,
                c.monto_total                                         AS total
            FROM comprobantes c
            JOIN clientes cl ON cl.id = c.cliente_id
            LEFT JOIN tipos_comprobante tc ON tc.id = c.tipo_id
            LEFT JOIN detalle_comprobantes d ON d.comprobante_id = c.id
            WHERE c.empresa_id = :empresa_id
              AND c.cliente_id IS NOT NULL
              AND c.estado_validacion = 'confirmado'
              {filtros}
            GROUP BY c.id, cl.ruc, cl.nombre, c.numero_comprobante,
                     c.fecha_emision, tc.nombre, c.monto_total
            ORDER BY c.fecha_emision, c.numero_comprobante
        """),
        params,
    )
    filas = result.mappings().all()

    return {
        "tipo": "ventas",
        "periodo": _periodo_label(mes, desde, hasta),
        "filas": filas,
        "totales": {
            "base_gravada_10": sum(f["base_gravada_10"] for f in filas),
            "iva_10":          sum(f["iva_10"] for f in filas),
            "base_gravada_5":  sum(f["base_gravada_5"] for f in filas),
            "iva_5":           sum(f["iva_5"] for f in filas),
            "exentas":         sum(f["exentas"] for f in filas),
            "total":           sum(f["total"] for f in filas),
        },
        "total_filas": len(filas),
    }


@router.get("/iva/compras", summary="Libro de Compras IVA (RG 90)")
async def libro_compras_iva(
    mes: Optional[str] = Query(None, description="YYYY-MM"),
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Libro de Compras — IVA Crédito Fiscal desglosado por tasa."""
    empresa_id = current_user["empresa_id"]
    filtros, params = _build_date_filter(mes, desde, hasta, "c.fecha_emision")
    params["empresa_id"] = empresa_id

    result = await db.execute(
        text(f"""
            SELECT
                pr.ruc                                        AS ruc_proveedor,
                pr.nombre                                     AS razon_social,
                c.numero_comprobante,
                c.fecha_emision,
                tc.nombre                                     AS tipo_comprobante,
                -- Mismo principio que en /iva/ventas: subtotal e iva_monto
                -- ya estan guardados como NETO y NETO*tasa, no hay que extraer.
                COALESCE(SUM(CASE WHEN d.porcentaje_iva = 10
                    THEN d.subtotal ELSE 0 END), 0)                   AS base_gravada_10,
                COALESCE(SUM(CASE WHEN d.porcentaje_iva = 10
                    THEN d.iva_monto ELSE 0 END), 0)                  AS credito_fiscal_10,
                COALESCE(SUM(CASE WHEN d.porcentaje_iva = 5
                    THEN d.subtotal ELSE 0 END), 0)                   AS base_gravada_5,
                COALESCE(SUM(CASE WHEN d.porcentaje_iva = 5
                    THEN d.iva_monto ELSE 0 END), 0)                  AS credito_fiscal_5,
                COALESCE(SUM(CASE WHEN d.porcentaje_iva = 0
                    THEN d.subtotal ELSE 0 END), 0)                   AS exentas,
                c.monto_total                                         AS total
            FROM comprobantes c
            JOIN proveedores pr ON pr.id = c.proveedor_id
            LEFT JOIN tipos_comprobante tc ON tc.id = c.tipo_id
            LEFT JOIN detalle_comprobantes d ON d.comprobante_id = c.id
            WHERE c.empresa_id = :empresa_id
              AND c.proveedor_id IS NOT NULL
              AND c.estado_validacion = 'confirmado'
              {filtros}
            GROUP BY c.id, pr.ruc, pr.nombre, c.numero_comprobante,
                     c.fecha_emision, tc.nombre, c.monto_total
            ORDER BY c.fecha_emision, c.numero_comprobante
        """),
        params,
    )
    filas = result.mappings().all()

    return {
        "tipo": "compras",
        "periodo": _periodo_label(mes, desde, hasta),
        "filas": filas,
        "totales": {
            "base_gravada_10":   sum(f["base_gravada_10"] for f in filas),
            "credito_fiscal_10": sum(f["credito_fiscal_10"] for f in filas),
            "base_gravada_5":    sum(f["base_gravada_5"] for f in filas),
            "credito_fiscal_5":  sum(f["credito_fiscal_5"] for f in filas),
            "exentas":           sum(f["exentas"] for f in filas),
            "total":             sum(f["total"] for f in filas),
        },
        "total_filas": len(filas),
    }


@router.get("/iva/liquidacion", summary="Liquidación mensual de IVA")
async def liquidacion_iva(
    mes: Optional[str] = Query(None, description="YYYY-MM"),
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Liquidación IVA del período:
      IVA Débito (ventas) - IVA Crédito (compras) = Saldo IVA a pagar/favor.
    """
    empresa_id = current_user["empresa_id"]
    filtros, params = _build_date_filter(mes, desde, hasta, "c.fecha_emision")
    params["empresa_id"] = empresa_id

    # IVA Débito (ventas)
    # iva_monto ya esta calculado al crear el detalle como subtotal*tasa/100,
    # asi que lo usamos directamente — es la fuente de verdad.
    ventas = (await db.execute(
        text(f"""
            SELECT
                COALESCE(SUM(CASE WHEN d.porcentaje_iva = 10
                    THEN d.iva_monto ELSE 0 END), 0)  AS iva_debito_10,
                COALESCE(SUM(CASE WHEN d.porcentaje_iva = 5
                    THEN d.iva_monto ELSE 0 END), 0)  AS iva_debito_5
            FROM comprobantes c
            LEFT JOIN detalle_comprobantes d ON d.comprobante_id = c.id
            WHERE c.empresa_id = :empresa_id
              AND c.cliente_id IS NOT NULL
              AND c.estado_validacion = 'confirmado'
              {filtros}
        """),
        params,
    )).mappings().first()

    # IVA Crédito (compras)
    compras = (await db.execute(
        text(f"""
            SELECT
                COALESCE(SUM(CASE WHEN d.porcentaje_iva = 10
                    THEN d.iva_monto ELSE 0 END), 0)  AS iva_credito_10,
                COALESCE(SUM(CASE WHEN d.porcentaje_iva = 5
                    THEN d.iva_monto ELSE 0 END), 0)  AS iva_credito_5
            FROM comprobantes c
            LEFT JOIN detalle_comprobantes d ON d.comprobante_id = c.id
            WHERE c.empresa_id = :empresa_id
              AND c.proveedor_id IS NOT NULL
              AND c.estado_validacion = 'confirmado'
              {filtros}
        """),
        params,
    )).mappings().first()

    iva_debito  = int(ventas["iva_debito_10"]) + int(ventas["iva_debito_5"])
    iva_credito = int(compras["iva_credito_10"]) + int(compras["iva_credito_5"])
    saldo       = iva_debito - iva_credito

    return {
        "periodo": _periodo_label(mes, desde, hasta),
        "iva_debito_10":  int(ventas["iva_debito_10"]),
        "iva_debito_5":   int(ventas["iva_debito_5"]),
        "total_iva_debito": iva_debito,
        "iva_credito_10": int(compras["iva_credito_10"]),
        "iva_credito_5":  int(compras["iva_credito_5"]),
        "total_iva_credito": iva_credito,
        "saldo_iva": saldo,
        "situacion": "a_pagar" if saldo > 0 else "a_favor" if saldo < 0 else "neutro",
    }


# ── Aging ─────────────────────────────────────────────────────────────────────

@router.get("/aging", summary="Antigüedad de saldos (Aging Report)")
async def aging_saldos(
    tipo: str = Query("clientes", pattern="^(clientes|proveedores)$"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Clasifica las cuentas por cobrar / pagar vencidas en rangos de antigüedad:
    - Corriente: 0-30 días
    - 31-60 días
    - 61-90 días
    - Más de 90 días
    Solo considera comprobantes con saldo_pendiente > 0 y condicion = 'credito'.
    """
    empresa_id = current_user["empresa_id"]
    join_col = "cliente_id" if tipo == "clientes" else "proveedor_id"
    entity   = "clientes" if tipo == "clientes" else "proveedores"

    # Cálculo de aging hecho en Python (compatible Postgres + SQLite — sin INTERVAL/::date)
    result = await db.execute(
        text(f"""
            SELECT
                e.nombre                          AS contraparte,
                e.ruc,
                c.numero_comprobante,
                c.fecha_emision,
                c.fecha_vencimiento,
                c.saldo_pendiente
            FROM comprobantes c
            JOIN {entity} e ON e.id = c.{join_col}
            WHERE c.empresa_id = :empresa_id
              AND c.{join_col} IS NOT NULL
              AND c.saldo_pendiente > 0
              AND c.condicion = 'credito'
              AND c.estado_validacion = 'confirmado'
            ORDER BY e.nombre, c.fecha_vencimiento
        """),
        {"empresa_id": empresa_id},
    )
    raw = result.mappings().all()

    from datetime import date as _date, timedelta as _td
    hoy = _date.today()

    def _to_date(v):
        if v is None: return None
        if hasattr(v, "year"): return v
        try: return _date.fromisoformat(str(v))
        except Exception: return None

    filas = []
    for r in raw:
        fe  = _to_date(r["fecha_emision"])
        fv  = _to_date(r["fecha_vencimiento"]) or (fe + _td(days=30) if fe else hoy)
        dias = (hoy - fv).days
        if   dias <= 0:  tramo = "corriente"
        elif dias <= 30: tramo = "1_30"
        elif dias <= 60: tramo = "31_60"
        elif dias <= 90: tramo = "61_90"
        else:            tramo = "mas_90"
        filas.append({
            **dict(r),
            "dias_vencido": dias,
            "tramo": tramo,
        })

    # Agregar por tramo
    tramos = {"corriente": 0, "1_30": 0, "31_60": 0, "61_90": 0, "mas_90": 0}
    for f in filas:
        tramos[f["tramo"]] += int(f["saldo_pendiente"])

    total_general = sum(tramos.values())

    return {
        "tipo": tipo,
        "filas": filas,
        "resumen": tramos,
        "total_general": total_general,
        "total_facturas": len(filas),
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_date_filter(mes, desde, hasta, col):
    filtros = ""
    params = {}
    if mes:
        filtros += f" AND substr(CAST({col} AS TEXT), 1, 7) = :mes"
        params["mes"] = mes
    else:
        if desde:
            filtros += f" AND {col} >= :desde"; params["desde"] = desde
        if hasta:
            filtros += f" AND {col} <= :hasta"; params["hasta"] = hasta
    return filtros, params


def _periodo_label(mes, desde, hasta):
    if mes:
        return mes
    if desde and hasta:
        return f"{desde} → {hasta}"
    if desde:
        return f"desde {desde}"
    if hasta:
        return f"hasta {hasta}"
    return "Todo el período"
