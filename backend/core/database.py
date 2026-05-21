"""
Conexión async a Postgres (Supabase) para el backend cloud.

Usar puerto 5432 (Session mode). Si en algún momento se mueve a 6543
(Transaction mode con pgBouncer), descomentar el bloque marcado más abajo
para evitar `DuplicatePreparedStatementError` con asyncpg.
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
# from sqlalchemy.pool import NullPool  # descomentar si se usa puerto 6543

from .config import settings


# ─── Engine ──────────────────────────────────────────────────────────────────
# Configuración estándar para Supabase puerto 5432 (Session mode).
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,    # detecta conexiones muertas antes de usarlas
    pool_size=5,
    max_overflow=10,
    pool_recycle=1800,     # recicla conexiones cada 30 min (Supabase mata conexiones idle)
)

# ─── Alternativa para puerto 6543 (Transaction mode con pgBouncer) ──────────
# Descomentar y reemplazar el `engine = ...` de arriba si se mueve a 6543:
#
# engine = create_async_engine(
#     settings.DATABASE_URL,
#     echo=settings.DEBUG,
#     poolclass=NullPool,   # pgBouncer hace su propio pooling
#     connect_args={
#         "statement_cache_size": 0,           # asyncpg + pgBouncer = no prepared
#         "prepared_statement_cache_size": 0,
#     },
# )


AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db():
    """Dependency de FastAPI — provee sesión de BD por request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
