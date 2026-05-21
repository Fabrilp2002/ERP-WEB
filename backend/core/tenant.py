"""
Helpers de contexto multi-tenant para RLS (Row Level Security).

Las tablas con `empresa_id` tienen política RLS `tenant_isolation` que filtra
filas según `current_setting('app.current_empresa')`. Antes de cada query
"de negocio", el backend debe setear ese valor por sesión.

Uso recomendado en routers:

    @router.get("/")
    async def listar(
        db: AsyncSession = Depends(get_db_tenant),  # <- ya tiene contexto
        current_user: dict = Depends(get_current_user),
    ):
        ...

Alternativa más manual:

    await set_tenant_context(db, current_user["empresa_id"])
"""
from __future__ import annotations

from fastapi import Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_db
from .security import get_current_user


async def set_tenant_context(db: AsyncSession, empresa_id: str | None) -> None:
    """Setea `app.current_empresa` para la sesión actual.

    `set_config(name, value, true)` con `true` = LOCAL (solo dura hasta el
    final de la transacción), idéntico a `SET LOCAL`. Si `empresa_id` viene
    None o vacío, no hace nada — y la política RLS rechazará cualquier query.
    """
    if not empresa_id:
        return
    await db.execute(
        text("SELECT set_config('app.current_empresa', :eid, true)"),
        {"eid": str(empresa_id)},
    )


async def get_db_tenant(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Dependency combinada: provee db con tenant context ya seteado.

    Reemplaza a `Depends(get_db)` en routers que necesitan filtrado multi-tenant
    a nivel base de datos. La adopción es gradual: las rutas que no la usan
    siguen funcionando si el usuario backend tiene `BYPASSRLS`.
    """
    await set_tenant_context(db, current_user.get("empresa_id"))
    return db
