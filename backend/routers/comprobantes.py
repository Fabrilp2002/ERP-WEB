from decimal import Decimal
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from ..core.database import get_db
from ..core.security import get_current_user, require_escritura
from ..models.schemas import ComprobanteCreate, ComprobanteRead, ComprobanteUpdate, TipoComprobanteRead
from ..services.audit import registrar as audit
from ..services.contabilidad import (
    asiento_comprobante_venta,
    asiento_comprobante_compra,
    revertir_asiento_comprobante,
)
from .cierre_contable import verificar_periodo_abierto

router = APIRouter(prefix="/comprobantes", tags=["Comprobantes"])

# Detección lazy de la extensión `unaccent`. Si no está habilitada en la DB,
# el filtro `buscar` cae en LOWER simple (sin sensibilidad a tildes).
# El check corre una sola vez por proceso y cachea el resultado.
_unaccent_disponible: bool | None = None


async def _detectar_unaccent(db: AsyncSession) -> bool:
    """Devuelve True si la extensión `unaccent` está instalada en la DB.

    Consulta `pg_extension` (catálogo del sistema) en vez de intentar llamar
    a `unaccent()`. La query siempre tiene éxito — no aborta la transacción
    aunque la extensión no exista. Resultado cacheado a nivel módulo.
    """
    global _unaccent_disponible
    if _unaccent_disponible is not None:
        return _unaccent_disponible
    try:
        result = await db.execute(
            text("SELECT 1 FROM pg_extension WHERE extname = 'unaccent' LIMIT 1")
        )
        _unaccent_disponible = result.scalar() is not None
    except Exception:
        # Cualquier error es defensivo: caemos en lower() simple.
        _unaccent_disponible = False
    return _unaccent_disponible


ESTADO_PAGO_SQL = """
CASE
  WHEN c.estado_validacion = 'anulado' THEN 'anulado'
  WHEN c.estado_validacion = 'rechazado' THEN 'rechazado'
  WHEN c.monto_total <= 0 THEN 'no_aplica'
  WHEN c.saldo_pendiente >= c.monto_total THEN 'no_pagado'
  WHEN c.saldo_pendiente <= 0 THEN 'pagado'
  ELSE 'pago_parcial'
END
"""


async def _tipo_movimiento_nota(
    db: AsyncSession,
    empresa_id: str,
    tipo_id: UUID,
) -> int:
    """Devuelve -1 para NC, +1 para ND y 0 para comprobantes normales."""
    nombre = (await db.execute(
        text("""
            SELECT LOWER(nombre) FROM tipos_comprobante
            WHERE id = :id AND empresa_id = :eid
        """),
        {"id": str(tipo_id), "eid": empresa_id},
    )).scalar()
    if not nombre:
        raise HTTPException(status_code=422, detail="Tipo de comprobante invalido")
    if "credito" in nombre or "crédito" in nombre:
        return -1
    if "debito" in nombre or "débito" in nombre:
        return 1
    return 0


@router.get("/tipos", response_model=list[TipoComprobanteRead], summary="Listar tipos de comprobante")
async def listar_tipos_comprobante(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    result = await db.execute(
        text("""
            SELECT id, empresa_id, nombre
            FROM tipos_comprobante
            WHERE empresa_id = :empresa_id
            ORDER BY nombre
        """),
        {"empresa_id": current_user["empresa_id"]},
    )
    return result.mappings().all()


# Orderings permitidos (whitelist anti SQL-injection). Cada clave mapea a una
# expresión SQL segura usada en ORDER BY.
_ORDER_BY_MAP = {
    "fecha_desc":       "c.fecha_emision DESC, c.fecha_creacion DESC",
    "fecha_asc":        "c.fecha_emision ASC, c.fecha_creacion ASC",
    "monto_desc":       "c.monto_total DESC",
    "monto_asc":        "c.monto_total ASC",
    "saldo_desc":       "c.saldo_pendiente DESC",
    "saldo_asc":        "c.saldo_pendiente ASC",
    "numero_asc":       "c.numero_comprobante ASC",
    "numero_desc":      "c.numero_comprobante DESC",
    "contraparte_asc":  "COALESCE(cl.nombre, pr.nombre, '') ASC",
    "contraparte_desc": "COALESCE(cl.nombre, pr.nombre, '') DESC",
}


@router.get("/", summary="Listar comprobantes")
async def listar_comprobantes(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=1000),
    estado: str = Query(None),
    estado_pago: str = Query(None, pattern="^(pagado|no_pagado|pago_parcial|anulado|rechazado|no_aplica)$"),
    tipo: str = Query(None, pattern="^(venta|compra)$"),
    cliente_id: UUID | None = Query(None),
    proveedor_id: UUID | None = Query(None),
    buscar: str | None = Query(None, description="Texto libre — matchea número de comprobante O nombre de cliente/proveedor (ILIKE)"),
    order_by: str = Query("fecha_desc", description="Ordenamiento: fecha_desc, fecha_asc, monto_desc, monto_asc, saldo_desc, saldo_asc, numero_asc, numero_desc, contraparte_asc, contraparte_desc"),
    with_total: bool = Query(False, description="Si True, devuelve {items, total, page, page_size} con el total no paginado"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),  # viewer puede ver
):
    """Listado de comprobantes con paginación, filtros y ordenamiento.

    Por compatibilidad, por default devuelve `list[ComprobanteRead]` (shape viejo).
    Si se pasa `with_total=true`, devuelve `{items, total, page, page_size}` —
    necesario para mostrar paginación "Página N de M" en la UI.

    Filtros (v7.2 — UI consolidada):
    - `tipo`: 'venta' o 'compra'
    - `cliente_id` / `proveedor_id`: UUID, sólo facturas de ese contacto
    - `buscar`: texto libre que matchea número de comprobante o nombre de
      cliente/proveedor (case-insensitive, parcial)
    - `order_by`: una de las claves de _ORDER_BY_MAP
    """
    empresa_id = current_user["empresa_id"]
    offset = (page - 1) * page_size

    # Mapeo seguro de order_by — si viene un valor no permitido, se cae al default.
    order_clause = _ORDER_BY_MAP.get(order_by, _ORDER_BY_MAP["fecha_desc"])

    filtros = []
    if estado:
        filtros.append("AND c.estado_validacion = :estado")
    if estado_pago:
        filtros.append(f"AND ({ESTADO_PAGO_SQL}) = :estado_pago")
    if tipo == "venta":
        filtros.append("AND c.cliente_id IS NOT NULL")
    elif tipo == "compra":
        filtros.append("AND c.proveedor_id IS NOT NULL")
    if cliente_id:
        filtros.append("AND c.cliente_id = :cliente_id")
    if proveedor_id:
        filtros.append("AND c.proveedor_id = :proveedor_id")
    if buscar and buscar.strip():
        # Match en número del comprobante O nombre del cliente O nombre del proveedor.
        # Si la extensión `unaccent` está habilitada en la DB, usamos eso para
        # que "insua" matchee "ÍNSUA". Si no, caemos en LOWER simple — el
        # buscador sigue funcionando, pero no es insensible a tildes.
        if await _detectar_unaccent(db):
            filtros.append(
                "AND ("
                "unaccent(lower(c.numero_comprobante)) ILIKE unaccent(lower(:buscar))"
                " OR unaccent(lower(coalesce(cl.nombre, ''))) ILIKE unaccent(lower(:buscar))"
                " OR unaccent(lower(coalesce(pr.nombre, ''))) ILIKE unaccent(lower(:buscar))"
                ")"
            )
        else:
            filtros.append(
                "AND ("
                "lower(c.numero_comprobante) ILIKE lower(:buscar)"
                " OR lower(coalesce(cl.nombre, '')) ILIKE lower(:buscar)"
                " OR lower(coalesce(pr.nombre, '')) ILIKE lower(:buscar)"
                ")"
            )
    where_extra = " ".join(filtros)

    params: dict = {
        "empresa_id": empresa_id, "estado": estado, "estado_pago": estado_pago,
        "limit": page_size, "offset": offset,
    }
    if cliente_id:
        params["cliente_id"] = str(cliente_id)
    if proveedor_id:
        params["proveedor_id"] = str(proveedor_id)
    if buscar and buscar.strip():
        params["buscar"] = f"%{buscar.strip()}%"

    result = await db.execute(
        text(f"""
            SELECT c.id, c.empresa_id, c.tipo_id, c.comprobante_origen_id,
                   c.numero_comprobante, c.fecha_emision,
                   c.fecha_vencimiento, c.monto_total,
                   GREATEST(c.monto_total - c.saldo_pendiente, 0) AS monto_pagado,
                   c.saldo_pendiente, ({ESTADO_PAGO_SQL}) AS estado_pago, c.metodo_carga,
                   c.estado_validacion, c.condicion, c.medio_pago_contado, c.fecha_creacion,
                   c.cliente_id, c.proveedor_id, c.ruta_archivo, c.ubicacion_fisica,
                   c.notas,
                   COALESCE(cl.nombre, pr.nombre, '—')  AS contraparte,
                   CASE WHEN c.cliente_id IS NOT NULL THEN 'venta' ELSE 'compra' END AS tipo,
                   NULLIF(TRIM(COALESCE(u.nombre,'') || ' ' || COALESCE(u.apellido,'')), '') AS cargado_por,
                   (SELECT d.descripcion FROM detalle_comprobantes d
                     WHERE d.comprobante_id = c.id ORDER BY d.subtotal DESC LIMIT 1) AS descripcion,
                   (SELECT COUNT(*) FROM detalle_comprobantes d
                     WHERE d.comprobante_id = c.id) AS cant_items
            FROM comprobantes c
            LEFT JOIN clientes cl    ON cl.id = c.cliente_id
            LEFT JOIN proveedores pr ON pr.id = c.proveedor_id
            LEFT JOIN usuarios u     ON u.id = c.usuario_carga_id
            WHERE c.empresa_id = :empresa_id
            {where_extra}
            ORDER BY {order_clause}
            LIMIT :limit OFFSET :offset
        """),
        params,
    )
    items = result.mappings().all()

    if not with_total:
        # Backward compat: la mayoría de consumidores (/movimientos, /timeline) usan el shape viejo
        return items

    # Conteo + sumas totales NO paginados para mostrar "Página N de M" y "suma G. X"
    # Necesita los mismos JOINs que la query principal porque `buscar` referencia
    # `cl.nombre` y `pr.nombre`.
    agregados = await db.execute(
        text(f"""
            SELECT
                COUNT(*)                              AS total,
                COALESCE(SUM(c.monto_total), 0)       AS suma_monto_total,
                COALESCE(SUM(c.saldo_pendiente), 0)   AS suma_saldo_pendiente
            FROM comprobantes c
            LEFT JOIN clientes cl    ON cl.id = c.cliente_id
            LEFT JOIN proveedores pr ON pr.id = c.proveedor_id
            WHERE c.empresa_id = :empresa_id
            {where_extra}
        """),
        params,
    )
    agg = dict(agregados.mappings().first() or {})
    return {
        "items": items,
        "total": int(agg.get("total") or 0),
        "suma_monto_total": float(agg.get("suma_monto_total") or 0),
        "suma_saldo_pendiente": float(agg.get("suma_saldo_pendiente") or 0),
        "page": page,
        "page_size": page_size,
    }


@router.get("/{comprobante_id}", response_model=ComprobanteRead,
            summary="Obtener comprobante con detalle")
async def obtener_comprobante(
    comprobante_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    empresa_id = current_user["empresa_id"]

    # Cabecera del comprobante (con joins para contraparte y tipo)
    result = await db.execute(
        text(f"""
            SELECT c.*,
                   GREATEST(c.monto_total - c.saldo_pendiente, 0) AS monto_pagado,
                   ({ESTADO_PAGO_SQL}) AS estado_pago,
                   COALESCE(cl.nombre, pr.nombre) AS contraparte,
                   CASE
                     WHEN c.cliente_id   IS NOT NULL THEN 'venta'
                     WHEN c.proveedor_id IS NOT NULL THEN 'compra'
                   END AS tipo
            FROM comprobantes c
            LEFT JOIN clientes    cl ON cl.id = c.cliente_id
            LEFT JOIN proveedores pr ON pr.id = c.proveedor_id
            WHERE c.id = :id AND c.empresa_id = :empresa_id
        """),
        {"id": str(comprobante_id), "empresa_id": empresa_id},
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Comprobante no encontrado")

    # Detalle de items (lista separada)
    det_rows = await db.execute(
        text("""
            SELECT id, descripcion, cantidad, precio_unitario, porcentaje_iva,
                   subtotal, iva_monto
            FROM detalle_comprobantes
            WHERE comprobante_id = :id
            ORDER BY descripcion
        """),
        {"id": str(comprobante_id)},
    )
    detalle = [dict(r) for r in det_rows.mappings().all()]

    notas_rows = await db.execute(
        text("""
            SELECT c.id, c.numero_comprobante, c.fecha_emision, c.monto_total,
                   c.estado_validacion, c.notas, tc.nombre AS tipo_nombre
            FROM comprobantes c
            LEFT JOIN tipos_comprobante tc ON tc.id = c.tipo_id
            WHERE c.comprobante_origen_id = :id
              AND c.empresa_id = :empresa_id
            ORDER BY c.fecha_emision DESC, c.fecha_creacion DESC
        """),
        {"id": str(comprobante_id), "empresa_id": empresa_id},
    )
    notas_vinculadas = [dict(r) for r in notas_rows.mappings().all()]

    # Mergear y devolver
    return {**dict(row), "detalle": detalle, "notas_vinculadas": notas_vinculadas}


@router.post("/", response_model=ComprobanteRead, status_code=status.HTTP_201_CREATED,
             summary="Registrar comprobante (factura externa)")
async def crear_comprobante(
    data: ComprobanteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_escritura),  # viewer bloqueado
):
    empresa_id = current_user["empresa_id"]
    usuario_id = current_user["sub"]
    tipo_movimiento = await _tipo_movimiento_nota(db, empresa_id, data.tipo_id)

    # Verificar período contable abierto
    await verificar_periodo_abierto(db, empresa_id, str(data.fecha_emision))

    # Validación: solo cliente O proveedor
    if data.cliente_id and data.proveedor_id:
        raise HTTPException(status_code=422,
                            detail="Un comprobante no puede tener cliente Y proveedor a la vez")
    if not data.cliente_id and not data.proveedor_id:
        raise HTTPException(status_code=422,
                            detail="El comprobante debe tener cliente o proveedor")
    if tipo_movimiento != 0 and not data.comprobante_origen_id:
        raise HTTPException(status_code=422, detail="Las notas deben vincularse a una factura origen")

    # Verificar comprobante origen si es NC/ND vinculada
    if data.comprobante_origen_id:
        origen = (await db.execute(
            text("""
                SELECT id, saldo_pendiente, cliente_id, proveedor_id
                FROM comprobantes WHERE id = :id AND empresa_id = :eid
            """),
            {"id": str(data.comprobante_origen_id), "eid": empresa_id},
        )).mappings().first()
        if not origen:
            raise HTTPException(status_code=404, detail="Comprobante origen no encontrado")
        if tipo_movimiento == 0:
            raise HTTPException(status_code=422, detail="El tipo debe ser Nota de Credito o Nota de Debito")
        if str(origen["cliente_id"] or "") != str(data.cliente_id or ""):
            raise HTTPException(status_code=422, detail="La nota debe conservar el mismo cliente de la factura origen")
        if str(origen["proveedor_id"] or "") != str(data.proveedor_id or ""):
            raise HTTPException(status_code=422, detail="La nota debe conservar el mismo proveedor de la factura origen")

    # Insertar comprobante
    result = await db.execute(
        text("""
            INSERT INTO comprobantes (
                empresa_id, tipo_id, numero_comprobante, fecha_emision, fecha_vencimiento,
                cliente_id, proveedor_id, monto_subtotal, monto_iva, monto_total,
                saldo_pendiente, metodo_carga, condicion, medio_pago_contado,
                ruta_archivo, notas, usuario_carga_id, comprobante_origen_id
            ) VALUES (
                :empresa_id, :tipo_id, :numero, :fecha_emision, :fecha_venc,
                :cliente_id, :proveedor_id, :subtotal, :iva, :total,
                :saldo_inicial, :metodo, :condicion, :medio_contado,
                :ruta, :notas, :usuario_id, :origen_id
            )
            RETURNING id, empresa_id, numero_comprobante, fecha_emision,
                      monto_total, saldo_pendiente, metodo_carga,
                      estado_validacion, fecha_creacion
        """),
        {
            "empresa_id": empresa_id,
            "tipo_id": str(data.tipo_id),
            "numero": data.numero_comprobante,
            "fecha_emision": data.fecha_emision,
            "fecha_venc": data.fecha_vencimiento,
            "cliente_id": str(data.cliente_id) if data.cliente_id else None,
            "proveedor_id": str(data.proveedor_id) if data.proveedor_id else None,
            "subtotal": data.monto_subtotal,
            "iva": data.monto_iva,
            "total": data.monto_total,
            "saldo_inicial": (
                Decimal("0")
                if data.comprobante_origen_id or data.condicion == "contado"
                else data.monto_total
            ),
            "condicion": data.condicion,
            "medio_contado": (data.medio_pago_contado or "efectivo") if data.condicion == "contado" else None,
            "metodo": data.metodo_carga,
            "ruta": data.ruta_archivo,
            "notas": data.notas,
            "usuario_id": usuario_id,
            "origen_id": str(data.comprobante_origen_id) if data.comprobante_origen_id else None,
        },
    )
    comprobante = result.mappings().first()

    # NC/ND vinculada: credito reduce saldo, debito aumenta saldo de la factura origen.
    if data.comprobante_origen_id:
        await db.execute(
            text("""
                UPDATE comprobantes
                SET saldo_pendiente = CASE
                        WHEN :movimiento < 0 THEN GREATEST(0, saldo_pendiente - :monto)
                        ELSE saldo_pendiente + :monto
                    END,
                    fecha_modificacion = NOW()
                WHERE id = :id AND empresa_id = :eid
            """),
            {
                "monto": data.monto_total,
                "movimiento": tipo_movimiento,
                "id": str(data.comprobante_origen_id),
                "eid": empresa_id,
            },
        )

    # Insertar líneas de detalle
    for item in data.detalle:
        subtotal = (item.cantidad * item.precio_unitario).quantize(Decimal("0.01"))
        if item.porcentaje_iva == Decimal("10"):
            iva_monto = (subtotal / Decimal("11")).quantize(Decimal("0.01"))
        elif item.porcentaje_iva == Decimal("5"):
            iva_monto = (subtotal / Decimal("21")).quantize(Decimal("0.01"))
        else:
            iva_monto = Decimal("0.00")
        await db.execute(
            text("""
                INSERT INTO detalle_comprobantes (
                    empresa_id, comprobante_id, inventario_id, descripcion,
                    cantidad, precio_unitario, porcentaje_iva, subtotal, iva_monto
                ) VALUES (
                    :empresa_id, :comprobante_id, :inv_id, :desc,
                    :cantidad, :precio, :iva_pct, :subtotal, :iva_monto
                )
            """),
            {
                "empresa_id": empresa_id,
                "comprobante_id": str(comprobante["id"]),
                "inv_id": str(item.inventario_id) if item.inventario_id else None,
                "desc": item.descripcion,
                "cantidad": item.cantidad,
                "precio": item.precio_unitario,
                "iva_pct": item.porcentaje_iva,
                "subtotal": subtotal,
                "iva_monto": iva_monto,
            },
        )

    await audit(db, usuario=current_user, accion="INSERT", tabla="comprobantes",
                registro_id=str(comprobante["id"]),
                datos_nuevos={"numero": data.numero_comprobante, "total": data.monto_total,
                              "condicion": data.condicion})

    # ── Asiento contable automático (partida doble) ───────────────────────────
    try:
        comp_id_str = str(comprobante["id"])
        if data.cliente_id:
            nombre = (await db.execute(
                text("SELECT nombre FROM clientes WHERE id = :id AND empresa_id = :e"),
                {"id": str(data.cliente_id), "e": empresa_id},
            )).scalar() or "—"
            await asiento_comprobante_venta(
                db, empresa_id, comp_id_str, data.numero_comprobante,
                data.fecha_emision, data.monto_subtotal, data.monto_iva,
                data.monto_total, nombre, usuario_id,
            )
        else:
            nombre = (await db.execute(
                text("SELECT nombre FROM proveedores WHERE id = :id AND empresa_id = :e"),
                {"id": str(data.proveedor_id), "e": empresa_id},
            )).scalar() or "—"
            await asiento_comprobante_compra(
                db, empresa_id, comp_id_str, data.numero_comprobante,
                data.fecha_emision, data.monto_subtotal, data.monto_iva,
                data.monto_total, nombre, usuario_id,
            )
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("Asiento auto falló (no crítico): %s", exc)

    await db.commit()
    return {**dict(comprobante), "detalle": []}


@router.patch("/{comprobante_id}/validar", summary="Aprobar o rechazar un comprobante OCR")
async def validar_comprobante(
    comprobante_id: UUID,
    estado: str = Query(..., pattern="^(confirmado|rechazado)$"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_escritura),
):
    """Human-in-the-Loop: confirma o rechaza un comprobante cargado por OCR."""
    empresa_id = current_user["empresa_id"]
    await db.execute(
        text("""
            UPDATE comprobantes
            SET estado_validacion = :estado, fecha_modificacion = NOW()
            WHERE id = :id AND empresa_id = :empresa_id
        """),
        {"estado": estado, "id": str(comprobante_id), "empresa_id": empresa_id},
    )
    return {"mensaje": f"Comprobante marcado como '{estado}'"}


# ── Anulación de comprobantes (Fase B) ───────────────────────────────────────

@router.patch("/{comprobante_id}", response_model=ComprobanteRead, summary="Editar campos seguros de un comprobante")
async def editar_comprobante(
    comprobante_id: UUID,
    data: ComprobanteUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_escritura),
):
    """Edita solo metadatos seguros; no modifica montos ni detalle."""
    empresa_id = current_user["empresa_id"]
    rol = current_user.get("rol")
    cambios = data.model_dump(exclude_unset=True)
    if not cambios:
        raise HTTPException(status_code=422, detail="No hay campos para actualizar")

    row = (await db.execute(
        text("""
            SELECT id, estado_validacion, numero_comprobante, fecha_emision,
                   fecha_vencimiento, notas, condicion, medio_pago_contado
            FROM comprobantes
            WHERE id = :id AND empresa_id = :empresa_id
        """),
        {"id": str(comprobante_id), "empresa_id": empresa_id},
    )).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Comprobante no encontrado")
    if row["estado_validacion"] == "anulado":
        raise HTTPException(status_code=409, detail="No se puede editar un comprobante anulado")
    if row["estado_validacion"] == "confirmado" and rol != "admin":
        raise HTTPException(status_code=403, detail="Solo admin puede editar comprobantes confirmados")

    if cambios.get("condicion") == "credito":
        cambios["medio_pago_contado"] = None
    elif cambios.get("condicion") == "contado" and not cambios.get("medio_pago_contado"):
        cambios["medio_pago_contado"] = row["medio_pago_contado"] or "efectivo"

    sets = []
    params = {"id": str(comprobante_id), "empresa_id": empresa_id}
    for key, value in cambios.items():
        sets.append(f"{key} = :{key}")
        params[key] = value
    sets.append("fecha_modificacion = NOW()")

    result = await db.execute(
        text(f"""
            UPDATE comprobantes
            SET {', '.join(sets)}
            WHERE id = :id AND empresa_id = :empresa_id
            RETURNING id, empresa_id, tipo_id, comprobante_origen_id,
                      numero_comprobante, fecha_emision, fecha_vencimiento,
                      monto_total, saldo_pendiente, metodo_carga, estado_validacion,
                      condicion, medio_pago_contado, cliente_id, proveedor_id,
                      ruta_archivo, notas, fecha_creacion
        """),
        params,
    )
    actualizado = result.mappings().first()
    await audit(
        db,
        usuario=current_user,
        accion="UPDATE",
        tabla="comprobantes",
        registro_id=str(comprobante_id),
        datos_anteriores={k: row[k] for k in cambios if k in row},
        datos_nuevos=cambios,
    )
    await db.commit()
    return {**dict(actualizado), "detalle": [], "notas_vinculadas": []}


class AnularIn(BaseModel):
    motivo: str = Field(..., min_length=5, max_length=500,
                        description="Razón de la anulación (mínimo 5 caracteres).")


@router.patch("/{comprobante_id}/anular", summary="Anular un comprobante con motivo")
async def anular_comprobante(
    comprobante_id: UUID,
    data: AnularIn,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_escritura),
):
    """
    Anula un comprobante de forma definitiva (soft-anulado: queda registrado
    con motivo, fecha y usuario que lo anuló; NUNCA se borra físicamente).
    """
    empresa_id = current_user["empresa_id"]
    usuario_id = current_user["sub"]

    # Verificar que exista y no esté ya anulado
    row = (await db.execute(
        text("""
            SELECT id, tipo_id, comprobante_origen_id, monto_total, estado_validacion
            FROM comprobantes
            WHERE id = :id AND empresa_id = :empresa_id
        """),
        {"id": str(comprobante_id), "empresa_id": empresa_id},
    )).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Comprobante no encontrado")
    if row["estado_validacion"] == "anulado":
        raise HTTPException(status_code=409, detail="El comprobante ya estaba anulado")

    notas_activas = (await db.execute(
        text("""
            SELECT COUNT(*)
            FROM comprobantes
            WHERE comprobante_origen_id = :id
              AND empresa_id = :empresa_id
              AND estado_validacion <> 'anulado'
        """),
        {"id": str(comprobante_id), "empresa_id": empresa_id},
    )).scalar() or 0
    if notas_activas:
        raise HTTPException(
            status_code=409,
            detail="Este comprobante tiene notas vinculadas activas. Anula primero esas notas.",
        )

    tipo_movimiento = await _tipo_movimiento_nota(db, empresa_id, row["tipo_id"])
    if row["comprobante_origen_id"] and tipo_movimiento != 0:
        await db.execute(
            text("""
                UPDATE comprobantes
                SET saldo_pendiente = CASE
                        WHEN :movimiento < 0 THEN saldo_pendiente + :monto
                        ELSE GREATEST(0, saldo_pendiente - :monto)
                    END,
                    fecha_modificacion = NOW()
                WHERE id = :origen_id AND empresa_id = :empresa_id
            """),
            {
                "movimiento": tipo_movimiento,
                "monto": row["monto_total"],
                "origen_id": str(row["comprobante_origen_id"]),
                "empresa_id": empresa_id,
            },
        )

    # Al anular, ponemos saldo_pendiente = 0 también. Sin esto el saldo del
    # comprobante queda "fantasma" y sigue contando en agregaciones (vistas
    # v_saldo_*, queries que filtran solo por saldo_pendiente > 0).
    await db.execute(
        text("""
            UPDATE comprobantes
            SET estado_validacion = 'anulado',
                saldo_pendiente = 0,
                motivo_anulacion = :motivo,
                fecha_anulacion = NOW(),
                usuario_anulacion_id = :usuario_id,
                fecha_modificacion = NOW()
            WHERE id = :id AND empresa_id = :empresa_id
        """),
        {
            "id": str(comprobante_id),
            "empresa_id": empresa_id,
            "motivo": data.motivo.strip(),
            "usuario_id": usuario_id,
        },
    )
    await audit(db, usuario=current_user, accion="UPDATE", tabla="comprobantes",
                registro_id=str(comprobante_id),
                datos_nuevos={
                    "accion": "anular",
                    "motivo": data.motivo.strip(),
                    "reversion_nota_vinculada": bool(row["comprobante_origen_id"] and tipo_movimiento != 0),
                })

    # Asiento inverso por anulación
    try:
        await revertir_asiento_comprobante(
            db, empresa_id, str(comprobante_id), usuario_id
        )
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("Asiento reverso falló (no crítico): %s", exc)

    await db.commit()
    return {
        "mensaje": "Comprobante anulado correctamente",
        "motivo": data.motivo.strip(),
    }
