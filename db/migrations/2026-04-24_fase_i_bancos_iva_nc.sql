-- =============================================================================
-- MIGRACIÓN FASE I — Bancos + IVA + Notas de Crédito vinculadas
-- =============================================================================

-- I.4 — Columna comprobante_origen_id en comprobantes (para NC/ND vinculadas)
ALTER TABLE comprobantes
    ADD COLUMN IF NOT EXISTS comprobante_origen_id UUID REFERENCES comprobantes(id);

COMMENT ON COLUMN comprobantes.comprobante_origen_id
    IS 'Factura origen que esta NC o ND está compensando. Nulable para comprobantes normales.';

CREATE INDEX IF NOT EXISTS idx_comprobantes_origen ON comprobantes (comprobante_origen_id)
    WHERE comprobante_origen_id IS NOT NULL;

-- I.1 — Asegurar que las tablas de banco tienen índices correctos
CREATE INDEX IF NOT EXISTS idx_cuentas_banco_empresa ON cuentas_banco (empresa_id);
CREATE INDEX IF NOT EXISTS idx_movimientos_banco_empresa ON movimientos_banco (empresa_id);

-- I.2 — Índice para reportes IVA por fecha (mejorar performance de queries mensuales)
CREATE INDEX IF NOT EXISTS idx_comprobantes_fecha ON comprobantes (empresa_id, fecha_emision);
CREATE INDEX IF NOT EXISTS idx_comprobantes_tipo_fecha ON comprobantes (empresa_id, cliente_id, proveedor_id, fecha_emision);
