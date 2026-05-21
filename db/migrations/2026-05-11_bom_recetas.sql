-- =============================================================================
-- MIGRATION: Bill of Materials (BOM) — Recetas de productos
-- Fecha: 2026-05-11
-- Proposito: Permitir que cada producto terminado tenga una "receta" que liste
-- sus insumos y cantidades. Habilita calculo de costo real por unidad,
-- planeacion de produccion y prediccion de quiebre de stock.
-- =============================================================================

-- 1. Distinguir productos terminados de insumos en la tabla inventario
ALTER TABLE inventario
  ADD COLUMN IF NOT EXISTS es_producto_terminado BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS precio_venta DECIMAL(15,2) NULL,
  ADD COLUMN IF NOT EXISTS notas_produccion TEXT NULL;

COMMENT ON COLUMN inventario.es_producto_terminado IS
  'TRUE = producto terminado (puede tener receta). FALSE = insumo/materia prima.';
COMMENT ON COLUMN inventario.precio_venta IS
  'Precio de venta sugerido por unidad (opcional). Usado para calcular margen.';

-- 2. Tabla de recetas — UNA cabecera por receta de producto
CREATE TABLE IF NOT EXISTS recetas (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    empresa_id          UUID            NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    producto_id         UUID            NOT NULL REFERENCES inventario(id) ON DELETE CASCADE,
    nombre              VARCHAR(200)    NOT NULL,
    version             VARCHAR(50)     NOT NULL DEFAULT 'v1',
    rendimiento         DECIMAL(15,4)   NOT NULL DEFAULT 1,    -- cuantas unidades produce 1 batch
    unidad_rendimiento  VARCHAR(20)     NOT NULL DEFAULT 'unidad',
    activa              BOOLEAN         NOT NULL DEFAULT TRUE,
    notas               TEXT,
    usuario_creacion_id UUID            REFERENCES usuarios(id),
    fecha_creacion      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    fecha_modificacion  TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE recetas IS
  'Receta o Bill of Materials (BOM): lista de insumos que componen un producto terminado.';
COMMENT ON COLUMN recetas.rendimiento IS
  'Cantidad de unidades del producto que se obtienen al ejecutar 1 vez esta receta.';

-- Solo puede haber una receta ACTIVA por producto (las anteriores quedan archivadas)
CREATE UNIQUE INDEX IF NOT EXISTS idx_recetas_producto_activa
  ON recetas (empresa_id, producto_id)
  WHERE activa = TRUE;

CREATE INDEX IF NOT EXISTS idx_recetas_empresa ON recetas (empresa_id);
CREATE INDEX IF NOT EXISTS idx_recetas_producto ON recetas (producto_id);

-- 3. Items de cada receta — los insumos con su cantidad
CREATE TABLE IF NOT EXISTS receta_items (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    receta_id           UUID            NOT NULL REFERENCES recetas(id) ON DELETE CASCADE,
    insumo_id           UUID            NOT NULL REFERENCES inventario(id),
    cantidad            DECIMAL(15,4)   NOT NULL,
    unidad_medida       VARCHAR(20)     NOT NULL,
    orden               INTEGER         NOT NULL DEFAULT 0,
    es_critico          BOOLEAN         NOT NULL DEFAULT FALSE,  -- el que si falta detiene la produccion
    notas               TEXT,
    CONSTRAINT cantidad_positiva CHECK (cantidad > 0)
);

CREATE INDEX IF NOT EXISTS idx_receta_items_receta ON receta_items (receta_id, orden);
CREATE INDEX IF NOT EXISTS idx_receta_items_insumo ON receta_items (insumo_id);

-- 4. Tabla de lotes de produccion (planificacion de produccion futura)
CREATE TABLE IF NOT EXISTS lotes_produccion (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    empresa_id          UUID            NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    receta_id           UUID            NOT NULL REFERENCES recetas(id),
    numero_lote         VARCHAR(50)     NOT NULL,
    cantidad_planificada DECIMAL(15,4)  NOT NULL,
    cantidad_producida  DECIMAL(15,4)   NOT NULL DEFAULT 0,
    estado              VARCHAR(20)     NOT NULL DEFAULT 'planificado'
                        CHECK (estado IN ('planificado','en_proceso','completado','cancelado')),
    fecha_planificada   DATE            NOT NULL,
    fecha_completado    DATE,
    fecha_vencimiento   DATE,                            -- vencimiento del producto terminado
    costo_total         DECIMAL(15,2),                   -- calculado al cerrar el lote
    notas               TEXT,
    usuario_id          UUID            REFERENCES usuarios(id),
    fecha_creacion      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    UNIQUE (empresa_id, numero_lote)
);

CREATE INDEX IF NOT EXISTS idx_lotes_empresa_estado ON lotes_produccion (empresa_id, estado);
CREATE INDEX IF NOT EXISTS idx_lotes_fecha ON lotes_produccion (fecha_planificada);

COMMENT ON TABLE lotes_produccion IS
  'Lotes planificados o en ejecucion. Al completarse, descuenta insumos y suma producto terminado.';

-- 5. Vista util: receta enriquecida con costo total y stock de insumos
CREATE OR REPLACE VIEW v_recetas_detalle AS
SELECT
    r.id                                                     AS receta_id,
    r.empresa_id,
    r.producto_id,
    p.descripcion                                            AS producto_nombre,
    p.codigo                                                 AS producto_codigo,
    p.precio_venta                                           AS producto_precio_venta,
    r.nombre,
    r.version,
    r.rendimiento,
    r.unidad_rendimiento,
    r.activa,
    -- Costo total de la receta = suma de (cantidad * costo unitario del insumo)
    COALESCE(SUM(ri.cantidad * i.costo_unitario), 0)         AS costo_total_receta,
    -- Costo unitario = costo total / rendimiento
    CASE WHEN r.rendimiento > 0
        THEN COALESCE(SUM(ri.cantidad * i.costo_unitario), 0) / r.rendimiento
        ELSE 0
    END                                                       AS costo_unitario,
    COUNT(ri.id)                                             AS cantidad_items
FROM recetas r
JOIN inventario p ON p.id = r.producto_id
LEFT JOIN receta_items ri ON ri.receta_id = r.id
LEFT JOIN inventario i ON i.id = ri.insumo_id
GROUP BY r.id, r.empresa_id, r.producto_id, p.descripcion,
         p.codigo, p.precio_venta, r.nombre, r.version,
         r.rendimiento, r.unidad_rendimiento, r.activa;

COMMENT ON VIEW v_recetas_detalle IS
  'Receta enriquecida con costo total y costo unitario calculados en tiempo real.';

-- 6. Vista util: capacidad de produccion (cuantas unidades puedo producir HOY)
CREATE OR REPLACE VIEW v_capacidad_produccion AS
WITH lim AS (
    SELECT
        r.id            AS receta_id,
        r.producto_id,
        r.empresa_id,
        ri.insumo_id,
        i.descripcion   AS insumo_nombre,
        i.cantidad_actual AS stock_actual,
        ri.cantidad     AS cantidad_requerida,
        -- Cuantos batches puedo hacer con el stock de este insumo
        CASE WHEN ri.cantidad > 0
            THEN FLOOR(i.cantidad_actual / ri.cantidad)
            ELSE 0
        END             AS batches_posibles_por_insumo
    FROM recetas r
    JOIN receta_items ri ON ri.receta_id = r.id
    JOIN inventario i ON i.id = ri.insumo_id
    WHERE r.activa = TRUE
)
SELECT
    receta_id,
    producto_id,
    empresa_id,
    MIN(batches_posibles_por_insumo)                AS batches_posibles,
    -- Insumo cuello de botella
    (SELECT insumo_nombre FROM lim l2
     WHERE l2.receta_id = lim.receta_id
     ORDER BY batches_posibles_por_insumo ASC LIMIT 1) AS insumo_limitante
FROM lim
GROUP BY receta_id, producto_id, empresa_id;

COMMENT ON VIEW v_capacidad_produccion IS
  'Cuantos batches de cada receta se pueden producir con el stock actual de insumos.';
