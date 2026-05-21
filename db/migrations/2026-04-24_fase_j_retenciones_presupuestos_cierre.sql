-- =============================================================================
-- MIGRACIÓN FASE J — Retenciones + Presupuestos + Cierre Contable
-- =============================================================================

-- J.1 Retenciones de IVA y Renta (Paraguay)
CREATE TABLE IF NOT EXISTS retenciones (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    empresa_id          UUID NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    comprobante_id      UUID REFERENCES comprobantes(id) ON DELETE SET NULL,
    tipo                VARCHAR(20) NOT NULL CHECK (tipo IN ('iva','renta','ambos')),
    porcentaje          DECIMAL(5,2) NOT NULL CHECK (porcentaje > 0 AND porcentaje <= 100),
    monto_base          DECIMAL(15,2) NOT NULL CHECK (monto_base >= 0),
    monto_retenido      DECIMAL(15,2) NOT NULL CHECK (monto_retenido >= 0),
    numero_certificado  VARCHAR(50),
    fecha               DATE NOT NULL,
    proveedor_id        UUID REFERENCES proveedores(id) ON DELETE SET NULL,
    notas               VARCHAR(500),
    usuario_id          UUID REFERENCES usuarios(id),
    fecha_creacion      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_retenciones_empresa ON retenciones (empresa_id, fecha);
CREATE INDEX IF NOT EXISTS idx_retenciones_comprobante ON retenciones (comprobante_id);

-- J.3 Presupuestos
CREATE TABLE IF NOT EXISTS presupuestos (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    empresa_id          UUID NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    nombre              VARCHAR(200) NOT NULL,
    periodo_inicio      DATE NOT NULL,
    periodo_fin         DATE NOT NULL,
    estado              VARCHAR(20) NOT NULL DEFAULT 'borrador'
                        CHECK (estado IN ('borrador','activo','cerrado')),
    notas               VARCHAR(1000),
    usuario_id          UUID REFERENCES usuarios(id),
    fecha_creacion      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (periodo_fin >= periodo_inicio)
);

CREATE TABLE IF NOT EXISTS detalle_presupuesto (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    empresa_id          UUID NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    presupuesto_id      UUID NOT NULL REFERENCES presupuestos(id) ON DELETE CASCADE,
    cuenta_id           UUID NOT NULL REFERENCES plan_cuentas(id),
    monto_presupuestado DECIMAL(15,2) NOT NULL CHECK (monto_presupuestado >= 0),
    notas               VARCHAR(300)
);
CREATE INDEX IF NOT EXISTS idx_presupuesto_empresa ON presupuestos (empresa_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_presupuesto_cuenta ON detalle_presupuesto (presupuesto_id, cuenta_id);

-- J.4 Periodos Contables (Cierre)
CREATE TABLE IF NOT EXISTS periodos_contables (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    empresa_id          UUID NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    periodo             CHAR(7) NOT NULL,          -- 'YYYY-MM'
    estado              VARCHAR(20) NOT NULL DEFAULT 'abierto'
                        CHECK (estado IN ('abierto','cerrado')),
    fecha_cierre        TIMESTAMPTZ,
    usuario_cierre_id   UUID REFERENCES usuarios(id),
    notas               VARCHAR(500),
    fecha_creacion      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (empresa_id, periodo)
);
CREATE INDEX IF NOT EXISTS idx_periodos_empresa ON periodos_contables (empresa_id, periodo);
