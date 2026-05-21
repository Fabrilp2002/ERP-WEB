"""
Servicio de análisis histórico por cliente/proveedor.

Calcula resumen de negocio, hábitos de pago, devoluciones, top productos y
score 🟢🟡🔴 a partir de datos ya existentes en `comprobantes`, `pagos` y
`detalle_comprobantes`. No introduce tablas nuevas.

Las Notas de Crédito (NC) y Notas de Débito (ND) se detectan por nombre del
tipo de comprobante (`tipos_comprobante.nombre` contiene 'credito' / 'debito'),
mismo patrón que `routers/comprobantes._tipo_movimiento_nota`.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Literal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


Rol = Literal["cliente", "proveedor"]


def _d(value) -> str:
    """Convierte Decimal/float/None a string sin notación científica.

    El frontend siempre maneja montos como string para evitar floats.
    """
    if value is None:
        return "0"
    if isinstance(value, Decimal):
        return format(value, "f")
    return format(Decimal(str(value)), "f")


def _calcular_score(
    porcentaje_devolucion: float,
    promedio_dias_pago: int | None,
    plazo_promedio_dias: int | None,
    tiene_saldo_60_mas: bool,
    dias_desde_ultima_compra: int | None,
    cantidad_facturas: int,
) -> dict:
    """Score simple y transparente según regla del plan.

    Devuelve `{"color": "verde"|"amarillo"|"rojo", "puntos": int, "razones": [...]}`.
    Si hay menos de 3 facturas devuelve color "gris" con razón "Datos insuficientes".
    """
    if cantidad_facturas < 3:
        return {"color": "gris", "puntos": None, "razones": ["Datos insuficientes (menos de 3 facturas)"]}

    puntos = 100
    razones: list[str] = []

    if porcentaje_devolucion > 20:
        puntos -= 50
        razones.append(f"Devoluciones altas ({porcentaje_devolucion:.0f}%)")
    elif porcentaje_devolucion > 10:
        puntos -= 20
        razones.append(f"Devoluciones por encima del 10% ({porcentaje_devolucion:.0f}%)")

    if promedio_dias_pago is not None and plazo_promedio_dias is not None:
        if promedio_dias_pago > plazo_promedio_dias + 7:
            puntos -= 15
            razones.append(f"Tarda {promedio_dias_pago} días en pagar (plazo {plazo_promedio_dias})")

    if tiene_saldo_60_mas:
        puntos -= 25
        razones.append("Tiene facturas vencidas hace más de 60 días")

    if dias_desde_ultima_compra is not None and dias_desde_ultima_compra > 90:
        puntos -= 15
        razones.append(f"No compra hace {dias_desde_ultima_compra} días")

    puntos = max(0, puntos)
    if puntos >= 75:
        color = "verde"
    elif puntos >= 50:
        color = "amarillo"
    else:
        color = "rojo"

    if not razones:
        razones.append("Sin alertas")
    return {"color": color, "puntos": puntos, "razones": razones}


async def analizar_contraparte(
    db: AsyncSession,
    empresa_id: str,
    rol: Rol,
    contraparte_id: str,
) -> dict:
    """Devuelve el JSON completo de análisis para un cliente o proveedor.

    Lanza ValueError si la contraparte no existe en la empresa.
    """
    col_fk = "cliente_id" if rol == "cliente" else "proveedor_id"
    tabla_contraparte = "clientes" if rol == "cliente" else "proveedores"

    contraparte = (await db.execute(
        text(f"""
            SELECT id, nombre, ruc, fecha_creacion
            FROM {tabla_contraparte}
            WHERE id = :id AND empresa_id = :eid
        """),
        {"id": contraparte_id, "eid": empresa_id},
    )).mappings().first()
    if not contraparte:
        raise ValueError(f"{rol.capitalize()} no encontrado")

    cte_clasificacion = f"""
        WITH comp_clasificado AS (
            SELECT
                c.id,
                c.numero_comprobante,
                c.fecha_emision,
                c.fecha_vencimiento,
                c.monto_total,
                c.saldo_pendiente,
                c.comprobante_origen_id,
                c.condicion,
                CASE
                    WHEN LOWER(tc.nombre) LIKE '%credito%'
                      OR LOWER(tc.nombre) LIKE '%crédito%' THEN -1
                    WHEN LOWER(tc.nombre) LIKE '%debito%'
                      OR LOWER(tc.nombre) LIKE '%débito%' THEN 1
                    ELSE 0
                END AS movimiento
            FROM comprobantes c
            JOIN tipos_comprobante tc ON tc.id = c.tipo_id
            WHERE c.empresa_id = :eid
              AND c.{col_fk} = :cid
              AND c.estado_validacion = 'confirmado'
        )
    """

    resumen_row = (await db.execute(
        text(cte_clasificacion + """
            SELECT
                COUNT(*) FILTER (WHERE movimiento = 0)  AS cantidad_facturas,
                COALESCE(SUM(monto_total) FILTER (WHERE movimiento = 0), 0)  AS total_facturado,
                COALESCE(SUM(monto_total) FILTER (WHERE movimiento = -1), 0) AS total_devoluciones,
                COALESCE(SUM(monto_total) FILTER (WHERE movimiento = 1), 0)  AS total_cargos_extra,
                COALESCE(SUM(saldo_pendiente) FILTER (WHERE movimiento = 0), 0) AS saldo_pendiente,
                MAX(fecha_emision) FILTER (WHERE movimiento = 0) AS ultima_factura,
                BOOL_OR(
                    movimiento = 0
                    AND saldo_pendiente > 0
                    AND fecha_vencimiento IS NOT NULL
                    AND fecha_vencimiento < CURRENT_DATE - INTERVAL '60 days'
                ) AS tiene_saldo_60_mas
            FROM comp_clasificado
        """),
        {"eid": empresa_id, "cid": contraparte_id},
    )).mappings().first()

    cantidad_facturas = int(resumen_row["cantidad_facturas"] or 0)
    total_facturado = Decimal(resumen_row["total_facturado"] or 0)
    total_devoluciones = Decimal(resumen_row["total_devoluciones"] or 0)
    total_cargos_extra = Decimal(resumen_row["total_cargos_extra"] or 0)
    saldo_pendiente = Decimal(resumen_row["saldo_pendiente"] or 0)
    compra_neta = total_facturado - total_devoluciones + total_cargos_extra
    porcentaje_devolucion = float(
        (total_devoluciones / total_facturado * 100) if total_facturado > 0 else 0
    )

    ya_cobrado_row = (await db.execute(
        text(f"""
            SELECT COALESCE(SUM(p.monto_pagado), 0) AS total
            FROM pagos p
            JOIN comprobantes c ON c.id = p.comprobante_id
            WHERE p.empresa_id = :eid AND c.{col_fk} = :cid
        """),
        {"eid": empresa_id, "cid": contraparte_id},
    )).mappings().first()
    ya_cobrado = Decimal(ya_cobrado_row["total"] or 0)

    habitos_row = (await db.execute(
        text(f"""
            SELECT
                AVG(EXTRACT(EPOCH FROM (p.fecha_pago - c.fecha_emision)) / 86400.0)::int AS promedio_dias,
                MIN(EXTRACT(EPOCH FROM (p.fecha_pago - c.fecha_emision)) / 86400.0)::int AS mejor_dias,
                MAX(EXTRACT(EPOCH FROM (p.fecha_pago - c.fecha_emision)) / 86400.0)::int AS peor_dias,
                AVG(EXTRACT(EPOCH FROM (c.fecha_vencimiento - c.fecha_emision)) / 86400.0)::int AS plazo_promedio_dias
            FROM pagos p
            JOIN comprobantes c ON c.id = p.comprobante_id
            JOIN tipos_comprobante tc ON tc.id = c.tipo_id
            WHERE p.empresa_id = :eid AND c.{col_fk} = :cid
              AND LOWER(tc.nombre) NOT LIKE '%credito%'
              AND LOWER(tc.nombre) NOT LIKE '%crédito%'
              AND LOWER(tc.nombre) NOT LIKE '%debito%'
              AND LOWER(tc.nombre) NOT LIKE '%débito%'
        """),
        {"eid": empresa_id, "cid": contraparte_id},
    )).mappings().first()

    medio_row = (await db.execute(
        text(f"""
            SELECT p.medio_pago, COUNT(*) AS cnt
            FROM pagos p
            JOIN comprobantes c ON c.id = p.comprobante_id
            WHERE p.empresa_id = :eid AND c.{col_fk} = :cid
              AND p.medio_pago IS NOT NULL
            GROUP BY p.medio_pago
            ORDER BY cnt DESC
            LIMIT 1
        """),
        {"eid": empresa_id, "cid": contraparte_id},
    )).mappings().first()

    total_pagos_row = (await db.execute(
        text(f"""
            SELECT COUNT(*) AS total
            FROM pagos p
            JOIN comprobantes c ON c.id = p.comprobante_id
            WHERE p.empresa_id = :eid AND c.{col_fk} = :cid
        """),
        {"eid": empresa_id, "cid": contraparte_id},
    )).mappings().first()
    total_pagos = int(total_pagos_row["total"] or 0)

    medio_favorito = medio_row["medio_pago"] if medio_row else None
    porcentaje_medio_favorito = (
        round(int(medio_row["cnt"]) / total_pagos * 100) if medio_row and total_pagos else 0
    )

    ultima_compra = resumen_row["ultima_factura"]
    dias_desde_ultima_compra = None
    if ultima_compra is not None:
        delta_row = (await db.execute(
            text("SELECT (CURRENT_DATE - :ult)::int AS d"),
            {"ult": ultima_compra},
        )).mappings().first()
        dias_desde_ultima_compra = int(delta_row["d"])

    top_productos_rows = (await db.execute(
        text(cte_clasificacion + """
            SELECT
                COALESCE(i.nombre, d.descripcion) AS producto,
                SUM(d.cantidad) AS cantidad,
                COUNT(DISTINCT cc.id) AS ventas,
                SUM(d.subtotal) AS total
            FROM comp_clasificado cc
            JOIN detalle_comprobantes d ON d.comprobante_id = cc.id
            LEFT JOIN inventario i ON i.id = d.inventario_id
            WHERE cc.movimiento = 0
            GROUP BY COALESCE(i.nombre, d.descripcion)
            ORDER BY total DESC
            LIMIT 5
        """),
        {"eid": empresa_id, "cid": contraparte_id},
    )).mappings().all()

    devoluciones_top_rows = (await db.execute(
        text(cte_clasificacion + """
            SELECT
                COALESCE(i.nombre, d.descripcion) AS producto,
                COUNT(DISTINCT cc.id) AS veces,
                SUM(d.cantidad) AS cantidad,
                SUM(d.subtotal) AS monto
            FROM comp_clasificado cc
            JOIN detalle_comprobantes d ON d.comprobante_id = cc.id
            LEFT JOIN inventario i ON i.id = d.inventario_id
            WHERE cc.movimiento = -1
            GROUP BY COALESCE(i.nombre, d.descripcion)
            ORDER BY monto DESC
            LIMIT 5
        """),
        {"eid": empresa_id, "cid": contraparte_id},
    )).mappings().all()

    notas_credito_rows = (await db.execute(
        text(cte_clasificacion + """
            SELECT
                cc.id,
                cc.numero_comprobante AS numero,
                cc.fecha_emision AS fecha,
                cc.monto_total AS monto,
                origen.numero_comprobante AS factura_origen_numero,
                cc.comprobante_origen_id AS factura_origen_id
            FROM comp_clasificado cc
            LEFT JOIN comprobantes origen ON origen.id = cc.comprobante_origen_id
            WHERE cc.movimiento = -1
            ORDER BY cc.fecha_emision DESC
            LIMIT 50
        """),
        {"eid": empresa_id, "cid": contraparte_id},
    )).mappings().all()

    notas_debito_rows = (await db.execute(
        text(cte_clasificacion + """
            SELECT
                cc.id,
                cc.numero_comprobante AS numero,
                cc.fecha_emision AS fecha,
                cc.monto_total AS monto,
                origen.numero_comprobante AS factura_origen_numero,
                cc.comprobante_origen_id AS factura_origen_id
            FROM comp_clasificado cc
            LEFT JOIN comprobantes origen ON origen.id = cc.comprobante_origen_id
            WHERE cc.movimiento = 1
            ORDER BY cc.fecha_emision DESC
            LIMIT 50
        """),
        {"eid": empresa_id, "cid": contraparte_id},
    )).mappings().all()

    score = _calcular_score(
        porcentaje_devolucion=porcentaje_devolucion,
        promedio_dias_pago=habitos_row["promedio_dias"] if habitos_row else None,
        plazo_promedio_dias=habitos_row["plazo_promedio_dias"] if habitos_row else None,
        tiene_saldo_60_mas=bool(resumen_row["tiene_saldo_60_mas"]),
        dias_desde_ultima_compra=dias_desde_ultima_compra,
        cantidad_facturas=cantidad_facturas,
    )

    return {
        "contraparte": {
            "id": str(contraparte["id"]),
            "rol": rol,
            "nombre": contraparte["nombre"],
            "ruc": contraparte["ruc"],
            "fecha_alta": contraparte["fecha_creacion"].isoformat() if contraparte["fecha_creacion"] else None,
        },
        "resumen": {
            "cantidad_facturas": cantidad_facturas,
            "total_facturado": _d(total_facturado),
            "total_devoluciones": _d(total_devoluciones),
            "total_cargos_extra": _d(total_cargos_extra),
            "compra_neta": _d(compra_neta),
            "ya_cobrado": _d(ya_cobrado),
            "saldo_pendiente": _d(saldo_pendiente),
            "porcentaje_devolucion": round(porcentaje_devolucion, 1),
        },
        "habitos_pago": {
            "promedio_dias": habitos_row["promedio_dias"] if habitos_row else None,
            "mejor_dias": habitos_row["mejor_dias"] if habitos_row else None,
            "peor_dias": habitos_row["peor_dias"] if habitos_row else None,
            "plazo_promedio_dias": habitos_row["plazo_promedio_dias"] if habitos_row else None,
            "medio_favorito": medio_favorito,
            "porcentaje_medio_favorito": porcentaje_medio_favorito,
            "ultima_compra": ultima_compra.isoformat() if ultima_compra else None,
            "dias_desde_ultima_compra": dias_desde_ultima_compra,
            "tiene_saldo_60_mas": bool(resumen_row["tiene_saldo_60_mas"]),
        },
        "score": score,
        "top_productos": [
            {
                "producto": r["producto"],
                "cantidad": _d(r["cantidad"]),
                "ventas": int(r["ventas"]),
                "total": _d(r["total"]),
            }
            for r in top_productos_rows
        ],
        "devoluciones": {
            "top_productos": [
                {
                    "producto": r["producto"],
                    "veces": int(r["veces"]),
                    "cantidad": _d(r["cantidad"]),
                    "monto": _d(r["monto"]),
                }
                for r in devoluciones_top_rows
            ],
            "notas_credito": [
                {
                    "id": str(r["id"]),
                    "numero": r["numero"],
                    "fecha": r["fecha"].isoformat() if r["fecha"] else None,
                    "monto": _d(r["monto"]),
                    "factura_origen_numero": r["factura_origen_numero"],
                    "factura_origen_id": str(r["factura_origen_id"]) if r["factura_origen_id"] else None,
                }
                for r in notas_credito_rows
            ],
        },
        "cargos_extra": {
            "notas_debito": [
                {
                    "id": str(r["id"]),
                    "numero": r["numero"],
                    "fecha": r["fecha"].isoformat() if r["fecha"] else None,
                    "monto": _d(r["monto"]),
                    "factura_origen_numero": r["factura_origen_numero"],
                    "factura_origen_id": str(r["factura_origen_id"]) if r["factura_origen_id"] else None,
                }
                for r in notas_debito_rows
            ],
        },
    }
