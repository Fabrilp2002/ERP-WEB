"""
Router de Recetas (Bill of Materials / BOM)
==========================================

Permite definir la "receta" de un producto terminado: que insumos lo componen
y en que cantidad. Habilita:
  - Calculo de costo real por producto
  - Margen automatico (precio_venta - costo_unitario)
  - Planeacion de produccion: "puedo producir N unidades"
  - Identificacion del insumo cuello de botella
  - Prediccion de quiebre de stock a tasa de venta actual
"""
from decimal import Decimal
from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from ..core.database import get_db
from ..core.security import get_current_user, require_escritura
from ..models.schemas_bom import (
    RecetaCreate, RecetaUpdate, RecetaRead, RecetaItemRead,
    CapacidadProduccion, LoteCreate, LoteRead,
)
from ..services.audit import registrar as audit


router = APIRouter(prefix="/recetas", tags=["Recetas (BOM)"])


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_receta_completa(db: AsyncSession, receta_id: str, empresa_id: str) -> Optional[dict]:
    """Trae la receta enriquecida (con items, costos calculados, etc.)."""
    cab = (await db.execute(
        text("""
            SELECT
                r.id, r.empresa_id, r.producto_id, r.nombre, r.version,
                r.rendimiento, r.unidad_rendimiento, r.activa, r.notas,
                r.fecha_creacion, r.fecha_modificacion,
                p.descripcion AS producto_nombre,
                p.codigo      AS producto_codigo,
                p.precio_venta AS producto_precio_venta,
                v.costo_total_receta,
                v.costo_unitario,
                v.cantidad_items
            FROM recetas r
            JOIN inventario p ON p.id = r.producto_id
            LEFT JOIN v_recetas_detalle v ON v.receta_id = r.id
            WHERE r.id = :rid AND r.empresa_id = :eid
        """),
        {"rid": receta_id, "eid": empresa_id},
    )).mappings().first()

    if not cab:
        return None

    items = (await db.execute(
        text("""
            SELECT
                ri.id, ri.insumo_id, ri.cantidad, ri.unidad_medida,
                ri.orden, ri.es_critico, ri.notas,
                i.descripcion AS insumo_nombre,
                i.codigo      AS insumo_codigo,
                i.cantidad_actual AS insumo_stock_actual,
                i.costo_unitario  AS insumo_costo_unitario,
                (ri.cantidad * i.costo_unitario) AS subtotal_costo
            FROM receta_items ri
            JOIN inventario i ON i.id = ri.insumo_id
            WHERE ri.receta_id = :rid
            ORDER BY ri.orden, ri.id
        """),
        {"rid": receta_id},
    )).mappings().all()

    out = dict(cab)
    out["items"] = list(items)

    # Calcular margen si hay precio de venta
    pv = out.get("producto_precio_venta")
    cu = out.get("costo_unitario")
    if pv is not None and cu is not None and Decimal(str(pv)) > 0:
        out["margen_pct"] = (Decimal(str(pv)) - Decimal(str(cu))) / Decimal(str(pv)) * 100
    else:
        out["margen_pct"] = None

    return out


# ── List & Get ────────────────────────────────────────────────────────────────

@router.get("/", response_model=list[RecetaRead], summary="Listar recetas")
async def listar_recetas(
    activas: Optional[bool] = Query(None, description="Filtrar por estado activo"),
    producto_id: Optional[UUID] = Query(None, description="Recetas de un producto especifico"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    empresa_id = current_user["empresa_id"]
    filtros = []
    params = {"eid": empresa_id}

    if activas is not None:
        filtros.append("r.activa = :activa")
        params["activa"] = activas
    if producto_id:
        filtros.append("r.producto_id = :pid")
        params["pid"] = str(producto_id)

    where_extra = (" AND " + " AND ".join(filtros)) if filtros else ""

    rows = (await db.execute(
        text(f"""
            SELECT
                r.id, r.empresa_id, r.producto_id, r.nombre, r.version,
                r.rendimiento, r.unidad_rendimiento, r.activa, r.notas,
                r.fecha_creacion, r.fecha_modificacion,
                p.descripcion AS producto_nombre,
                p.codigo      AS producto_codigo,
                p.precio_venta AS producto_precio_venta,
                v.costo_total_receta,
                v.costo_unitario,
                v.cantidad_items
            FROM recetas r
            JOIN inventario p ON p.id = r.producto_id
            LEFT JOIN v_recetas_detalle v ON v.receta_id = r.id
            WHERE r.empresa_id = :eid {where_extra}
            ORDER BY r.nombre
        """),
        params,
    )).mappings().all()

    result = []
    for r in rows:
        rec = dict(r)
        pv = rec.get("producto_precio_venta")
        cu = rec.get("costo_unitario")
        if pv is not None and cu is not None and Decimal(str(pv)) > 0:
            rec["margen_pct"] = (Decimal(str(pv)) - Decimal(str(cu))) / Decimal(str(pv)) * 100
        rec["items"] = []
        result.append(rec)
    return result


@router.get("/{receta_id}", response_model=RecetaRead, summary="Obtener receta con items")
async def obtener_receta(
    receta_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    rec = await _get_receta_completa(db, str(receta_id), current_user["empresa_id"])
    if not rec:
        raise HTTPException(status_code=404, detail="Receta no encontrada")
    return rec


# ── Create ────────────────────────────────────────────────────────────────────

@router.post("/", response_model=RecetaRead, status_code=status.HTTP_201_CREATED,
             summary="Crear receta con sus items")
async def crear_receta(
    data: RecetaCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_escritura),
):
    empresa_id = current_user["empresa_id"]

    # 1. Verificar que el producto existe y es terminado (o convertirlo)
    prod = (await db.execute(
        text("""
            SELECT id, es_producto_terminado
            FROM inventario
            WHERE id = :id AND empresa_id = :eid
        """),
        {"id": str(data.producto_id), "eid": empresa_id},
    )).mappings().first()

    if not prod:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    # Marcarlo como producto terminado si no lo es
    if not prod["es_producto_terminado"]:
        await db.execute(
            text("""
                UPDATE inventario
                SET es_producto_terminado = TRUE
                WHERE id = :id
            """),
            {"id": str(data.producto_id)},
        )

    # 2. Si esta receta es activa, desactivar otras activas del mismo producto
    if data.activa:
        await db.execute(
            text("""
                UPDATE recetas
                SET activa = FALSE
                WHERE producto_id = :pid AND empresa_id = :eid AND activa = TRUE
            """),
            {"pid": str(data.producto_id), "eid": empresa_id},
        )

    # 3. Crear la cabecera
    cab = (await db.execute(
        text("""
            INSERT INTO recetas
                (empresa_id, producto_id, nombre, version, rendimiento,
                 unidad_rendimiento, activa, notas, usuario_creacion_id)
            VALUES
                (:eid, :pid, :nombre, :version, :rend,
                 :ur, :activa, :notas, :uid)
            RETURNING id
        """),
        {
            "eid": empresa_id,
            "pid": str(data.producto_id),
            "nombre": data.nombre,
            "version": data.version,
            "rend": data.rendimiento,
            "ur": data.unidad_rendimiento,
            "activa": data.activa,
            "notas": data.notas,
            "uid": current_user.get("usuario_id"),
        },
    )).mappings().first()

    receta_id = cab["id"]

    # 4. Insertar items
    for idx, item in enumerate(data.items):
        await db.execute(
            text("""
                INSERT INTO receta_items
                    (receta_id, insumo_id, cantidad, unidad_medida,
                     orden, es_critico, notas)
                VALUES
                    (:rid, :iid, :cant, :um, :orden, :crit, :notas)
            """),
            {
                "rid": str(receta_id),
                "iid": str(item.insumo_id),
                "cant": item.cantidad,
                "um": item.unidad_medida,
                "orden": item.orden if item.orden else idx,
                "crit": item.es_critico,
                "notas": item.notas,
            },
        )

    await audit(db, usuario=current_user, accion="INSERT", tabla="recetas",
                registro_id=str(receta_id),
                datos_nuevos={"producto_id": str(data.producto_id),
                              "items": len(data.items)})
    await db.commit()

    return await _get_receta_completa(db, str(receta_id), empresa_id)


# ── Update ────────────────────────────────────────────────────────────────────

@router.put("/{receta_id}", response_model=RecetaRead, summary="Actualizar receta")
async def actualizar_receta(
    receta_id: UUID,
    data: RecetaUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_escritura),
):
    empresa_id = current_user["empresa_id"]

    exists = (await db.execute(
        text("SELECT id FROM recetas WHERE id = :rid AND empresa_id = :eid"),
        {"rid": str(receta_id), "eid": empresa_id},
    )).first()
    if not exists:
        raise HTTPException(status_code=404, detail="Receta no encontrada")

    # Update fields conditionally
    fields = []
    params = {"rid": str(receta_id), "eid": empresa_id}
    if data.nombre is not None:        fields.append("nombre = :nombre");        params["nombre"] = data.nombre
    if data.version is not None:       fields.append("version = :version");      params["version"] = data.version
    if data.rendimiento is not None:   fields.append("rendimiento = :rend");     params["rend"] = data.rendimiento
    if data.unidad_rendimiento is not None: fields.append("unidad_rendimiento = :ur"); params["ur"] = data.unidad_rendimiento
    if data.activa is not None:        fields.append("activa = :activa");        params["activa"] = data.activa
    if data.notas is not None:         fields.append("notas = :notas");          params["notas"] = data.notas

    if fields:
        fields.append("fecha_modificacion = NOW()")
        await db.execute(
            text(f"UPDATE recetas SET {', '.join(fields)} WHERE id = :rid AND empresa_id = :eid"),
            params,
        )

    # Si se pasan items, reemplazar todos
    if data.items is not None:
        await db.execute(
            text("DELETE FROM receta_items WHERE receta_id = :rid"),
            {"rid": str(receta_id)},
        )
        for idx, item in enumerate(data.items):
            await db.execute(
                text("""
                    INSERT INTO receta_items
                        (receta_id, insumo_id, cantidad, unidad_medida,
                         orden, es_critico, notas)
                    VALUES
                        (:rid, :iid, :cant, :um, :orden, :crit, :notas)
                """),
                {
                    "rid": str(receta_id),
                    "iid": str(item.insumo_id),
                    "cant": item.cantidad,
                    "um": item.unidad_medida,
                    "orden": item.orden if item.orden else idx,
                    "crit": item.es_critico,
                    "notas": item.notas,
                },
            )

    await audit(db, usuario=current_user, accion="UPDATE", tabla="recetas",
                registro_id=str(receta_id),
                datos_nuevos=data.model_dump(exclude_unset=True))
    await db.commit()

    return await _get_receta_completa(db, str(receta_id), empresa_id)


# ── Delete (soft) ─────────────────────────────────────────────────────────────

@router.delete("/{receta_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Desactivar receta (soft delete)")
async def eliminar_receta(
    receta_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_escritura),
):
    empresa_id = current_user["empresa_id"]
    result = await db.execute(
        text("""
            UPDATE recetas
            SET activa = FALSE, fecha_modificacion = NOW()
            WHERE id = :rid AND empresa_id = :eid
            RETURNING id
        """),
        {"rid": str(receta_id), "eid": empresa_id},
    )
    if not result.first():
        raise HTTPException(status_code=404, detail="Receta no encontrada")
    await audit(db, usuario=current_user, accion="UPDATE", tabla="recetas",
                registro_id=str(receta_id), datos_nuevos={"activa": False})
    await db.commit()


# ── Capacidad de Produccion ───────────────────────────────────────────────────

@router.get("/{receta_id}/capacidad", response_model=CapacidadProduccion,
            summary="¿Cuanto puedo producir con stock actual?")
async def capacidad_produccion(
    receta_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Calcula cuantos batches y unidades se pueden producir con el stock actual
    de insumos. Identifica el insumo "cuello de botella".
    """
    empresa_id = current_user["empresa_id"]

    # Receta + producto
    rec = (await db.execute(
        text("""
            SELECT r.id, r.producto_id, r.rendimiento, p.descripcion AS producto_nombre
            FROM recetas r
            JOIN inventario p ON p.id = r.producto_id
            WHERE r.id = :rid AND r.empresa_id = :eid AND r.activa = TRUE
        """),
        {"rid": str(receta_id), "eid": empresa_id},
    )).mappings().first()

    if not rec:
        raise HTTPException(status_code=404, detail="Receta no encontrada o no activa")

    # Items + stock
    items = (await db.execute(
        text("""
            SELECT
                ri.insumo_id,
                i.descripcion AS insumo_nombre,
                i.codigo,
                i.unidad_medida,
                ri.cantidad   AS cantidad_requerida,
                i.cantidad_actual AS stock_actual,
                CASE WHEN ri.cantidad > 0
                    THEN FLOOR(i.cantidad_actual / ri.cantidad)
                    ELSE 0
                END AS batches_posibles
            FROM receta_items ri
            JOIN inventario i ON i.id = ri.insumo_id
            WHERE ri.receta_id = :rid
            ORDER BY batches_posibles ASC, i.descripcion
        """),
        {"rid": str(receta_id)},
    )).mappings().all()

    if not items:
        return CapacidadProduccion(
            receta_id=receta_id,
            producto_id=rec["producto_id"],
            producto_nombre=rec["producto_nombre"],
            batches_posibles=0,
            unidades_posibles=Decimal("0"),
            items_status=[],
        )

    batches_min = min(int(it["batches_posibles"]) for it in items)
    unidades = Decimal(batches_min) * Decimal(str(rec["rendimiento"]))
    insumo_limitante = items[0]["insumo_nombre"]  # menor batches_posibles

    items_status = [
        {
            "insumo_nombre": it["insumo_nombre"],
            "codigo": it["codigo"],
            "unidad_medida": it["unidad_medida"],
            "stock_actual": float(it["stock_actual"] or 0),
            "cantidad_requerida": float(it["cantidad_requerida"] or 0),
            "batches_posibles": int(it["batches_posibles"] or 0),
            "es_limitante": it["insumo_nombre"] == insumo_limitante,
        }
        for it in items
    ]

    return CapacidadProduccion(
        receta_id=receta_id,
        producto_id=rec["producto_id"],
        producto_nombre=rec["producto_nombre"],
        batches_posibles=batches_min,
        unidades_posibles=unidades,
        insumo_limitante=insumo_limitante,
        items_status=items_status,
    )


# ── Lotes de Produccion ───────────────────────────────────────────────────────

@router.post("/lotes", response_model=LoteRead, status_code=status.HTTP_201_CREATED,
             summary="Planificar un lote de produccion")
async def crear_lote(
    data: LoteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_escritura),
):
    empresa_id = current_user["empresa_id"]

    # Verificar receta
    rec = (await db.execute(
        text("""
            SELECT r.id, r.producto_id
            FROM recetas r
            WHERE r.id = :rid AND r.empresa_id = :eid
        """),
        {"rid": str(data.receta_id), "eid": empresa_id},
    )).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Receta no encontrada")

    row = (await db.execute(
        text("""
            INSERT INTO lotes_produccion
                (empresa_id, receta_id, numero_lote, cantidad_planificada,
                 fecha_planificada, fecha_vencimiento, notas, usuario_id)
            VALUES
                (:eid, :rid, :num, :cant, :fp, :fv, :notas, :uid)
            RETURNING id
        """),
        {
            "eid": empresa_id,
            "rid": str(data.receta_id),
            "num": data.numero_lote,
            "cant": data.cantidad_planificada,
            "fp": data.fecha_planificada,
            "fv": data.fecha_vencimiento,
            "notas": data.notas,
            "uid": current_user.get("usuario_id"),
        },
    )).mappings().first()

    await audit(db, usuario=current_user, accion="INSERT", tabla="lotes_produccion",
                registro_id=str(row["id"]), datos_nuevos=data.model_dump())
    await db.commit()

    full = (await db.execute(
        text("""
            SELECT l.*, r.nombre AS receta_nombre, p.descripcion AS producto_nombre
            FROM lotes_produccion l
            JOIN recetas r ON r.id = l.receta_id
            JOIN inventario p ON p.id = r.producto_id
            WHERE l.id = :id
        """),
        {"id": str(row["id"])},
    )).mappings().first()
    return dict(full)


@router.get("/lotes/listar", response_model=list[LoteRead], summary="Listar lotes")
async def listar_lotes(
    estado: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    empresa_id = current_user["empresa_id"]
    extra = "AND l.estado = :estado" if estado else ""
    params = {"eid": empresa_id}
    if estado:
        params["estado"] = estado

    rows = (await db.execute(
        text(f"""
            SELECT l.*, r.nombre AS receta_nombre, p.descripcion AS producto_nombre
            FROM lotes_produccion l
            JOIN recetas r ON r.id = l.receta_id
            JOIN inventario p ON p.id = r.producto_id
            WHERE l.empresa_id = :eid {extra}
            ORDER BY l.fecha_planificada DESC
        """),
        params,
    )).mappings().all()
    return [dict(r) for r in rows]
