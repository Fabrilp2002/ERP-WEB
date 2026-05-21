"""
Bootstrap inicial de la BD cloud — crea empresa + admin.

Uso (post-deploy, una sola vez):

    python scripts/bootstrap_admin.py \
        --email admin@miempresa.com \
        --password "TuPassword123" \
        --nombre "Administrador"

Si ya existe un admin con ese email, actualiza su password (UPSERT).
"""
from __future__ import annotations
import argparse
import asyncio
import os
import sys
from pathlib import Path

# Permitir importar `backend.*` cuando se ejecuta desde la raíz del repo
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import bcrypt
import asyncpg


async def bootstrap(database_url: str, email: str, password: str,
                    nombre: str, empresa_nombre: str | None) -> None:
    """Crea o actualiza la empresa inicial + admin."""
    # asyncpg necesita el DSN sin el prefijo +asyncpg
    dsn = database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    conn = await asyncpg.connect(dsn)
    try:
        # Verificar que las tablas existan (las migraciones tienen que haber corrido)
        existe = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'empresas'
            )
        """)
        if not existe:
            raise RuntimeError(
                "La tabla 'empresas' no existe. Aplicá las migraciones primero "
                "(ver db/esquema_bd.sql + db/migrations/*.sql)."
            )

        # Empresa: usar la primera o crear una nueva
        empresa_id = await conn.fetchval(
            "SELECT id FROM empresas ORDER BY fecha_creacion ASC LIMIT 1"
        )
        if empresa_id is None:
            empresa_nombre = empresa_nombre or "Mi Empresa"
            print(f"-> creando empresa: {empresa_nombre}")
            empresa_id = await conn.fetchval(
                "INSERT INTO empresas (nombre) VALUES ($1) RETURNING id",
                empresa_nombre,
            )
        elif empresa_nombre:
            print(f"-> actualizando nombre de empresa a: {empresa_nombre}")
            await conn.execute(
                "UPDATE empresas SET nombre = $1 WHERE id = $2",
                empresa_nombre, empresa_id,
            )

        # Rol admin
        rol_admin = await conn.fetchval(
            "SELECT id FROM roles_usuario WHERE nombre = 'admin'"
        )
        if rol_admin is None:
            raise RuntimeError(
                "No existe el rol 'admin' en roles_usuario. "
                "El esquema base no se aplicó correctamente."
            )

        # Hash bcrypt 12 rounds
        password_hash = bcrypt.hashpw(
            password.encode("utf-8"), bcrypt.gensalt(12)
        ).decode("utf-8")

        # UPSERT del admin
        await conn.execute("""
            INSERT INTO usuarios (empresa_id, nombre, email, password_hash, id_rol, activo)
            VALUES ($1, $2, $3, $4, $5, TRUE)
            ON CONFLICT (empresa_id, email) DO UPDATE
            SET nombre = EXCLUDED.nombre,
                password_hash = EXCLUDED.password_hash,
                id_rol = EXCLUDED.id_rol,
                activo = TRUE
        """, empresa_id, nombre, email.lower().strip(), password_hash, rol_admin)

        print(f"[OK] admin listo: {email} / empresa_id={empresa_id}")
    finally:
        await conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap admin del ERP_Web")
    parser.add_argument("--email", required=True, help="Email del admin")
    parser.add_argument("--password", required=True, help="Password (mín 8 chars)")
    parser.add_argument("--nombre", default="Administrador", help="Nombre para mostrar")
    parser.add_argument("--empresa", default=None,
                        help="Nombre de la empresa. Si ya existe una empresa y se omite, no la modifica.")
    parser.add_argument("--database-url", default=None,
                        help="Override de DATABASE_URL (sino lee de .env)")
    args = parser.parse_args()

    if len(args.password) < 8:
        sys.exit("ERROR: la password debe tener al menos 8 caracteres.")
    if "@" not in args.email:
        sys.exit("ERROR: --email debe ser un email válido.")

    # Cargar DATABASE_URL desde .env si no se pasa explícito
    db_url = args.database_url or os.environ.get("DATABASE_URL")
    if not db_url:
        env_file = Path(__file__).resolve().parent.parent / "backend" / ".env"
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                if line.startswith("DATABASE_URL="):
                    db_url = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    if not db_url:
        sys.exit("ERROR: DATABASE_URL no definido. Pasalo con --database-url o en .env.")

    print(f"-> conectando a: {db_url.split('@')[-1] if '@' in db_url else db_url}")
    asyncio.run(bootstrap(
        database_url=db_url,
        email=args.email,
        password=args.password,
        nombre=args.nombre,
        empresa_nombre=args.empresa,
    ))


if __name__ == "__main__":
    main()
