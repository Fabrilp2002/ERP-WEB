"""
Router /adjuntos — sube imágenes o PDFs asociados a:
- comprobantes (factura escaneada original)
- pagos        (recibo escaneado)

A diferencia de la versión desktop, los archivos se guardan en **Supabase Storage**
(bucket `adjuntos`, privado). En la BD se guarda la ruta dentro del bucket
(ej: `EMPRESA_ID/comprobantes/COMP_ID.pdf`). El frontend pide una signed URL
temporal vía `GET /adjuntos/<tipo>/<id>/url` para mostrar el archivo.

Cualquier usuario autenticado puede leer/descargar; solo roles con escritura
pueden subir/eliminar.
"""
from __future__ import annotations
from pathlib import PurePosixPath
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from ..core.database import get_db
from ..core.security import get_current_user, require_escritura
from ..core.storage import storage, StorageError
from ..services.audit import registrar as audit

router = APIRouter(prefix="/adjuntos", tags=["Adjuntos"])


ALLOWED = {
    "image/png":        ".png",
    "image/jpeg":       ".jpg",
    "image/jpg":        ".jpg",
    "image/webp":       ".webp",
    "application/pdf":  ".pdf",
}
MAX_SIZE = 8 * 1024 * 1024  # 8 MB

TABLAS_PERMITIDAS = {"comprobantes", "pagos"}


# ─── Helpers ─────────────────────────────────────────────────────────────────

async def _verificar_permiso(db: AsyncSession, tabla: str, reg_id: str, empresa_id: str):
    if tabla not in TABLAS_PERMITIDAS:
        raise ValueError(f"Tabla no permitida: {tabla}")
    row = (await db.execute(
        text(f"SELECT 1 FROM {tabla} WHERE id = :id AND empresa_id = :e"),
        {"id": reg_id, "e": empresa_id},
    )).scalar()
    if not row:
        raise HTTPException(status_code=404,
                            detail=f"{tabla[:-1].capitalize()} no encontrado")


def _validar_archivo(content_type: str | None, contenido: bytes) -> str:
    """Devuelve la extensión normalizada o lanza HTTPException."""
    if content_type not in ALLOWED:
        raise HTTPException(status_code=415,
                            detail="Formato no permitido. Usa PNG, JPG, WEBP o PDF.")
    if len(contenido) > MAX_SIZE:
        raise HTTPException(status_code=413, detail="El archivo supera 8MB.")
    return ALLOWED[content_type]


def _ext_from_path(path: str | None) -> str | None:
    """Saca la extensión de una ruta tipo `EMPRESA/comprobantes/UUID.pdf`."""
    if not path:
        return None
    return PurePosixPath(path).suffix or None


# ─── Comprobantes ────────────────────────────────────────────────────────────

@router.post("/comprobante/{comprobante_id}", summary="Adjuntar imagen/PDF a un comprobante")
async def subir_adjunto_comprobante(
    comprobante_id: UUID,
    archivo: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_escritura),
):
    empresa_id = current_user["empresa_id"]
    await _verificar_permiso(db, "comprobantes", str(comprobante_id), empresa_id)

    contenido = await archivo.read()
    ext = _validar_archivo(archivo.content_type, contenido)

    # Borrar adjunto previo (si había uno con otra extensión, ej: .jpg → .pdf)
    prev_path = (await db.execute(
        text("SELECT ruta_archivo FROM comprobantes WHERE id = :id"),
        {"id": str(comprobante_id)},
    )).scalar()
    prev_ext = _ext_from_path(prev_path)
    if prev_ext and prev_ext != ext:
        try:
            storage.delete_adjunto_comprobante(empresa_id, str(comprobante_id), prev_ext)
        except StorageError:
            pass  # no es crítico si falla

    # Subir el nuevo archivo
    try:
        ruta = storage.upload_adjunto_comprobante(
            empresa_id=empresa_id,
            comprobante_id=str(comprobante_id),
            contenido=contenido,
            filename=archivo.filename or f"comprobante{ext}",
        )
    except StorageError as e:
        raise HTTPException(status_code=502, detail=f"Error al subir a Storage: {e}")

    await db.execute(
        text("UPDATE comprobantes SET ruta_archivo = :r WHERE id = :id AND empresa_id = :e"),
        {"r": ruta, "id": str(comprobante_id), "e": empresa_id},
    )
    await audit(
        db, usuario=current_user, accion="UPDATE", tabla="comprobantes",
        registro_id=str(comprobante_id),
        datos_nuevos={"evento": "subir_adjunto", "ruta": ruta, "bytes": len(contenido)},
    )
    await db.commit()
    return {"ruta_archivo": ruta, "bytes": len(contenido)}


@router.delete("/comprobante/{comprobante_id}", summary="Quitar adjunto de un comprobante")
async def quitar_adjunto_comprobante(
    comprobante_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_escritura),
):
    empresa_id = current_user["empresa_id"]
    await _verificar_permiso(db, "comprobantes", str(comprobante_id), empresa_id)

    prev_path = (await db.execute(
        text("SELECT ruta_archivo FROM comprobantes WHERE id = :id"),
        {"id": str(comprobante_id)},
    )).scalar()
    ext = _ext_from_path(prev_path)
    if ext:
        try:
            storage.delete_adjunto_comprobante(empresa_id, str(comprobante_id), ext)
        except StorageError:
            pass  # log pero no fallar — la BD se debe poder limpiar de todos modos

    await db.execute(
        text("UPDATE comprobantes SET ruta_archivo = NULL WHERE id = :id AND empresa_id = :e"),
        {"id": str(comprobante_id), "e": empresa_id},
    )
    await audit(
        db, usuario=current_user, accion="UPDATE", tabla="comprobantes",
        registro_id=str(comprobante_id), datos_nuevos={"evento": "quitar_adjunto"},
    )
    await db.commit()
    return {"mensaje": "Adjunto eliminado"}


@router.get("/comprobante/{comprobante_id}/url", summary="Obtener signed URL temporal del adjunto")
async def url_adjunto_comprobante(
    comprobante_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Devuelve una URL firmada con expiración (~1h) para mostrar el adjunto."""
    empresa_id = current_user["empresa_id"]
    await _verificar_permiso(db, "comprobantes", str(comprobante_id), empresa_id)

    ruta = (await db.execute(
        text("SELECT ruta_archivo FROM comprobantes WHERE id = :id"),
        {"id": str(comprobante_id)},
    )).scalar()
    if not ruta:
        raise HTTPException(status_code=404, detail="Este comprobante no tiene adjunto")

    ext = _ext_from_path(ruta) or ".bin"
    try:
        url = storage.url_adjunto_comprobante(empresa_id, str(comprobante_id), ext)
    except StorageError as e:
        raise HTTPException(status_code=502, detail=f"Error al firmar URL: {e}")
    return {"url": url, "ruta_archivo": ruta}


# ─── Pagos ───────────────────────────────────────────────────────────────────

@router.post("/pago/{pago_id}", summary="Adjuntar imagen/PDF a un recibo de pago")
async def subir_adjunto_pago(
    pago_id: UUID,
    archivo: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_escritura),
):
    empresa_id = current_user["empresa_id"]
    await _verificar_permiso(db, "pagos", str(pago_id), empresa_id)

    contenido = await archivo.read()
    ext = _validar_archivo(archivo.content_type, contenido)

    prev_path = (await db.execute(
        text("SELECT ruta_adjunto FROM pagos WHERE id = :id"),
        {"id": str(pago_id)},
    )).scalar()
    prev_ext = _ext_from_path(prev_path)
    if prev_ext and prev_ext != ext:
        try:
            storage.delete_adjunto_pago(empresa_id, str(pago_id), prev_ext)
        except StorageError:
            pass

    try:
        ruta = storage.upload_adjunto_pago(
            empresa_id=empresa_id,
            pago_id=str(pago_id),
            contenido=contenido,
            filename=archivo.filename or f"recibo{ext}",
        )
    except StorageError as e:
        raise HTTPException(status_code=502, detail=f"Error al subir a Storage: {e}")

    await db.execute(
        text("UPDATE pagos SET ruta_adjunto = :r WHERE id = :id AND empresa_id = :e"),
        {"r": ruta, "id": str(pago_id), "e": empresa_id},
    )
    await audit(
        db, usuario=current_user, accion="UPDATE", tabla="pagos",
        registro_id=str(pago_id),
        datos_nuevos={"evento": "subir_adjunto", "ruta": ruta, "bytes": len(contenido)},
    )
    await db.commit()
    return {"ruta_adjunto": ruta, "bytes": len(contenido)}


@router.delete("/pago/{pago_id}", summary="Quitar adjunto de un pago")
async def quitar_adjunto_pago(
    pago_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_escritura),
):
    empresa_id = current_user["empresa_id"]
    await _verificar_permiso(db, "pagos", str(pago_id), empresa_id)

    prev_path = (await db.execute(
        text("SELECT ruta_adjunto FROM pagos WHERE id = :id"),
        {"id": str(pago_id)},
    )).scalar()
    ext = _ext_from_path(prev_path)
    if ext:
        try:
            storage.delete_adjunto_pago(empresa_id, str(pago_id), ext)
        except StorageError:
            pass

    await db.execute(
        text("UPDATE pagos SET ruta_adjunto = NULL WHERE id = :id AND empresa_id = :e"),
        {"id": str(pago_id), "e": empresa_id},
    )
    await audit(
        db, usuario=current_user, accion="UPDATE", tabla="pagos",
        registro_id=str(pago_id), datos_nuevos={"evento": "quitar_adjunto"},
    )
    await db.commit()
    return {"mensaje": "Adjunto eliminado"}


@router.get("/pago/{pago_id}/url", summary="Obtener signed URL temporal del recibo")
async def url_adjunto_pago(
    pago_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Devuelve una URL firmada con expiración (~1h) para mostrar el recibo."""
    empresa_id = current_user["empresa_id"]
    await _verificar_permiso(db, "pagos", str(pago_id), empresa_id)

    ruta = (await db.execute(
        text("SELECT ruta_adjunto FROM pagos WHERE id = :id"),
        {"id": str(pago_id)},
    )).scalar()
    if not ruta:
        raise HTTPException(status_code=404, detail="Este pago no tiene adjunto")

    ext = _ext_from_path(ruta) or ".bin"
    try:
        url = storage.url_adjunto_pago(empresa_id, str(pago_id), ext)
    except StorageError as e:
        raise HTTPException(status_code=502, detail=f"Error al firmar URL: {e}")
    return {"url": url, "ruta_adjunto": ruta}
