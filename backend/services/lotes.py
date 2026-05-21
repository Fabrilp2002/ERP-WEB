"""
Servicio v7.1 — Trazabilidad de lotes + Costo Promedio Ponderado.

Reglas:
- FEFO: las salidas consumen primero el lote con `fecha_vencimiento` más cercana
  (NULLs van al final), empate desempata por `fecha_ingreso` ASC.
- CPP: el campo `inventario.costo_unitario` representa el costo promedio
  ponderado vigente. Se recalcula sólo en INGRESOS:
      cpp_nuevo = (stock_ant * costo_ant + cant_nueva * costo_nuevo)
                  / (stock_ant + cant_nueva)
- Toda mutación de stock queda registrada en `inventario_movimientos` (kardex).

Esta capa NO commitea. El caller decide cuándo cerrar la transacción.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Iterable

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class LoteError(Exception):
    """Errores de dominio del módulo de lotes (stock insuficiente, etc)."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _cargar_inventario(db: AsyncSession, empresa_id: str, inventario_id: str) -> dict:
    row = (await db.execute(
        text("""
            SELECT id, cantidad_actual, costo_unitario
            FROM inventario
            WHERE id = :id AND empresa_id = :eid AND activo = TRUE
        """),
        {"id": inventario_id, "eid": empresa_id},
    )).mappings().first()
    if not row:
        raise LoteError(404, "Item de inventario no encontrado")
    return dict(row)


# ── Crear lote (ingreso de mercadería) ───────────────────────────────────────

async def crear_lote(
    db: AsyncSession,
    *,
    empresa_id: str,
    inventario_id: str,
    numero_lote: str,
    cantidad: Decimal,
    costo_unitario: Decimal,
    fecha_ingreso: date | None = None,
    fecha_vencimiento: date | None = None,
    proveedor_id: str | None = None,
    comprobante_id: str | None = None,
    usuario_id: str | None = None,
    notas: str | None = None,
) -> dict:
    """Registra un lote nuevo, actualiza stock e item.costo_unitario (CPP).

    Devuelve el lote creado + el kardex generado.
    """
    if cantidad <= 0:
        raise LoteError(422, "La cantidad debe ser mayor que cero")
    if costo_unitario < 0:
        raise LoteError(422, "El costo unitario no puede ser negativo")
    if not numero_lote or not numero_lote.strip():
        raise LoteError(422, "El número de lote es obligatorio")

    inv = await _cargar_inventario(db, empresa_id, inventario_id)
    stock_ant = Decimal(str(inv["cantidad_actual"]))
    costo_ant = Decimal(str(inv["costo_unitario"]))

    # Cálculo CPP. Si el stock anterior era 0, el costo nuevo arranca igual al ingreso.
    nuevo_stock = stock_ant + cantidad
    if stock_ant == 0:
        cpp_nuevo = costo_unitario
    else:
        cpp_nuevo = (stock_ant * costo_ant + cantidad * costo_unitario) / nuevo_stock
    cpp_nuevo = cpp_nuevo.quantize(Decimal("0.01"))

    # 1) Insert lote
    lote = (await db.execute(
        text("""
            INSERT INTO inventario_lotes (
                empresa_id, inventario_id, numero_lote, cantidad, cantidad_inicial,
                costo_unitario, fecha_ingreso, fecha_vencimiento,
                proveedor_id, comprobante_id, notas
            ) VALUES (
                :eid, :iid, :nl, :cant, :cant, :cu, COALESCE(:fi, CURRENT_DATE),
                :fv, :pid, :cid, :notas
            )
            RETURNING id, numero_lote, cantidad, costo_unitario,
                      fecha_ingreso, fecha_vencimiento
        """),
        {
            "eid": empresa_id, "iid": inventario_id, "nl": numero_lote.strip(),
            "cant": cantidad, "cu": costo_unitario,
            "fi": fecha_ingreso, "fv": fecha_vencimiento,
            "pid": proveedor_id, "cid": comprobante_id, "notas": notas,
        },
    )).mappings().first()

    # 2) Actualizar inventario (stock + CPP)
    await db.execute(
        text("""
            UPDATE inventario
               SET cantidad_actual = :stock,
                   costo_unitario  = :cpp
             WHERE id = :id AND empresa_id = :eid
        """),
        {"stock": nuevo_stock, "cpp": cpp_nuevo, "id": inventario_id, "eid": empresa_id},
    )

    # 3) Registrar kardex
    await db.execute(
        text("""
            INSERT INTO inventario_movimientos (
                empresa_id, inventario_id, lote_id, tipo, cantidad,
                costo_unitario, cpp_resultante, fecha, comprobante_id, usuario_id, notas
            ) VALUES (
                :eid, :iid, :lid, 'ingreso', :cant,
                :cu, :cpp, COALESCE(:fi, CURRENT_DATE), :cid, :uid, :notas
            )
        """),
        {
            "eid": empresa_id, "iid": inventario_id, "lid": str(lote["id"]),
            "cant": cantidad, "cu": costo_unitario, "cpp": cpp_nuevo,
            "fi": fecha_ingreso, "cid": comprobante_id, "uid": usuario_id, "notas": notas,
        },
    )

    return {
        "lote_id": str(lote["id"]),
        "numero_lote": lote["numero_lote"],
        "cantidad": float(lote["cantidad"]),
        "costo_unitario": float(lote["costo_unitario"]),
        "fecha_ingreso": lote["fecha_ingreso"].isoformat(),
        "fecha_vencimiento": lote["fecha_vencimiento"].isoformat() if lote["fecha_vencimiento"] else None,
        "cpp_resultante": float(cpp_nuevo),
        "stock_resultante": float(nuevo_stock),
    }


# ── Consumir FEFO (salida) ───────────────────────────────────────────────────

async def consumir_fefo(
    db: AsyncSession,
    *,
    empresa_id: str,
    inventario_id: str,
    cantidad: Decimal,
    comprobante_id: str | None = None,
    usuario_id: str | None = None,
    notas: str | None = None,
    fecha: date | None = None,
) -> dict:
    """Descuenta `cantidad` del stock siguiendo FEFO.

    Si la cantidad pedida es mayor al stock total, lanza LoteError.
    Registra un movimiento de kardex por cada lote tocado.

    Devuelve la lista de lotes consumidos + total descontado.
    """
    if cantidad <= 0:
        raise LoteError(422, "La cantidad debe ser mayor que cero")

    inv = await _cargar_inventario(db, empresa_id, inventario_id)
    stock_ant = Decimal(str(inv["cantidad_actual"]))
    if cantidad > stock_ant:
        raise LoteError(
            409,
            f"Stock insuficiente: pedido {cantidad}, disponible {stock_ant}",
        )

    # Traer lotes con stock > 0 en orden FEFO
    lotes = (await db.execute(
        text("""
            SELECT id, numero_lote, cantidad, costo_unitario, fecha_vencimiento
            FROM inventario_lotes
            WHERE empresa_id = :eid AND inventario_id = :iid AND cantidad > 0
            ORDER BY fecha_vencimiento NULLS LAST, fecha_ingreso ASC
            FOR UPDATE
        """),
        {"eid": empresa_id, "iid": inventario_id},
    )).mappings().all()

    consumidos: list[dict] = []
    restante = cantidad
    cpp_actual = Decimal(str(inv["costo_unitario"]))

    for lote in lotes:
        if restante <= 0:
            break
        cant_lote = Decimal(str(lote["cantidad"]))
        a_consumir = min(cant_lote, restante)
        nueva_cant = cant_lote - a_consumir

        await db.execute(
            text("UPDATE inventario_lotes SET cantidad = :c WHERE id = :id"),
            {"c": nueva_cant, "id": str(lote["id"])},
        )
        await db.execute(
            text("""
                INSERT INTO inventario_movimientos (
                    empresa_id, inventario_id, lote_id, tipo, cantidad,
                    costo_unitario, cpp_resultante, fecha, comprobante_id, usuario_id, notas
                ) VALUES (
                    :eid, :iid, :lid, 'salida', :cant,
                    :cu, :cpp, COALESCE(:fecha, CURRENT_DATE), :cid, :uid, :notas
                )
            """),
            {
                "eid": empresa_id, "iid": inventario_id, "lid": str(lote["id"]),
                "cant": a_consumir, "cu": lote["costo_unitario"], "cpp": cpp_actual,
                "fecha": fecha, "cid": comprobante_id, "uid": usuario_id, "notas": notas,
            },
        )
        consumidos.append({
            "lote_id": str(lote["id"]),
            "numero_lote": lote["numero_lote"],
            "cantidad": float(a_consumir),
            "costo_unitario": float(lote["costo_unitario"]),
            "fecha_vencimiento": lote["fecha_vencimiento"].isoformat() if lote["fecha_vencimiento"] else None,
        })
        restante -= a_consumir

    # Actualizar stock en inventario (CPP NO cambia en salidas)
    nuevo_stock = stock_ant - cantidad
    await db.execute(
        text("UPDATE inventario SET cantidad_actual = :s WHERE id = :id AND empresa_id = :eid"),
        {"s": nuevo_stock, "id": inventario_id, "eid": empresa_id},
    )

    return {
        "cantidad_total": float(cantidad),
        "stock_resultante": float(nuevo_stock),
        "lotes_consumidos": consumidos,
    }


# ── Próximos vencimientos ────────────────────────────────────────────────────

async def proximos_vencimientos(
    db: AsyncSession,
    *,
    empresa_id: str,
    dias: int | None = None,
) -> list[dict]:
    """Devuelve lotes que vencen en los próximos N días (o ya vencidos).

    Si `dias` viene None, se toma de `empresas.dias_alerta_vencimiento`.
    Ordenado por fecha_vencimiento ASC (los más urgentes primero).
    """
    params = {"eid": empresa_id}
    if dias is None:
        # Leer default de la empresa
        params["dias"] = (await db.execute(
            text("SELECT dias_alerta_vencimiento FROM empresas WHERE id = :eid"),
            {"eid": empresa_id},
        )).scalar() or 30
    else:
        params["dias"] = int(dias)

    rows = (await db.execute(
        text("""
            SELECT
                l.id              AS lote_id,
                l.numero_lote,
                l.cantidad,
                l.costo_unitario,
                l.fecha_ingreso,
                l.fecha_vencimiento,
                (l.fecha_vencimiento - CURRENT_DATE)::int AS dias_restantes,
                i.id              AS inventario_id,
                i.codigo          AS inventario_codigo,
                i.descripcion     AS inventario_descripcion,
                i.unidad_medida
            FROM inventario_lotes l
            JOIN inventario i ON i.id = l.inventario_id
            WHERE l.empresa_id = :eid
              AND l.cantidad > 0
              AND l.fecha_vencimiento IS NOT NULL
              AND l.fecha_vencimiento <= CURRENT_DATE + (:dias || ' days')::interval
            ORDER BY l.fecha_vencimiento ASC
        """),
        params,
    )).mappings().all()

    return [
        {
            "lote_id": str(r["lote_id"]),
            "numero_lote": r["numero_lote"],
            "cantidad": float(r["cantidad"]),
            "costo_unitario": float(r["costo_unitario"]),
            "valor_lote": float(Decimal(str(r["cantidad"])) * Decimal(str(r["costo_unitario"]))),
            "fecha_ingreso": r["fecha_ingreso"].isoformat() if r["fecha_ingreso"] else None,
            "fecha_vencimiento": r["fecha_vencimiento"].isoformat(),
            "dias_restantes": int(r["dias_restantes"]),
            "vencido": int(r["dias_restantes"]) < 0,
            "inventario_id": str(r["inventario_id"]),
            "inventario_codigo": r["inventario_codigo"],
            "inventario_descripcion": r["inventario_descripcion"],
            "unidad_medida": r["unidad_medida"],
        }
        for r in rows
    ]


# ── Listar lotes de un item ──────────────────────────────────────────────────

async def listar_lotes_item(
    db: AsyncSession,
    *,
    empresa_id: str,
    inventario_id: str,
    incluir_agotados: bool = False,
) -> list[dict]:
    cond = "" if incluir_agotados else "AND l.cantidad > 0"
    rows = (await db.execute(
        text(f"""
            SELECT
                l.id, l.numero_lote, l.cantidad, l.cantidad_inicial,
                l.costo_unitario, l.fecha_ingreso, l.fecha_vencimiento,
                l.proveedor_id, p.nombre AS proveedor_nombre,
                l.comprobante_id, l.notas, l.fecha_creacion
            FROM inventario_lotes l
            LEFT JOIN proveedores p ON p.id = l.proveedor_id
            WHERE l.empresa_id = :eid AND l.inventario_id = :iid
            {cond}
            ORDER BY l.fecha_vencimiento NULLS LAST, l.fecha_ingreso DESC
        """),
        {"eid": empresa_id, "iid": inventario_id},
    )).mappings().all()
    return [
        {
            "id": str(r["id"]),
            "numero_lote": r["numero_lote"],
            "cantidad": float(r["cantidad"]),
            "cantidad_inicial": float(r["cantidad_inicial"]),
            "costo_unitario": float(r["costo_unitario"]),
            "fecha_ingreso": r["fecha_ingreso"].isoformat() if r["fecha_ingreso"] else None,
            "fecha_vencimiento": r["fecha_vencimiento"].isoformat() if r["fecha_vencimiento"] else None,
            "proveedor_id": str(r["proveedor_id"]) if r["proveedor_id"] else None,
            "proveedor_nombre": r["proveedor_nombre"],
            "comprobante_id": str(r["comprobante_id"]) if r["comprobante_id"] else None,
            "notas": r["notas"],
            "fecha_creacion": r["fecha_creacion"].isoformat() if r["fecha_creacion"] else None,
        }
        for r in rows
    ]


# ── Listar todos los lotes (con paginación liviana) ──────────────────────────

async def listar_todos_los_lotes(
    db: AsyncSession,
    *,
    empresa_id: str,
    solo_con_vencimiento: bool = False,
    limit: int = 200,
) -> list[dict]:
    cond_venc = "AND l.fecha_vencimiento IS NOT NULL" if solo_con_vencimiento else ""
    rows = (await db.execute(
        text(f"""
            SELECT
                l.id, l.numero_lote, l.cantidad, l.cantidad_inicial,
                l.costo_unitario, l.fecha_ingreso, l.fecha_vencimiento,
                i.id AS inventario_id, i.codigo, i.descripcion, i.unidad_medida,
                p.nombre AS proveedor_nombre
            FROM inventario_lotes l
            JOIN inventario i ON i.id = l.inventario_id
            LEFT JOIN proveedores p ON p.id = l.proveedor_id
            WHERE l.empresa_id = :eid AND l.cantidad > 0
            {cond_venc}
            ORDER BY l.fecha_vencimiento NULLS LAST, i.descripcion
            LIMIT :limit
        """),
        {"eid": empresa_id, "limit": limit},
    )).mappings().all()
    return [
        {
            "id": str(r["id"]),
            "numero_lote": r["numero_lote"],
            "cantidad": float(r["cantidad"]),
            "cantidad_inicial": float(r["cantidad_inicial"]),
            "costo_unitario": float(r["costo_unitario"]),
            "fecha_ingreso": r["fecha_ingreso"].isoformat() if r["fecha_ingreso"] else None,
            "fecha_vencimiento": r["fecha_vencimiento"].isoformat() if r["fecha_vencimiento"] else None,
            "inventario_id": str(r["inventario_id"]),
            "inventario_codigo": r["codigo"],
            "inventario_descripcion": r["descripcion"],
            "unidad_medida": r["unidad_medida"],
            "proveedor_nombre": r["proveedor_nombre"],
        }
        for r in rows
    ]
