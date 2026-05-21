-- Migración idempotente: agregar apellido a usuarios.
-- Fecha: 2026-04-18
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS apellido VARCHAR(150);

-- Backfill: si el nombre tiene espacio, usar última palabra como apellido (opcional).
UPDATE usuarios
SET apellido = CASE
    WHEN position(' ' IN nombre) > 0 THEN split_part(nombre, ' ', 2)
    ELSE NULL
END
WHERE apellido IS NULL;
