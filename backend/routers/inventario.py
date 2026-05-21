from decimal import Decimal
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from ..core.database import get_db
from ..core.security import get_current_user, require_escritura
from ..models.schemas import InventarioCreate, InventarioRead

router = APIRouter(prefix="/inventario", tags=["Inventario"])


@router.get("/", response_model=list[InventarioRead], summary="Listar items de inventario")
async def listar_inventario(
    bajo_stock: bool = Query(False, description="Solo items bajo punto de reorden"),
    buscar: str = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    empresa_id = current_user["empresa_id"]
    filtros = []
    if bajo_stock:
        filtros.append("i.cantidad_actual <= i.punto_reorden AND i.punto_reorden > 0")
    if buscar:
        filtros.append("(i.descripcion ILIKE :buscar OR i.codigo ILIKE :buscar)")
    where_extra = ("AND " + " AND ".join(filtros)) if filtros else ""

    result = await db.execute(
        text(f"""
            SELECT i.id, i.empresa_id, i.codigo, i.descripcion, i.cantidad_actual,
                   i.costo_unitario, i.unidad_medida, i.punto_reorden, i.activo, i.fecha_creacion,
                   i.categoria_id, ci.nombre AS categoria_nombre
            FROM inventario i
            LEFT JOIN categorias_inventario ci ON ci.id = i.categoria_id
            WHERE i.empresa_id = :empresa_id AND i.activo = TRUE {where_extra}
            ORDER BY ci.nombre NULLS LAST, i.codigo
        """),
        {"empresa_id": empresa_id, "buscar": f"%{buscar}%" if buscar else None},
    )
    return result.mappings().all()


@router.post("/", response_model=InventarioRead, status_code=status.HTTP_201_CREATED,
             summary="Crear item de inventario")
async def crear_item(
    data: InventarioCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_escritura),
):
    empresa_id = current_user["empresa_id"]
    result = await db.execute(
        text("""
            INSERT INTO inventario (
                empresa_id, categoria_id, codigo, descripcion,
                unidad_medida, cantidad_actual, costo_unitario, punto_reorden
            ) VALUES (
                :empresa_id, :categoria_id, :codigo, :descripcion,
                :unidad_medida, :cantidad_actual, :costo_unitario, :punto_reorden
            )
            RETURNING id, empresa_id, descripcion, cantidad_actual,
                      costo_unitario, punto_reorden, activo, fecha_creacion
        """),
        {"empresa_id": empresa_id, **data.model_dump()},
    )
    return result.mappings().first()


@router.patch("/{item_id}/cantidad", summary="Ajustar cantidad de stock")
async def ajustar_cantidad(
    item_id: UUID,
    cantidad_nueva: Decimal = Query(..., description="Nueva cantidad absoluta"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_escritura),
):
    empresa_id = current_user["empresa_id"]
    await db.execute(
        text("""
            UPDATE inventario SET cantidad_actual = :cantidad
            WHERE id = :id AND empresa_id = :empresa_id
        """),
        {"cantidad": cantidad_nueva, "id": str(item_id), "empresa_id": empresa_id},
    )
    return {"mensaje": "Stock actualizado"}


@router.put("/{item_id}", response_model=InventarioRead, summary="Actualizar item de inventario")
async def actualizar_item(
    item_id: UUID,
    data: InventarioCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_escritura),
):
    empresa_id = current_user["empresa_id"]
    result = await db.execute(
        text("""
            UPDATE inventario SET
                categoria_id   = :categoria_id,
                codigo         = :codigo,
                descripcion    = :descripcion,
                unidad_medida  = :unidad_medida,
                cantidad_actual= :cantidad_actual,
                costo_unitario = :costo_unitario,
                punto_reorden  = :punto_reorden
            WHERE id = :id AND empresa_id = :empresa_id
            RETURNING id, empresa_id, codigo, descripcion, cantidad_actual,
                      costo_unitario, unidad_medida, punto_reorden, activo,
                      fecha_creacion, categoria_id
        """),
        {"id": str(item_id), "empresa_id": empresa_id, **data.model_dump()},
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Item no encontrado")
    return row


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Eliminar item (soft delete: activo=FALSE)")
async def eliminar_item(
    item_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_escritura),
):
    empresa_id = current_user["empresa_id"]
    result = await db.execute(
        text("""
            UPDATE inventario SET activo = FALSE
            WHERE id = :id AND empresa_id = :empresa_id
            RETURNING id
        """),
        {"id": str(item_id), "empresa_id": empresa_id},
    )
    if not result.first():
        raise HTTPException(status_code=404, detail="Item no encontrado")
