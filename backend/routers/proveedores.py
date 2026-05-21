from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from ..core.database import get_db
from ..core.security import get_current_user, require_escritura
from ..models.schemas import ProveedorCreate, ProveedorRead
from ..services.audit import registrar as audit

router = APIRouter(prefix="/proveedores", tags=["Proveedores"])


@router.get("/", response_model=list[ProveedorRead], summary="Listar proveedores")
async def listar_proveedores(
    buscar: str = Query(None, description="Buscar por nombre o RUC"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    empresa_id = current_user["empresa_id"]
    filtro = "AND (nombre ILIKE :buscar OR ruc ILIKE :buscar)" if buscar else ""
    result = await db.execute(
        text(f"""
            SELECT id, empresa_id, nombre, ruc, telefono, email, direccion, notas, activo, fecha_creacion
            FROM proveedores
            WHERE empresa_id = :empresa_id AND activo = TRUE {filtro}
            ORDER BY nombre
        """),
        {"empresa_id": empresa_id, "buscar": f"%{buscar}%" if buscar else None},
    )
    return result.mappings().all()


@router.post("/", response_model=ProveedorRead, status_code=status.HTTP_201_CREATED,
             summary="Crear proveedor")
async def crear_proveedor(
    data: ProveedorCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_escritura),
):
    empresa_id = current_user["empresa_id"]
    result = await db.execute(
        text("""
            INSERT INTO proveedores (empresa_id, nombre, ruc, telefono, email, direccion, notas)
            VALUES (:empresa_id, :nombre, :ruc, :telefono, :email, :direccion, :notas)
            RETURNING id, empresa_id, nombre, ruc, telefono, email, direccion, notas, activo, fecha_creacion
        """),
        {"empresa_id": empresa_id, **data.model_dump()},
    )
    row = result.mappings().first()
    await audit(db, usuario=current_user, accion="INSERT", tabla="proveedores",
                registro_id=str(row["id"]), datos_nuevos=data.model_dump())
    await db.commit()
    return row


@router.put("/{proveedor_id}", response_model=ProveedorRead, summary="Actualizar proveedor")
async def actualizar_proveedor(
    proveedor_id: UUID,
    data: ProveedorCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_escritura),
):
    empresa_id = current_user["empresa_id"]
    result = await db.execute(
        text("""
            UPDATE proveedores
            SET nombre=:nombre, ruc=:ruc, telefono=:telefono,
                email=:email, direccion=:direccion, notas=:notas
            WHERE id=:id AND empresa_id=:empresa_id
            RETURNING id, empresa_id, nombre, ruc, telefono, email, direccion, notas, activo, fecha_creacion
        """),
        {"id": str(proveedor_id), "empresa_id": empresa_id, **data.model_dump()},
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    await audit(db, usuario=current_user, accion="UPDATE", tabla="proveedores",
                registro_id=str(proveedor_id), datos_nuevos=data.model_dump())
    await db.commit()
    return row


@router.delete("/{proveedor_id}", summary="Anular/desactivar proveedor")
async def eliminar_proveedor(
    proveedor_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_escritura),
):
    empresa_id = current_user["empresa_id"]
    ex = (await db.execute(
        text("SELECT nombre, ruc, activo FROM proveedores WHERE id=:id AND empresa_id=:e"),
        {"id": str(proveedor_id), "e": empresa_id},
    )).mappings().first()
    if not ex:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    await db.execute(
        text("UPDATE proveedores SET activo = FALSE WHERE id=:id AND empresa_id=:e"),
        {"id": str(proveedor_id), "e": empresa_id},
    )
    await audit(db, usuario=current_user, accion="DELETE", tabla="proveedores",
                registro_id=str(proveedor_id), datos_anteriores=dict(ex))
    await db.commit()
    return {"mensaje": "Proveedor anulado"}


@router.get("/{proveedor_id}/saldo", summary="Estado de cuenta del proveedor")
async def saldo_proveedor(
    proveedor_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    empresa_id = current_user["empresa_id"]
    result = await db.execute(
        text("""
            SELECT * FROM v_saldo_proveedores
            WHERE empresa_id = :empresa_id AND proveedor_id = :proveedor_id
        """),
        {"empresa_id": empresa_id, "proveedor_id": str(proveedor_id)},
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    return row
