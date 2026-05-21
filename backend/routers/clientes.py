from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from ..core.database import get_db
from ..core.security import get_current_user, require_escritura
from ..models.schemas import ClienteCreate, ClienteRead
from ..services.audit import registrar as audit

router = APIRouter(prefix="/clientes", tags=["Clientes"])


@router.get("/", response_model=list[ClienteRead], summary="Listar clientes")
async def listar_clientes(
    buscar: str = Query(None, description="Buscar por nombre o RUC"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    empresa_id = current_user["empresa_id"]
    filtro = "AND (nombre ILIKE :buscar OR ruc ILIKE :buscar)" if buscar else ""
    result = await db.execute(
        text(f"""
            SELECT id, empresa_id, nombre, ruc, telefono, email, direccion, notas, activo, fecha_creacion
            FROM clientes
            WHERE empresa_id = :empresa_id AND activo = TRUE {filtro}
            ORDER BY nombre
        """),
        {"empresa_id": empresa_id, "buscar": f"%{buscar}%" if buscar else None},
    )
    return result.mappings().all()


@router.post("/", response_model=ClienteRead, status_code=status.HTTP_201_CREATED,
             summary="Crear cliente")
async def crear_cliente(
    data: ClienteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_escritura),
):
    empresa_id = current_user["empresa_id"]
    result = await db.execute(
        text("""
            INSERT INTO clientes (empresa_id, nombre, ruc, telefono, email, direccion, notas)
            VALUES (:empresa_id, :nombre, :ruc, :telefono, :email, :direccion, :notas)
            RETURNING id, empresa_id, nombre, ruc, telefono, email, direccion, notas, activo, fecha_creacion
        """),
        {"empresa_id": empresa_id, **data.model_dump()},
    )
    row = result.mappings().first()
    await audit(db, usuario=current_user, accion="INSERT", tabla="clientes",
                registro_id=str(row["id"]), datos_nuevos=data.model_dump())
    await db.commit()
    return row


@router.put("/{cliente_id}", response_model=ClienteRead, summary="Actualizar cliente")
async def actualizar_cliente(
    cliente_id: UUID,
    data: ClienteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_escritura),
):
    empresa_id = current_user["empresa_id"]
    result = await db.execute(
        text("""
            UPDATE clientes
            SET nombre=:nombre, ruc=:ruc, telefono=:telefono,
                email=:email, direccion=:direccion, notas=:notas
            WHERE id=:id AND empresa_id=:empresa_id
            RETURNING id, empresa_id, nombre, ruc, telefono, email, direccion, notas, activo, fecha_creacion
        """),
        {"id": str(cliente_id), "empresa_id": empresa_id, **data.model_dump()},
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    await audit(db, usuario=current_user, accion="UPDATE", tabla="clientes",
                registro_id=str(cliente_id), datos_nuevos=data.model_dump())
    await db.commit()
    return row


@router.delete("/{cliente_id}", summary="Anular/desactivar cliente")
async def eliminar_cliente(
    cliente_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_escritura),
):
    empresa_id = current_user["empresa_id"]
    ex = (await db.execute(
        text("SELECT nombre, ruc, activo FROM clientes WHERE id=:id AND empresa_id=:e"),
        {"id": str(cliente_id), "e": empresa_id},
    )).mappings().first()
    if not ex:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    await db.execute(
        text("UPDATE clientes SET activo = FALSE WHERE id=:id AND empresa_id=:e"),
        {"id": str(cliente_id), "e": empresa_id},
    )
    await audit(db, usuario=current_user, accion="DELETE", tabla="clientes",
                registro_id=str(cliente_id), datos_anteriores=dict(ex))
    await db.commit()
    return {"mensaje": "Cliente anulado"}


@router.get("/{cliente_id}/saldo", summary="Estado de cuenta del cliente")
async def saldo_cliente(
    cliente_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    empresa_id = current_user["empresa_id"]
    result = await db.execute(
        text("""
            SELECT * FROM v_saldo_clientes
            WHERE empresa_id = :empresa_id AND cliente_id = :cliente_id
        """),
        {"empresa_id": empresa_id, "cliente_id": str(cliente_id)},
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return row
