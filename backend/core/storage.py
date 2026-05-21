"""
Wrapper de Supabase Storage para adjuntos y logos.

Reemplaza el almacenamiento en disco de la versión desktop (`backend/core/paths.py`).

Buckets esperados (crearlos en Supabase Dashboard → Storage):
  - `adjuntos`  → privado (signed URLs con expiración)
  - `logos`     → público (URLs directas)

Uso típico:
    from backend.core.storage import storage

    # Subir factura adjunta
    path = storage.upload_adjunto_comprobante(
        empresa_id="...", comprobante_id="...",
        contenido=file.read(), filename=file.filename,
    )
    # path es algo como "EMPRESA_ID/comprobantes/COMP_ID.pdf"

    # Obtener URL para que el frontend la pueda mostrar
    url = storage.url_adjunto_comprobante(empresa_id, comprobante_id, ".pdf")

    # Borrar
    storage.delete_adjunto_comprobante(empresa_id, comprobante_id, ".pdf")
"""
from __future__ import annotations
import logging
import mimetypes
from pathlib import PurePosixPath
from typing import Optional

from supabase import create_client, Client

from .config import settings

logger = logging.getLogger(__name__)


# Buckets nombrados para no esparcir strings mágicos
BUCKET_ADJUNTOS = "adjuntos"
BUCKET_LOGOS = "logos"

# Default TTL para signed URLs del bucket adjuntos
SIGNED_URL_TTL_SECONDS = 3600  # 1 hora


class StorageError(Exception):
    """Error genérico al interactuar con Supabase Storage."""


class _Storage:
    """Wrapper singleton de Supabase Storage."""

    _client: Optional[Client] = None

    @classmethod
    def client(cls) -> Client:
        """Cliente Supabase (lazy init para no romper imports si no hay key)."""
        if cls._client is None:
            if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
                raise StorageError(
                    "SUPABASE_URL y SUPABASE_KEY deben estar definidas en .env "
                    "para usar Supabase Storage."
                )
            cls._client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
            logger.info("Supabase Storage client inicializado")
        return cls._client

    # ─── Genéricos (subida / borrado / URL) ────────────────────────────────

    def upload(
        self,
        bucket: str,
        path: str,
        contenido: bytes,
        content_type: Optional[str] = None,
        upsert: bool = True,
    ) -> str:
        """Sube `contenido` al bucket en la ruta `path`. Devuelve `path` si OK."""
        if content_type is None:
            content_type = mimetypes.guess_type(path)[0] or "application/octet-stream"
        try:
            file_options = {
                "content-type": content_type,
                "upsert": "true" if upsert else "false",
            }
            self.client().storage.from_(bucket).upload(
                path=path,
                file=contenido,
                file_options=file_options,
            )
            logger.info("[storage] uploaded %s/%s (%d bytes)", bucket, path, len(contenido))
            return path
        except Exception as e:
            logger.exception("[storage] upload fallo: %s/%s", bucket, path)
            raise StorageError(f"Error al subir a {bucket}/{path}: {e}") from e

    def delete(self, bucket: str, path: str) -> None:
        """Borra un archivo del bucket. Idempotente: no falla si no existe."""
        try:
            self.client().storage.from_(bucket).remove([path])
            logger.info("[storage] deleted %s/%s", bucket, path)
        except Exception as e:
            # Supabase devuelve éxito incluso si el archivo no existe — esto solo captura errores reales
            logger.warning("[storage] delete %s/%s warning: %s", bucket, path, e)

    def public_url(self, bucket: str, path: str) -> str:
        """URL pública del archivo (solo válido si el bucket es público)."""
        return self.client().storage.from_(bucket).get_public_url(path)

    def download(self, bucket: str, path: str) -> bytes:
        """Descarga el archivo del bucket. Útil para el backup ZIP."""
        try:
            return self.client().storage.from_(bucket).download(path)
        except Exception as e:
            logger.exception("[storage] download fallo: %s/%s", bucket, path)
            raise StorageError(f"Error al descargar {bucket}/{path}: {e}") from e

    def list_files(self, bucket: str, prefix: str = "") -> list[dict]:
        """Lista archivos del bucket con prefijo. Devuelve lista de dicts con metadata."""
        try:
            return self.client().storage.from_(bucket).list(path=prefix)
        except Exception as e:
            logger.warning("[storage] list_files %s/%s fallo: %s", bucket, prefix, e)
            return []

    def signed_url(self, bucket: str, path: str, expires_in: int = SIGNED_URL_TTL_SECONDS) -> str:
        """URL firmada con expiración (para buckets privados como `adjuntos`)."""
        try:
            response = self.client().storage.from_(bucket).create_signed_url(path, expires_in)
            # supabase-py devuelve dict con keys 'signedURL' o 'signedUrl' según versión
            return response.get("signedURL") or response.get("signedUrl") or ""
        except Exception as e:
            logger.exception("[storage] signed_url fallo: %s/%s", bucket, path)
            raise StorageError(f"Error al firmar URL {bucket}/{path}: {e}") from e

    # ─── Helpers específicos del dominio ───────────────────────────────────

    @staticmethod
    def _ext(filename: str) -> str:
        """Extension en minúsculas con punto (`.pdf`, `.jpg`)."""
        ext = PurePosixPath(filename).suffix.lower()
        return ext or ".bin"

    @staticmethod
    def _path_adjunto_comprobante(empresa_id: str, comprobante_id: str, ext: str) -> str:
        return f"{empresa_id}/comprobantes/{comprobante_id}{ext}"

    @staticmethod
    def _path_adjunto_pago(empresa_id: str, pago_id: str, ext: str) -> str:
        return f"{empresa_id}/pagos/{pago_id}{ext}"

    @staticmethod
    def _path_logo(empresa_id: str, ext: str) -> str:
        return f"{empresa_id}/logo{ext}"

    # Adjunto de comprobante (factura escaneada)
    def upload_adjunto_comprobante(
        self, empresa_id: str, comprobante_id: str,
        contenido: bytes, filename: str,
    ) -> str:
        ext = self._ext(filename)
        path = self._path_adjunto_comprobante(empresa_id, comprobante_id, ext)
        return self.upload(BUCKET_ADJUNTOS, path, contenido)

    def delete_adjunto_comprobante(self, empresa_id: str, comprobante_id: str, ext: str) -> None:
        path = self._path_adjunto_comprobante(empresa_id, comprobante_id, ext)
        self.delete(BUCKET_ADJUNTOS, path)

    def url_adjunto_comprobante(self, empresa_id: str, comprobante_id: str, ext: str) -> str:
        path = self._path_adjunto_comprobante(empresa_id, comprobante_id, ext)
        return self.signed_url(BUCKET_ADJUNTOS, path)

    # Adjunto de pago (recibo)
    def upload_adjunto_pago(
        self, empresa_id: str, pago_id: str,
        contenido: bytes, filename: str,
    ) -> str:
        ext = self._ext(filename)
        path = self._path_adjunto_pago(empresa_id, pago_id, ext)
        return self.upload(BUCKET_ADJUNTOS, path, contenido)

    def delete_adjunto_pago(self, empresa_id: str, pago_id: str, ext: str) -> None:
        path = self._path_adjunto_pago(empresa_id, pago_id, ext)
        self.delete(BUCKET_ADJUNTOS, path)

    def url_adjunto_pago(self, empresa_id: str, pago_id: str, ext: str) -> str:
        path = self._path_adjunto_pago(empresa_id, pago_id, ext)
        return self.signed_url(BUCKET_ADJUNTOS, path)

    # Logo de empresa (público)
    def upload_logo(self, empresa_id: str, contenido: bytes, filename: str) -> tuple[str, str]:
        """Sube el logo. Devuelve (path, public_url)."""
        ext = self._ext(filename)
        path = self._path_logo(empresa_id, ext)
        self.upload(BUCKET_LOGOS, path, contenido)
        return path, self.public_url(BUCKET_LOGOS, path)

    def delete_logo(self, empresa_id: str, ext: str) -> None:
        path = self._path_logo(empresa_id, ext)
        self.delete(BUCKET_LOGOS, path)

    def url_logo(self, empresa_id: str, ext: str) -> str:
        return self.public_url(BUCKET_LOGOS, self._path_logo(empresa_id, ext))


# Singleton accesible como `from .storage import storage`
storage = _Storage()
