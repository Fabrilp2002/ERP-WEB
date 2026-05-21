-- =============================================================================
-- MIGRACIÓN: Fase H — Contabilidad Real
-- Libro Diario (asientos partida doble) + Libro Mayor + Estados Financieros
-- =============================================================================

-- ── Tabla de asientos contables (encabezado del libro diario) ─────────────────
CREATE TABLE IF NOT EXISTS asientos_contables (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    empresa_id      UUID NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    numero          INTEGER NOT NULL,                          -- numeracion secuencial por empresa
    fecha           DATE NOT NULL,
    concepto        VARCHAR(500) NOT NULL,
    comprobante_id  UUID REFERENCES comprobantes(id) ON DELETE SET NULL,
    pago_id         UUID REFERENCES pagos(id) ON DELETE SET NULL,
    tipo            VARCHAR(20) NOT NULL DEFAULT 'automatico'
                    CHECK (tipo IN ('automatico','manual','ajuste','cierre')),
    usuario_id      UUID REFERENCES usuarios(id),
    fecha_creacion  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (empresa_id, numero)
);

COMMENT ON TABLE asientos_contables IS 'Encabezado del Libro Diario. Cada fila es un asiento con sus partidas en detalle_asientos.';

-- ── Detalle de asientos (partidas individuales — partida doble) ────────────────
CREATE TABLE IF NOT EXISTS detalle_asientos (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    empresa_id  UUID NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    asiento_id  UUID NOT NULL REFERENCES asientos_contables(id) ON DELETE CASCADE,
    cuenta_id   UUID NOT NULL REFERENCES plan_cuentas(id),
    debe        DECIMAL(15,2) NOT NULL DEFAULT 0,
    haber       DECIMAL(15,2) NOT NULL DEFAULT 0,
    CONSTRAINT chk_detalle_positivos CHECK (debe >= 0 AND haber >= 0),
    CONSTRAINT chk_detalle_al_menos_uno CHECK (debe > 0 OR haber > 0)
);

COMMENT ON TABLE detalle_asientos IS 'Partidas del asiento. SUM(debe) = SUM(haber) siempre (partida doble).';

-- ── Índices ───────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_asientos_empresa_fecha ON asientos_contables(empresa_id, fecha DESC);
CREATE INDEX IF NOT EXISTS idx_asientos_comprobante   ON asientos_contables(comprobante_id);
CREATE INDEX IF NOT EXISTS idx_asientos_pago          ON asientos_contables(pago_id);
CREATE INDEX IF NOT EXISTS idx_detalle_asiento        ON detalle_asientos(asiento_id);
CREATE INDEX IF NOT EXISTS idx_detalle_cuenta         ON detalle_asientos(cuenta_id);

-- ── Cuentas faltantes para el juego completo de asientos automáticos ──────────
-- IVA Crédito Fiscal (activo corriente — aparece en compras)
INSERT INTO plan_cuentas (empresa_id, codigo, nombre, tipo, naturaleza, es_hoja)
SELECT e.id, '1.1.04', 'IVA Crédito Fiscal', 'activo', 'deudora', TRUE
FROM empresas e
WHERE NOT EXISTS (
    SELECT 1 FROM plan_cuentas pc
    WHERE pc.empresa_id = e.id AND pc.codigo = '1.1.04'
);

-- IVA Débito Fiscal (pasivo — detalle separado del IVA por Pagar para claridad)
INSERT INTO plan_cuentas (empresa_id, codigo, nombre, tipo, naturaleza, es_hoja)
SELECT e.id, '2.1.03', 'IVA Débito Fiscal', 'pasivo', 'acreedora', TRUE
FROM empresas e
WHERE NOT EXISTS (
    SELECT 1 FROM plan_cuentas pc
    WHERE pc.empresa_id = e.id AND pc.codigo = '2.1.03'
);

-- Anticipo de Clientes (pasivo — cuando se recibe pago sin factura)
INSERT INTO plan_cuentas (empresa_id, codigo, nombre, tipo, naturaleza, es_hoja)
SELECT e.id, '2.1.04', 'Anticipos de Clientes', 'pasivo', 'acreedora', TRUE
FROM empresas e
WHERE NOT EXISTS (
    SELECT 1 FROM plan_cuentas pc
    WHERE pc.empresa_id = e.id AND pc.codigo = '2.1.04'
);
