"""
Router /empresa — configuración de la empresa del usuario logueado.

- GET    /empresa        : datos de la empresa (cualquier rol autenticado)
- PATCH  /empresa        : actualizar datos (solo admin)
- POST   /empresa/logo   : subir logo (solo admin) — imagen <=2MB
- DELETE /empresa/logo   : quitar logo (solo admin)

El logo vive en Supabase Storage (bucket público `logos`). En `empresas.logo_url`
se guarda la URL pública directa, que el frontend usa tal cual con `<img>`.
"""
from __future__ import annotations
from pathlib import PurePosixPath
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from ..core.database import get_db
from ..core.security import get_current_user, require_admin
from ..core.storage import storage, StorageError
from ..services.audit import registrar as audit

router = APIRouter(prefix="/empresa", tags=["Empresa"])


ALLOWED_MIME = {
    "image/png":      ".png",
    "image/jpeg":     ".jpg",
    "image/jpg":      ".jpg",
    "image/webp":     ".webp",
    "image/svg+xml":  ".svg",
}
MAX_SIZE = 2 * 1024 * 1024  # 2 MB


class EmpresaUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=2, max_length=200)
    ruc: Optional[str] = Field(None, max_length=30)
    direccion: Optional[str] = Field(None, max_length=300)
    telefono: Optional[str] = Field(None, max_length=50)
    email: Optional[EmailStr] = None
    moneda_principal: Optional[str] = Field(None, max_length=10)


def _ext_from_url(url: str | None) -> str | None:
    """Saca extensión de una URL pública de Supabase (`.../logos/EID/logo.png`)."""
    if not url:
        return None
    return PurePosixPath(url.split("?", 1)[0]).suffix or None


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.get("", summary="Datos de la empresa actual")
async def obtener_empresa(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    empresa_id = current_user["empresa_id"]
    row = (await db.execute(
        text("""
            SELECT id, nombre, ruc, direccion, telefono, email,
                   moneda_principal, logo_url, activa, fecha_creacion
            FROM empresas WHERE id = :id
        """),
        {"id": empresa_id},
    )).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    return dict(row)


@router.patch("", summary="Actualizar datos de la empresa (solo admin)")
async def actualizar_empresa(
    data: EmpresaUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    empresa_id = current_user["empresa_id"]
    updates = data.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="Nada para actualizar")

    set_parts = ", ".join(f"{k} = :{k}" for k in updates)
    params = {**updates, "id": empresa_id}
    await db.execute(
        text(f"UPDATE empresas SET {set_parts} WHERE id = :id"),
        params,
    )
    await audit(
        db, usuario=current_user, accion="UPDATE", tabla="empresas",
        registro_id=empresa_id, datos_nuevos=updates,
    )
    await db.commit()

    return await obtener_empresa(db, current_user)


@router.post("/logo", summary="Subir logo de empresa (solo admin)")
async def subir_logo(
    archivo: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    empresa_id = current_user["empresa_id"]

    if archivo.content_type not in ALLOWED_MIME:
        raise HTTPException(
            status_code=415,
            detail="Formato no permitido. Usa PNG, JPG, WEBP o SVG.",
        )

    contenido = await archivo.read()
    if len(contenido) > MAX_SIZE:
        raise HTTPException(
            status_code=413, detail="El logo supera 2MB. Reducilo antes de subir.",
        )

    ext = ALLOWED_MIME[archivo.content_type]

    # Borrar logo previo si tenía otra extensión (PNG → SVG, etc.)
    prev_url = (await db.execute(
        text("SELECT logo_url FROM empresas WHERE id = :id"),
        {"id": empresa_id},
    )).scalar()
    prev_ext = _ext_from_url(prev_url)
    if prev_ext and prev_ext != ext:
        try:
            storage.delete_logo(empresa_id, prev_ext)
        except StorageError:
            pass  # no es crítico

    # Subir el nuevo logo
    try:
        _path, public_url = storage.upload_logo(
            empresa_id=empresa_id,
            contenido=contenido,
            filename=archivo.filename or f"logo{ext}",
        )
    except StorageError as e:
        raise HTTPException(status_code=502, detail=f"Error al subir a Storage: {e}")

    # Cache-bust appendiendo timestamp para que el frontend recargue al actualizar
    import time
    cache_busted_url = f"{public_url}?v={int(time.time())}"

    await db.execute(
        text("UPDATE empresas SET logo_url = :u WHERE id = :id"),
        {"u": cache_busted_url, "id": empresa_id},
    )
    await audit(
        db, usuario=current_user, accion="UPDATE", tabla="empresas",
        registro_id=empresa_id,
        datos_nuevos={"evento": "subir_logo", "url": public_url, "bytes": len(contenido)},
    )
    await db.commit()
    return {"logo_url": cache_busted_url, "bytes": len(contenido)}


@router.delete("/logo", summary="Quitar logo de empresa (solo admin)")
async def quitar_logo(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    empresa_id = current_user["empresa_id"]

    prev_url = (await db.execute(
        text("SELECT logo_url FROM empresas WHERE id = :id"),
        {"id": empresa_id},
    )).scalar()
    ext = _ext_from_url(prev_url)
    if ext:
        try:
            storage.delete_logo(empresa_id, ext)
        except StorageError:
            pass

    await db.execute(
        text("UPDATE empresas SET logo_url = NULL WHERE id = :id"),
        {"id": empresa_id},
    )
    await audit(
        db, usuario=current_user, accion="UPDATE", tabla="empresas",
        registro_id=empresa_id, datos_nuevos={"evento": "quitar_logo"},
    )
    await db.commit()
    return {"mensaje": "Logo eliminado"}
