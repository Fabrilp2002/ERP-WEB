-- =============================================================================
-- MIGRATION: Fase v7.1 — Trazabilidad de lotes + Costo Promedio Ponderado
-- Fecha: 2026-05-17
-- Decisiones cerradas (ver docs/roadmap/PLAN_V7_LOTES_CPP.md):
--   - Stock existente → lote 'INICIAL' sin vencimiento, NO se reprocesa historia.
--   - Salida → FEFO (manejado en backend, no en este SQL).
--   - CPP → incremental desde la fecha de migración.
--   - Alerta default 30 días, configurable por empresa.
-- Idempotente: CREATE IF NOT EXISTS, columnas con IF NOT EXISTS.
-- =============================================================================

BEGIN;

-- 1. Tabla inventario_lotes ---------------------------------------------------
CREATE TABLE IF NOT EXISTS inventario_lotes (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    empresa_id          UUID            NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    inventario_id       UUID            NOT NULL REFERENCES inventario(id) ON DELETE CASCADE,
    numero_lote         VARCHAR(50)     NOT NULL,
    cantidad            DECIMAL(15,4)   NOT NULL CHECK (cantidad >= 0),
    cantidad_inicial    DECIMAL(15,4)   NOT NULL CHECK (cantidad_inicial >= 0),
    costo_unitario      DECIMAL(15,2)   NOT NULL DEFAULT 0,
    fecha_ingreso       DATE            NOT NULL DEFAULT CURRENT_DATE,
    fecha_vencimiento   DATE            NULL,
    proveedor_id        UUID            NULL REFERENCES proveedores(id) ON DELETE SET NULL,
    comprobante_id      UUID            NULL REFERENCES comprobantes(id) ON DELETE SET NULL,
    notas               TEXT,
    fecha_creacion      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    UNIQUE (empresa_id, inventario_id, numero_lote)
);

CREATE INDEX IF NOT EXISTS idx_lotes_fefo
    ON inventario_lotes (empresa_id, inventario_id, fecha_vencimiento NULLS LAST, fecha_ingreso);

CREATE INDEX IF NOT EXISTS idx_lotes_vencimiento_activo
    ON inventario_lotes (empresa_id, fecha_vencimiento)
    WHERE cantidad > 0 AND fecha_vencimiento IS NOT NULL;

COMMENT ON TABLE  inventario_lotes IS 'Lotes individuales de stock con vencimiento opcional. v7.1.';
COMMENT ON COLUMN inventario_lotes.cantidad_inicial IS 'Cantidad con la que entró el lote — no cambia. cantidad se decrementa con ventas.';
COMMENT ON COLUMN inventario_lotes.numero_lote IS 'Identificador del lote. INICIAL = creado por migración para stock pre-existente.';

-- 2. Tabla inventario_movimientos (kardex) ------------------------------------
CREATE TABLE IF NOT EXISTS inventario_movimientos (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    empresa_id          UUID            NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    inventario_id       UUID            NOT NULL REFERENCES inventario(id) ON DELETE CASCADE,
    lote_id             UUID            NULL REFERENCES inventario_lotes(id) ON DELETE SET NULL,
    tipo                VARCHAR(20)     NOT NULL
                        CHECK (tipo IN ('ingreso','salida','ajuste','merma')),
    cantidad            DECIMAL(15,4)   NOT NULL CHECK (cantidad > 0),
    costo_unitario      DECIMAL(15,2)   NOT NULL DEFAULT 0,
    cpp_resultante      DECIMAL(15,2)   NOT NULL DEFAULT 0,
    fecha               DATE            NOT NULL DEFAULT CURRENT_DATE,
    comprobante_id      UUID            NULL REFERENCES comprobantes(id) ON DELETE SET NULL,
    usuario_id          UUID            NULL REFERENCES usuarios(id) ON DELETE SET NULL,
    notas               TEXT,
    fecha_creacion      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_kardex_item_fecha
    ON inventario_movimientos (empresa_id, inventario_id, fecha DESC, fecha_creacion DESC);

COMMENT ON TABLE inventario_movimientos IS
    'Kardex append-only de movimientos de stock. Base para valuación y trazabilidad.';

-- 3. Columna empresas.dias_alerta_vencimiento ---------------------------------
ALTER TABLE empresas
    ADD COLUMN IF NOT EXISTS dias_alerta_vencimiento INTEGER NOT NULL DEFAULT 30;

COMMENT ON COLUMN empresas.dias_alerta_vencimiento IS
    'v7.1 — Días de anticipación para alerta de lotes próximos a vencer.';

-- 4. RLS para las tablas nuevas (consistente con migración previa) ------------
DO $$
BEGIN
  EXECUTE 'ALTER TABLE inventario_lotes ENABLE ROW LEVEL SECURITY';
  EXECUTE 'DROP POLICY IF EXISTS tenant_isolation ON inventario_lotes';
  EXECUTE 'CREATE POLICY tenant_isolation ON inventario_lotes '
          'USING (empresa_id = current_setting(''app.current_empresa'', true)::uuid) '
          'WITH CHECK (empresa_id = current_setting(''app.current_empresa'', true)::uuid)';

  EXECUTE 'ALTER TABLE inventario_movimientos ENABLE ROW LEVEL SECURITY';
  EXECUTE 'DROP POLICY IF EXISTS tenant_isolation ON inventario_movimientos';
  EXECUTE 'CREATE POLICY tenant_isolation ON inventario_movimientos '
          'USING (empresa_id = current_setting(''app.current_empresa'', true)::uuid) '
          'WITH CHECK (empresa_id = current_setting(''app.current_empresa'', true)::uuid)';
END $$;

-- 5. Seed lote INICIAL para stock existente -----------------------------------
-- Crea un lote único por cada item con cantidad_actual > 0.
-- Idempotente: si el lote INICIAL ya existe para un item, ON CONFLICT no hace nada.
INSERT INTO inventario_lotes (
    empresa_id, inventario_id, numero_lote, cantidad, cantidad_inicial,
    costo_unitario, fecha_ingreso, fecha_vencimiento, notas
)
SELECT
    i.empresa_id,
    i.id                         AS inventario_id,
    'INICIAL'                    AS numero_lote,
    i.cantidad_actual            AS cantidad,
    i.cantidad_actual            AS cantidad_inicial,
    i.costo_unitario             AS costo_unitario,
    COALESCE(i.fecha_creacion::date, CURRENT_DATE) AS fecha_ingreso,
    NULL                         AS fecha_vencimiento,
    'Lote creado por migración v7.1 — stock pre-existente' AS notas
FROM inventario i
WHERE i.activo = TRUE
  AND i.cantidad_actual > 0
ON CONFLICT (empresa_id, inventario_id, numero_lote) DO NOTHING;

-- 6. Seed kardex inicial (un movimiento de ingreso por cada lote INICIAL) -----
INSERT INTO inventario_movimientos (
    empresa_id, inventario_id, lote_id, tipo, cantidad, costo_unitario,
    cpp_resultante, fecha, notas
)
SELECT
    l.empresa_id,
    l.inventario_id,
    l.id                       AS lote_id,
    'ingreso'                  AS tipo,
    l.cantidad_inicial         AS cantidad,
    l.costo_unitario           AS costo_unitario,
    i.costo_unitario           AS cpp_resultante,
    l.fecha_ingreso            AS fecha,
    'Migración v7.1 — apertura de kardex' AS notas
FROM inventario_lotes l
JOIN inventario i ON i.id = l.inventario_id
WHERE l.numero_lote = 'INICIAL'
  AND NOT EXISTS (
    SELECT 1 FROM inventario_movimientos m
    WHERE m.lote_id = l.id AND m.tipo = 'ingreso'
  );

COMMIT;

-- Verificación post-aplicación
-- SELECT COUNT(*) FROM inventario_lotes WHERE numero_lote = 'INICIAL';
-- SELECT COUNT(*) FROM inventario_movimientos;
-- SELECT i.descripcion, l.cantidad, l.costo_unitario FROM inventario i
--   JOIN inventario_lotes l ON l.inventario_id = i.id
--   WHERE l.numero_lote = 'INICIAL' LIMIT 5;
