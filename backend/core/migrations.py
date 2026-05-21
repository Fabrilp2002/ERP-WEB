"""
Auto-aplicación del schema al arrancar el backend (cloud).

Comportamiento:
  - Si la BD está vacía → ejecuta `db/esquema_bd.sql` y crea tabla `schema_migrations`.
  - Aplica migrations/*.sql en orden cronológico (por nombre de archivo).
  - Marca cada migración aplicada en `schema_migrations` para no re-aplicarla.

El bootstrap del usuario admin **NO** ocurre acá automáticamente. Para crear el
admin inicial, usar el script `scripts/bootstrap_admin.py` post-deploy.
"""
from __future__ import annotations
import asyncio
import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def _db_root() -> Path:
    """Localiza la carpeta `db/` del proyecto (en repo o en deployment)."""
    # En el repo: backend/core/migrations.py → ../../db
    return Path(__file__).resolve().parent.parent.parent / "db"


# ─── PostgreSQL / Supabase ───────────────────────────────────────────────────

async def _aplicar_schema_postgres(database_url: str) -> None:
    """Aplica esquema base + migraciones incrementales contra Postgres."""
    import asyncpg

    db_dir = _db_root()
    schema_file = db_dir / "esquema_bd.sql"
    mig_dir = db_dir / "migrations"

    # asyncpg necesita el DSN sin el prefijo `+asyncpg`
    dsn = database_url.replace("postgresql+asyncpg://", "postgresql://", 1)

    logger.info("[migrations] conectando a Postgres…")
    conn = await asyncpg.connect(dsn)
    try:
        # Tabla de control
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                nombre      TEXT PRIMARY KEY,
                aplicada_en TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)

        # Esquema base — solo si la BD está vacía
        existe_empresas = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'empresas'
            )
        """)
        if not existe_empresas:
            if not schema_file.exists():
                raise FileNotFoundError(f"No se encontró {schema_file}")
            logger.info("[migrations] aplicando esquema_bd.sql")
            sql = schema_file.read_text(encoding="utf-8")
            await conn.execute(sql)
            await conn.execute(
                "INSERT INTO schema_migrations(nombre) VALUES($1) ON CONFLICT DO NOTHING",
                "00_esquema_bd.sql",
            )
            logger.info("[migrations] esquema base aplicado OK")
        else:
            logger.info("[migrations] esquema ya existe, salteando esquema_bd.sql")

        # Migraciones incrementales
        if mig_dir.exists():
            aplicadas = {
                r["nombre"]
                for r in await conn.fetch("SELECT nombre FROM schema_migrations")
            }
            archivos = sorted(mig_dir.glob("*.sql"))
            nuevas = [f for f in archivos if f.name not in aplicadas]
            if nuevas:
                logger.info("[migrations] aplicando %d migraciones nuevas", len(nuevas))
                for f in nuevas:
                    logger.info("[migrations]   → %s", f.name)
                    sql = f.read_text(encoding="utf-8")
                    async with conn.transaction():
                        await conn.execute(sql)
                        await conn.execute(
                            "INSERT INTO schema_migrations(nombre) VALUES($1)",
                            f.name,
                        )
                logger.info("[migrations] todas las migraciones aplicadas OK")
            else:
                logger.info("[migrations] no hay migraciones pendientes")
    finally:
        await conn.close()


# ─── Entry point sync para uvicorn / pre-arranque ────────────────────────────

def aplicar_migraciones_sync(database_url: str) -> None:
    """
    Aplica migraciones de forma síncrona. Llamado opcionalmente desde main.py
    durante el startup del backend, o desde scripts/bootstrap_admin.py.

    Si la conexión falla o las migraciones rompen, propaga la excepción para
    que el deploy falle visiblemente (mejor que arrancar con BD inconsistente).
    """
    if not database_url.startswith(("postgresql://", "postgresql+asyncpg://")):
        raise ValueError(
            f"DATABASE_URL inválido para cloud: {database_url[:30]}... "
            "se espera postgresql:// o postgresql+asyncpg://"
        )
    try:
        asyncio.run(_aplicar_schema_postgres(database_url))
    except Exception as e:
        logger.error("[migrations] FALLO: %s", e)
        if os.environ.get("ERP_MIGRATIONS_STRICT", "1") == "1":
            raise


# ─── Compatibilidad con código antiguo ───────────────────────────────────────

async def aplicar_migraciones(database_url: str) -> None:
    """Versión async (por si algún router viejo la importa)."""
    await _aplicar_schema_postgres(database_url)
