"""
Router Export — Descarga de reportes Excel.
Accesible por todos los roles (incluyendo viewer — solo lectura).
"""
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from io import BytesIO
from ..core.database import get_db
from ..core.security import get_current_user
from ..services.export import (
    generar_excel_comprobantes,
    generar_excel_cuentas_corrientes,
    generar_excel_inventario,
    generar_excel_movimientos,
    generar_excel_iva,
)

router = APIRouter(prefix="/export", tags=["Exportación Excel"])


def _excel_response(data: bytes, filename: str) -> StreamingResponse:
    return StreamingResponse(
        BytesIO(data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _build_date_filter(mes: str | None, desde: str | None, hasta: str | None, col: str):
    filtros = ""
    params = {}
    if mes:
        filtros += f" AND substr(CAST({col} AS TEXT), 1, 7) = :mes"
        params["mes"] = mes
    else:
        if desde:
            filtros += f" AND {col} >= :desde"
            params["desde"] = desde
        if hasta:
            filtros += f" AND {col} <= :hasta"
            params["hasta"] = hasta
    return filtros, params


def _periodo_label(mes: str | None, desde: str | None, hasta: str | None) -> str:
    if mes:
        return mes
    if desde and hasta:
        return f"{desde} a {hasta}"
    if desde:
        return f"desde {desde}"
    if hasta:
        return f"hasta {hasta}"
    return "Todo el periodo"


@router.get("/comprobantes", summary="Exportar comprobantes a Excel")
async def export_comprobantes(
    estado: str = Query(None, description="Filtrar por estado_validacion"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    empresa_id = current_user["empresa_id"]
    filtro = "AND c.estado_validacion = :estado" if estado else ""

    result = await db.execute(
        text(f"""
            SELECT c.numero_comprobante, c.fecha_emision, c.fecha_vencimiento,
                   CASE WHEN c.cliente_id IS NOT NULL THEN 'Venta' ELSE 'Compra' END AS tipo,
                   COALESCE(cl.nombre, pr.nombre, '—') AS contraparte,
                   COALESCE(cl.ruc, pr.ruc, '') AS contraparte_ruc,
                   c.condicion, c.monto_subtotal,
                   c.monto_iva, c.monto_total, c.saldo_pendiente,
                   c.metodo_carga, c.estado_validacion, c.ubicacion_fisica
            FROM comprobantes c
            LEFT JOIN clientes cl    ON cl.id = c.cliente_id
            LEFT JOIN proveedores pr ON pr.id = c.proveedor_id
            WHERE c.empresa_id = :empresa_id {filtro}
            ORDER BY c.fecha_emision DESC
        """),
        {"empresa_id": empresa_id, "estado": estado},
    )
    filas = [dict(r) for r in result.mappings().all()]

    # Nombre de empresa
    emp_result = await db.execute(
        text("SELECT nombre FROM empresas WHERE id = :id"),
        {"id": empresa_id},
    )
    empresa_nombre = emp_result.scalar() or "ERP"

    excel = generar_excel_comprobantes(filas, empresa_nombre)
    return _excel_response(excel, f"Comprobantes_{empresa_nombre}.xlsx")


@router.get("/iva/{tipo}", summary="Exportar Libro IVA a Excel")
async def export_iva(
    tipo: str,
    mes: str = Query(None, description="YYYY-MM"),
    desde: str = Query(None, description="YYYY-MM-DD inclusive"),
    hasta: str = Query(None, description="YYYY-MM-DD inclusive"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if tipo not in {"ventas", "compras"}:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="Tipo invalido: use ventas o compras")

    empresa_id = current_user["empresa_id"]
    filtros, params = _build_date_filter(mes, desde, hasta, "c.fecha_emision")
    params["empresa_id"] = empresa_id

    if tipo == "ventas":
        sql = f"""
            SELECT
                cl.ruc AS ruc_comprador,
                cl.nombre AS razon_social,
                c.numero_comprobante,
                c.fecha_emision,
                tc.nombre AS tipo_comprobante,
                COALESCE(SUM(CASE WHEN d.porcentaje_iva = 10 THEN d.subtotal ELSE 0 END), 0) AS base_gravada_10,
                COALESCE(SUM(CASE WHEN d.porcentaje_iva = 10 THEN d.iva_monto ELSE 0 END), 0) AS iva_10,
                COALESCE(SUM(CASE WHEN d.porcentaje_iva = 5 THEN d.subtotal ELSE 0 END), 0) AS base_gravada_5,
                COALESCE(SUM(CASE WHEN d.porcentaje_iva = 5 THEN d.iva_monto ELSE 0 END), 0) AS iva_5,
                COALESCE(SUM(CASE WHEN d.porcentaje_iva = 0 THEN d.subtotal ELSE 0 END), 0) AS exentas,
                c.monto_total AS total
            FROM comprobantes c
            JOIN clientes cl ON cl.id = c.cliente_id
            LEFT JOIN tipos_comprobante tc ON tc.id = c.tipo_id
            LEFT JOIN detalle_comprobantes d ON d.comprobante_id = c.id
            WHERE c.empresa_id = :empresa_id
              AND c.cliente_id IS NOT NULL
              AND c.estado_validacion = 'confirmado'
              {filtros}
            GROUP BY c.id, cl.ruc, cl.nombre, c.numero_comprobante, c.fecha_emision, tc.nombre, c.monto_total
            ORDER BY c.fecha_emision, c.numero_comprobante
        """
        money_fields = ["base_gravada_10", "iva_10", "base_gravada_5", "iva_5", "exentas", "total"]
    else:
        sql = f"""
            SELECT
                pr.ruc AS ruc_proveedor,
                pr.nombre AS razon_social,
                c.numero_comprobante,
                c.fecha_emision,
                tc.nombre AS tipo_comprobante,
                COALESCE(SUM(CASE WHEN d.porcentaje_iva = 10 THEN d.subtotal ELSE 0 END), 0) AS base_gravada_10,
                COALESCE(SUM(CASE WHEN d.porcentaje_iva = 10 THEN d.iva_monto ELSE 0 END), 0) AS credito_fiscal_10,
                COALESCE(SUM(CASE WHEN d.porcentaje_iva = 5 THEN d.subtotal ELSE 0 END), 0) AS base_gravada_5,
                COALESCE(SUM(CASE WHEN d.porcentaje_iva = 5 THEN d.iva_monto ELSE 0 END), 0) AS credito_fiscal_5,
                COALESCE(SUM(CASE WHEN d.porcentaje_iva = 0 THEN d.subtotal ELSE 0 END), 0) AS exentas,
                c.monto_total AS total
            FROM comprobantes c
            JOIN proveedores pr ON pr.id = c.proveedor_id
            LEFT JOIN tipos_comprobante tc ON tc.id = c.tipo_id
            LEFT JOIN detalle_comprobantes d ON d.comprobante_id = c.id
            WHERE c.empresa_id = :empresa_id
              AND c.proveedor_id IS NOT NULL
              AND c.estado_validacion = 'confirmado'
              {filtros}
            GROUP BY c.id, pr.ruc, pr.nombre, c.numero_comprobante, c.fecha_emision, tc.nombre, c.monto_total
            ORDER BY c.fecha_emision, c.numero_comprobante
        """
        money_fields = ["base_gravada_10", "credito_fiscal_10", "base_gravada_5", "credito_fiscal_5", "exentas", "total"]

    filas = [dict(r) for r in (await db.execute(text(sql), params)).mappings().all()]
    totales = {field: sum(f[field] for f in filas) for field in money_fields}
    empresa_nombre = (await db.execute(
        text("SELECT nombre FROM empresas WHERE id = :id"),
        {"id": empresa_id},
    )).scalar() or "ERP"

    periodo = _periodo_label(mes, desde, hasta)
    excel = generar_excel_iva(tipo, filas, totales, empresa_nombre, periodo)
    return _excel_response(excel, f"Libro_IVA_{tipo}_{periodo.replace(' ', '_')}.xlsx")


@router.get("/cuentas-corrientes", summary="Exportar cuentas corrientes a Excel")
async def export_cuentas_corrientes(
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

    emp_result = await db.execute(
        text("SELECT nombre FROM empresas WHERE id = :id"),
        {"id": empresa_id},
    )
    empresa_nombre = emp_result.scalar() or "ERP"

    excel = generar_excel_cuentas_corrientes(
        [dict(r) for r in clientes.mappings().all()],
        [dict(r) for r in proveedores.mappings().all()],
        empresa_nombre,
    )
    return _excel_response(excel, f"Cuentas_Corrientes_{empresa_nombre}.xlsx")


@router.get("/movimientos", summary="Exportar movimientos (cobros + pagos) a Excel")
async def export_movimientos(
    desde: str = Query(None, description="YYYY-MM-DD inclusive"),
    hasta: str = Query(None, description="YYYY-MM-DD inclusive"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    empresa_id = current_user["empresa_id"]
    filtros = []
    params: dict = {"empresa_id": empresa_id}
    if desde:
        filtros.append("p.fecha_pago >= :desde"); params["desde"] = desde
    if hasta:
        filtros.append("p.fecha_pago <= :hasta"); params["hasta"] = hasta
    where_extra = (" AND " + " AND ".join(filtros)) if filtros else ""

    result = await db.execute(
        text(f"""
            SELECT
                CASE WHEN c.cliente_id IS NOT NULL THEN 'cobro' ELSE 'pago' END AS tipo,
                p.fecha_pago,
                c.numero_comprobante,
                COALESCE(cl.nombre, pr.nombre, '—') AS contraparte,
                COALESCE(cl.ruc, pr.ruc, '') AS contraparte_ruc,
                p.numero_recibo,
                p.monto_pagado,
                p.medio_pago,
                p.notas,
                TRIM(COALESCE(u.nombre,'') || ' ' || COALESCE(u.apellido,'')) AS usuario
            FROM pagos p
            JOIN comprobantes c    ON c.id = p.comprobante_id
            LEFT JOIN clientes cl  ON cl.id = c.cliente_id
            LEFT JOIN proveedores pr ON pr.id = c.proveedor_id
            LEFT JOIN usuarios u   ON u.id = p.usuario_id
            WHERE p.empresa_id = :empresa_id {where_extra}
            ORDER BY p.fecha_pago DESC
        """),
        params,
    )
    filas = [dict(r) for r in result.mappings().all()]
    cobros = [f for f in filas if f["tipo"] == "cobro"]
    pagos_l = [f for f in filas if f["tipo"] == "pago"]

    emp_result = await db.execute(
        text("SELECT nombre FROM empresas WHERE id = :id"),
        {"id": empresa_id},
    )
    empresa_nombre = emp_result.scalar() or "ERP"

    excel = generar_excel_movimientos(cobros, pagos_l, empresa_nombre)
    return _excel_response(excel, f"Movimientos_{empresa_nombre}.xlsx")


@router.get("/inventario", summary="Exportar inventario a Excel")
async def export_inventario(
    solo_critico: bool = Query(False, description="Solo items bajo punto de reorden"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    empresa_id = current_user["empresa_id"]
    filtro_critico = "AND i.cantidad_actual <= i.punto_reorden AND i.punto_reorden > 0" if solo_critico else ""

    result = await db.execute(
        text(f"""
            SELECT i.codigo, i.descripcion, i.unidad_medida,
                   i.cantidad_actual, i.punto_reorden, i.costo_unitario
            FROM inventario i
            WHERE i.empresa_id = :empresa_id AND i.activo = TRUE {filtro_critico}
            ORDER BY i.descripcion
        """),
        {"empresa_id": empresa_id},
    )

    emp_result = await db.execute(
        text("SELECT nombre FROM empresas WHERE id = :id"),
        {"id": empresa_id},
    )
    empresa_nombre = emp_result.scalar() or "ERP"

    excel = generar_excel_inventario(
        [dict(r) for r in result.mappings().all()],
        empresa_nombre,
    )
    return _excel_response(excel, f"Inventario_{empresa_nombre}.xlsx")
