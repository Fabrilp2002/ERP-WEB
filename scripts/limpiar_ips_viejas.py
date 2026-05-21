"""Ejecuta la retención de privacidad de auditoría (IPs/User-Agent > 90 días).

Pensado para Render Cron o ejecución manual:
    python scripts/limpiar_ips_viejas.py
"""
from __future__ import annotations

import asyncio
import os
import sys

import asyncpg


async def main() -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        sys.exit("ERROR: DATABASE_URL no definido")
    dsn = database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    conn = await asyncpg.connect(dsn)
    try:
        await conn.execute("SELECT limpiar_ips_viejas()")
        print("[OK] auditoria_log: IP/User-Agent mayores a 90 dias limpiados")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
