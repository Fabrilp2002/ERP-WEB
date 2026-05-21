"""
Router de Dashboard — Solo lectura.
Accesible por todos los roles incluyendo viewer.
Diseñado para el acceso remoto (gerentes, dueños, contadores externos).
Todos los endpoints aceptan ?desde=YYYY-MM-DD&hasta=YYYY-MM-DD para filtrar por período.
"""
from datetime import datetime, timezone, date
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from ..core.database import get_db
from ..core.security import get_current_user
from ..models.schemas import ResumenDashboard

router = APIRouter(prefix="/dashboard", tags=["Dashboard (solo lectura)"])


def _rango(desde: Optional[date], hasta: Optional[date]):
    """Devuelve (desde, hasta) normalizados. Si no se pasan, no filtra por fecha."""
    return desde, hasta or date.today()


def _filtro_fecha(campo: str, desde: Optional[date], hasta: Optional[date]) -> tuple[str, dict]:
    """Genera la cláusula SQL y parámetros para el rango de fechas."""
    if desde is None:
        return "", {}
    return f"AND {campo} BETWEEN :desde AND :hasta", {"desde": desde, "hasta": hasta or date.today()}


@router.get("/resumen", response_model=ResumenDashboard, summary="KPIs principales")
async def resumen(
    desde: Optional[date] = Query(None, description="Fecha inicio del período (YYYY-MM-DD)"),
    hasta: Optional[date] = Query(None, description="Fecha fin del período (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    empresa_id = current_user["empresa_id"]
    cond, params = _filtro_fecha("fecha_emision", desde, hasta)

    r = await db.execute(
        text(f"""
            SELECT
                COALESCE(SUM(CASE WHEN saldo_pendiente > 0 THEN 1 ELSE 0 END), 0) AS total_facturas_pendientes,
                COALESCE(SUM(CASE WHEN cliente_id   IS NOT NULL AND saldo_pendiente > 0 THEN 1 ELSE 0 END), 0) AS facturas_pendientes_cobrar,
                COALESCE(SUM(CASE WHEN proveedor_id IS NOT NULL AND saldo_pendiente > 0 THEN 1 ELSE 0 END), 0) AS facturas_pendientes_pagar,
                COALESCE(SUM(CASE WHEN cliente_id   IS NOT NULL AND saldo_pendiente > 0 THEN saldo_pendiente ELSE 0 END), 0) AS monto_por_cobrar,
                COALESCE(SUM(CASE WHEN proveedor_id IS NOT NULL AND saldo_pendiente > 0 THEN saldo_pendiente ELSE 0 END), 0) AS monto_por_pagar,
                COALESCE(SUM(CASE WHEN cliente_id   IS NOT NULL THEN monto_total ELSE 0 END), 0) AS total_ingresos,
                COALESCE(SUM(CASE WHEN proveedor_id IS NOT NULL THEN monto_total ELSE 0 END), 0) AS total_egresos
            FROM comprobantes
            WHERE empresa_id = :empresa_id
              AND estado_validacion NOT IN ('anulado', 'rechazado')
              {cond}
        """),
        {"empresa_id": empresa_id, **params},
    )
    row = dict(r.mappings().first())

    stock_r = await db.execute(
        text("""
            SELECT COUNT(*) AS items_bajo_stock
            FROM inventario
            WHERE empresa_id = :empresa_id
              AND activo = TRUE
              AND punto_reorden > 0
              AND cantidad_actual <= punto_reorden
        """),
        {"empresa_id": empresa_id},
    )
    stock_row = stock_r.mappings().first()

    return ResumenDashboard(
        total_facturas_pendientes=row["total_facturas_pendientes"],
        facturas_pendientes_cobrar=row["facturas_pendientes_cobrar"],
        facturas_pendientes_pagar=row["facturas_pendientes_pagar"],
        monto_por_cobrar=row["monto_por_cobrar"],
        monto_por_pagar=row["monto_por_pagar"],
        items_bajo_stock=stock_row["items_bajo_stock"],
        ultima_actualizacion=datetime.now(timezone.utc),
    )


@router.get("/cuentas-corrientes", summary="Saldos de clientes y proveedores")
async def cuentas_corrientes(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    empresa_id = current_user["empresa_id"]
    clientes = await db.execute(
        text("SELECT * FROM v_saldo_clientes WHERE empresa_id = :e ORDER BY saldo_pendiente DESC"),
        {"e": empresa_id},
    )
    proveedores = await db.execute(
        text("SELECT * FROM v_saldo_proveedores WHERE empresa_id = :e ORDER BY saldo_pendiente DESC"),
        {"e": empresa_id},
    )
    return {
        "clientes": clientes.mappings().all(),
        "proveedores": proveedores.mappings().all(),
    }


@router.get("/flujo-mensual", summary="Ingresos vs egresos por mes")
async def flujo_mensual(
    meses: int = Query(6, description="Cantidad de meses hacia atrás (usado si no se pasa desde/hasta)"),
    desde: Optional[date] = Query(None, description="Fecha inicio (YYYY-MM-DD)"),
    hasta: Optional[date] = Query(None, description="Fecha fin (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Retorna serie mensual de ingresos (ventas a clientes) y egresos (compras a proveedores).
    Si se pasan desde/hasta se usa ese rango; si no, se usan los últimos N meses.
    """
    empresa_id = current_user["empresa_id"]

    # Generamos la lista de meses en Python (cross-database simple), después
    # un solo query agrupado por YYYY-MM y mergeamos en el server.
    if desde is not None:
        hasta_real = hasta or date.today()
        meses_rango = (hasta_real.year - desde.year) * 12 + (hasta_real.month - desde.month) + 1
        meses_rango = max(1, min(meses_rango, 120))
        inicio = date(desde.year, desde.month, 1)
    else:
        # "Todo": buscar la fecha más antigua en la DB para cubrir el historial completo
        min_row = await db.execute(
            text("""
                SELECT MIN(fecha_emision) AS min_fecha
                FROM comprobantes
                WHERE empresa_id = :empresa_id
                  AND estado_validacion NOT IN ('anulado','rechazado')
            """),
            {"empresa_id": empresa_id},
        )
        min_fecha = min_row.mappings().first()["min_fecha"]
        if min_fecha is None:
            return []
        if isinstance(min_fecha, str):
            min_fecha = date.fromisoformat(min_fecha[:10])
        hoy = date.today()
        inicio = date(min_fecha.year, min_fecha.month, 1)
        meses_rango = (hoy.year - inicio.year) * 12 + (hoy.month - inicio.month) + 1
        meses_rango = max(1, min(meses_rango, 120))

    # Lista de tuplas (periodo='YYYY-MM', etiqueta='Mon YYYY')
    meses_lst = []
    cy, cm = inicio.year, inicio.month
    nombres_es = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic']
    for _ in range(meses_rango):
        meses_lst.append({
            "periodo":  f"{cy:04d}-{cm:02d}",
            "etiqueta": f"{nombres_es[cm-1]} {cy}",
            # Facturado por mes (ventas y compras emitidas)
            "ingresos": 0, "egresos": 0, "facturas": 0,
            # Caja real por mes (cobros recibidos y pagos efectuados)
            "cobros": 0, "pagos_realizados": 0,
        })
        cm += 1
        if cm > 12: cm = 1; cy += 1

    fin = date(cy, cm, 1)  # exclusive

    # 1) Facturado por mes (sobre comprobantes.fecha_emision)
    rows = await db.execute(
        text("""
            SELECT
                substr(CAST(fecha_emision AS TEXT), 1, 7) AS periodo,
                COALESCE(SUM(CASE WHEN cliente_id   IS NOT NULL THEN monto_total ELSE 0 END), 0) AS ingresos,
                COALESCE(SUM(CASE WHEN proveedor_id IS NOT NULL THEN monto_total ELSE 0 END), 0) AS egresos,
                COUNT(*) AS facturas
            FROM comprobantes
            WHERE empresa_id = :empresa_id
              AND estado_validacion NOT IN ('anulado','rechazado')
              AND fecha_emision >= :desde
              AND fecha_emision <  :fin
            GROUP BY substr(CAST(fecha_emision AS TEXT), 1, 7)
        """),
        {"empresa_id": empresa_id, "desde": inicio, "fin": fin},
    )
    by_periodo = {r["periodo"]: r for r in rows.mappings().all()}
    for m in meses_lst:
        if m["periodo"] in by_periodo:
            row = by_periodo[m["periodo"]]
            m["ingresos"] = float(row["ingresos"] or 0)
            m["egresos"]  = float(row["egresos"] or 0)
            m["facturas"] = int(row["facturas"] or 0)

    # 2) Caja real por mes (sobre pagos.fecha_pago):
    #    cobros = pagos recibidos de clientes; pagos_realizados = pagos a proveedores.
    rows_caja = await db.execute(
        text("""
            SELECT
                substr(CAST(p.fecha_pago AS TEXT), 1, 7) AS periodo,
                COALESCE(SUM(CASE WHEN c.cliente_id   IS NOT NULL THEN p.monto_pagado ELSE 0 END), 0) AS cobros,
                COALESCE(SUM(CASE WHEN c.proveedor_id IS NOT NULL THEN p.monto_pagado ELSE 0 END), 0) AS pagos_realizados
            FROM pagos p
            JOIN comprobantes c ON c.id = p.comprobante_id
            WHERE p.empresa_id = :empresa_id
              AND p.fecha_pago >= :desde
              AND p.fecha_pago <  :fin
            GROUP BY substr(CAST(p.fecha_pago AS TEXT), 1, 7)
        """),
        {"empresa_id": empresa_id, "desde": inicio, "fin": fin},
    )
    by_periodo_caja = {r["periodo"]: r for r in rows_caja.mappings().all()}
    for m in meses_lst:
        if m["periodo"] in by_periodo_caja:
            row = by_periodo_caja[m["periodo"]]
            m["cobros"]            = float(row["cobros"] or 0)
            m["pagos_realizados"]  = float(row["pagos_realizados"] or 0)

    return meses_lst


@router.get("/top-clientes", summary="Top N clientes por facturación")
async def top_clientes(
    limite: int = Query(5),
    desde: Optional[date] = Query(None),
    hasta: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    empresa_id = current_user["empresa_id"]
    limite = max(1, min(int(limite or 5), 20))
    cond, params = _filtro_fecha("c.fecha_emision", desde, hasta)

    result = await db.execute(
        text(f"""
            SELECT cl.id           AS cliente_id,
                   cl.nombre       AS cliente,
                   COALESCE(SUM(c.monto_total), 0)      AS total_facturado,
                   COALESCE(SUM(c.saldo_pendiente), 0)  AS saldo_pendiente,
                   COUNT(c.id)     AS facturas
            FROM clientes cl
            LEFT JOIN comprobantes c
                   ON c.cliente_id = cl.id
                  AND c.empresa_id = cl.empresa_id
                  AND c.estado_validacion NOT IN ('anulado', 'rechazado')
                  {cond}
            WHERE cl.empresa_id = :empresa_id
            GROUP BY cl.id, cl.nombre
            HAVING COALESCE(SUM(c.monto_total), 0) > 0
            ORDER BY total_facturado DESC
            LIMIT :limite
        """),
        {"empresa_id": empresa_id, "limite": limite, **params},
    )
    return [dict(r) for r in result.mappings().all()]


@router.get("/medios-pago", summary="Distribución de pagos por medio")
async def medios_pago(
    desde: Optional[date] = Query(None),
    hasta: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    empresa_id = current_user["empresa_id"]

    if desde is not None:
        hasta_real = hasta or date.today()
        cond = "AND p.fecha_pago BETWEEN :desde AND :hasta"
        params: dict = {"empresa_id": empresa_id, "desde": desde, "hasta": hasta_real}
    else:
        # Sin filtro: todo el historial
        cond = ""
        params = {"empresa_id": empresa_id}

    result = await db.execute(
        text(f"""
            SELECT COALESCE(p.medio_pago, 'otros')  AS medio,
                   COUNT(*)                          AS cantidad,
                   COALESCE(SUM(p.monto_pagado), 0)  AS monto_total
            FROM pagos p
            JOIN comprobantes c ON c.id = p.comprobante_id
            WHERE c.empresa_id = :empresa_id
              {cond}
            GROUP BY p.medio_pago
            ORDER BY monto_total DESC
        """),
        params,
    )
    return [dict(r) for r in result.mappings().all()]


@router.get("/ultimos-comprobantes", summary="Últimos N comprobantes cargados")
async def ultimos_comprobantes(
    limite: int = Query(5),
    desde: Optional[date] = Query(None),
    hasta: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    empresa_id = current_user["empresa_id"]
    limite = max(1, min(int(limite or 5), 20))
    cond, params = _filtro_fecha("c.fecha_emision", desde, hasta)

    result = await db.execute(
        text(f"""
            SELECT c.id,
                   c.numero_comprobante,
                   c.fecha_emision,
                   c.monto_total,
                   c.estado_validacion,
                   c.metodo_carga,
                   COALESCE(cl.nombre, pr.nombre, '—')  AS contraparte,
                   CASE WHEN c.cliente_id IS NOT NULL THEN 'venta' ELSE 'compra' END AS tipo
            FROM comprobantes c
            LEFT JOIN clientes cl    ON cl.id = c.cliente_id
            LEFT JOIN proveedores pr ON pr.id = c.proveedor_id
            WHERE c.empresa_id = :empresa_id
              {cond}
            ORDER BY c.fecha_emision DESC, c.fecha_creacion DESC
            LIMIT :limite
        """),
        {"empresa_id": empresa_id, "limite": limite, **params},
    )
    return [dict(r) for r in result.mappings().all()]


@router.get("/stock-critico", summary="Items por debajo del punto de reorden")
async def stock_critico(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    empresa_id = current_user["empresa_id"]
    result = await db.execute(
        text("""
            SELECT i.descripcion, i.codigo, i.cantidad_actual,
                   i.punto_reorden, i.unidad_medida,
                   c.nombre AS categoria
            FROM inventario i
            LEFT JOIN categorias_inventario c ON c.id = i.categoria_id
            WHERE i.empresa_id = :empresa_id
              AND i.activo = TRUE
              AND i.punto_reorden > 0
              AND i.cantidad_actual <= i.punto_reorden
            ORDER BY (i.cantidad_actual / NULLIF(i.punto_reorden, 0)) ASC
        """),
        {"empresa_id": empresa_id},
    )
    return result.mappings().all()
