-- =============================================================================
-- ESQUEMA SQL v4.0 — Sistema ERP Universal
-- Multi-tenant | UUID | DECIMAL(15,2) | Roles admin/operador/viewer
-- Empresa paraguaya — procesamiento de facturas externas (no emisión propia)
-- Campos de expansión futura marcados como NULLABLE (ej: timbrado)
-- =============================================================================

-- =============================================================================
-- 0. EXTENSIÓN UUID (PostgreSQL)
-- =============================================================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";


-- =============================================================================
-- 1. EMPRESAS (raíz del multi-tenant)
-- =============================================================================
CREATE TABLE empresas (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nombre              VARCHAR(200)    NOT NULL,
    ruc                 VARCHAR(50),                    -- RUC paraguayo (futuro: validación DNIT)
    direccion           VARCHAR(300),
    telefono            VARCHAR(50),
    email               VARCHAR(150),
    moneda_principal    VARCHAR(10)     NOT NULL DEFAULT 'PYG',  -- Guaraní paraguayo
    activa              BOOLEAN         NOT NULL DEFAULT TRUE,
    fecha_creacion      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE empresas IS 'Raíz del modelo multi-tenant. Cada empresa es un tenant aislado por RLS.';


-- =============================================================================
-- 2. ROLES Y USUARIOS
-- =============================================================================
CREATE TABLE roles_usuario (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nombre              VARCHAR(50)     NOT NULL UNIQUE,   -- 'admin', 'operador', 'viewer'
    descripcion         VARCHAR(200),
    puede_escribir      BOOLEAN         NOT NULL DEFAULT FALSE
);

INSERT INTO roles_usuario (nombre, descripcion, puede_escribir) VALUES
    ('admin',    'Acceso completo: configuración, CRUD, reportes', TRUE),
    ('operador', 'Carga de comprobantes, inventario y cuentas corrientes', TRUE),
    ('viewer',   'Solo lectura: dashboards y reportes remotos', FALSE);

CREATE TABLE usuarios (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    empresa_id          UUID            NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    nombre              VARCHAR(150)    NOT NULL,
    email               VARCHAR(150)    NOT NULL,
    password_hash       VARCHAR(255)    NOT NULL,           -- bcrypt, nunca texto plano
    id_rol              UUID            NOT NULL REFERENCES roles_usuario(id),
    activo              BOOLEAN         NOT NULL DEFAULT TRUE,
    ultimo_acceso       TIMESTAMPTZ,
    fecha_creacion      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    UNIQUE (empresa_id, email)                              -- email único por empresa
);

COMMENT ON COLUMN usuarios.password_hash IS 'Hash bcrypt. Nunca almacenar texto plano.';


-- =============================================================================
-- 3. CLIENTES Y PROVEEDORES
-- =============================================================================
CREATE TABLE clientes (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    empresa_id          UUID            NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    nombre              VARCHAR(200)    NOT NULL,
    ruc                 VARCHAR(50),
    telefono            VARCHAR(50),
    email               VARCHAR(150),
    direccion           VARCHAR(300),
    notas               TEXT,
    activo              BOOLEAN         NOT NULL DEFAULT TRUE,
    fecha_creacion      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE TABLE proveedores (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    empresa_id          UUID            NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    nombre              VARCHAR(200)    NOT NULL,
    ruc                 VARCHAR(50),
    telefono            VARCHAR(50),
    email               VARCHAR(150),
    direccion           VARCHAR(300),
    notas               TEXT,
    activo              BOOLEAN         NOT NULL DEFAULT TRUE,
    fecha_creacion      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);


-- =============================================================================
-- 4. PLAN DE CUENTAS CONTABLE
-- =============================================================================
CREATE TABLE plan_cuentas (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    empresa_id          UUID            NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    codigo              VARCHAR(20)     NOT NULL,           -- Ej: '1.1.01', '4.2.03'
    nombre              VARCHAR(200)    NOT NULL,
    tipo                VARCHAR(30)     NOT NULL            -- 'activo','pasivo','patrimonio','ingreso','egreso'
                        CHECK (tipo IN ('activo','pasivo','patrimonio','ingreso','egreso','resultado')),
    naturaleza          VARCHAR(10)     NOT NULL DEFAULT 'deudora'
                        CHECK (naturaleza IN ('deudora','acreedora')),
    cuenta_padre_id     UUID            REFERENCES plan_cuentas(id),  -- árbol jerárquico
    es_hoja             BOOLEAN         NOT NULL DEFAULT TRUE,         -- solo las hojas reciben movimientos
    activa              BOOLEAN         NOT NULL DEFAULT TRUE,
    UNIQUE (empresa_id, codigo)
);

COMMENT ON TABLE plan_cuentas IS 'Plan de cuentas parametrizable por empresa. Estructura árbol con cuenta_padre_id.';


-- =============================================================================
-- 5. INVENTARIO
-- =============================================================================
CREATE TABLE categorias_inventario (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    empresa_id          UUID            NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    nombre              VARCHAR(100)    NOT NULL,            -- 'Materia Prima', 'Insumos', 'Producto Terminado'
    descripcion         VARCHAR(200)
);

CREATE TABLE inventario (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    empresa_id          UUID            NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    categoria_id        UUID            REFERENCES categorias_inventario(id),
    codigo              VARCHAR(50),
    descripcion         VARCHAR(300)    NOT NULL,
    unidad_medida       VARCHAR(20)                          -- 'kg', 'lt', 'unidad', 'm2'
                        CHECK (unidad_medida IN ('kg','lt','unidad','m2','m3','caja','bolsa','otro')),
    cantidad_actual     DECIMAL(15,4)   NOT NULL DEFAULT 0,  -- 4 decimales para cantidades (ej: kg)
    costo_unitario      DECIMAL(15,2)   NOT NULL DEFAULT 0,  -- DECIMAL obligatorio, nunca FLOAT
    punto_reorden       DECIMAL(15,4)   NOT NULL DEFAULT 0,  -- stock mínimo para alerta
    activo              BOOLEAN         NOT NULL DEFAULT TRUE,
    fecha_creacion      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

COMMENT ON COLUMN inventario.costo_unitario IS 'DECIMAL(15,2) obligatorio para montos. Nunca usar FLOAT.';


-- =============================================================================
-- 6. COMPROBANTES (facturas externas procesadas — NO emitidas por el sistema)
-- =============================================================================
CREATE TABLE tipos_comprobante (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    empresa_id          UUID            NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    nombre              VARCHAR(80)     NOT NULL             -- 'Factura Compra', 'Factura Venta', 'Nota Crédito', 'Recibo'
);

CREATE TABLE comprobantes (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    empresa_id          UUID            NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    tipo_id             UUID            NOT NULL REFERENCES tipos_comprobante(id),

    -- Datos del documento externo (no generado por el sistema)
    numero_comprobante  VARCHAR(50)     NOT NULL,            -- número que viene en la factura externa
    fecha_emision       DATE            NOT NULL,
    fecha_vencimiento   DATE,

    -- Contraparte
    cliente_id          UUID            REFERENCES clientes(id),
    proveedor_id        UUID            REFERENCES proveedores(id),

    -- Montos — DECIMAL(15,2) obligatorio
    monto_subtotal      DECIMAL(15,2)   NOT NULL DEFAULT 0,
    monto_iva           DECIMAL(15,2)   NOT NULL DEFAULT 0,
    monto_total         DECIMAL(15,2)   NOT NULL,
    saldo_pendiente     DECIMAL(15,2)   NOT NULL,            -- monto_total - pagado hasta el momento

    -- Carga y validación IA
    metodo_carga        VARCHAR(20)     NOT NULL DEFAULT 'manual'
                        CHECK (metodo_carga IN ('manual','ocr_pdf','ocr_imagen')),
    ruta_archivo        VARCHAR(500),                        -- ruta/URL del PDF o imagen original
    estado_validacion   VARCHAR(20)     NOT NULL DEFAULT 'confirmado'
                        CHECK (estado_validacion IN ('pendiente_revision','confirmado','rechazado')),

    -- Auditoría
    usuario_carga_id    UUID            REFERENCES usuarios(id),
    notas               TEXT,
    fecha_creacion      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    fecha_modificacion  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    -- Expansión futura: Timbrado DNIT (nullable — activar cuando el sistema emita facturas propias)
    timbrado_id         UUID            NULL,                -- FK futura a tabla timbrados (no existe aún)

    -- Un mismo número de comprobante no puede repetirse por empresa y tipo
    UNIQUE (empresa_id, tipo_id, numero_comprobante),

    -- Solo cliente O proveedor, no ambos
    CHECK (
        (cliente_id IS NOT NULL AND proveedor_id IS NULL) OR
        (cliente_id IS NULL AND proveedor_id IS NOT NULL)
    )
);

COMMENT ON COLUMN comprobantes.numero_comprobante IS 'Número del documento externo recibido. No es generado por este sistema.';
COMMENT ON COLUMN comprobantes.timbrado_id        IS 'NULLABLE — Expansión futura para emisión propia de facturas con Timbrado DNIT.';

CREATE TABLE detalle_comprobantes (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    empresa_id          UUID            NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    comprobante_id      UUID            NOT NULL REFERENCES comprobantes(id) ON DELETE CASCADE,
    inventario_id       UUID            REFERENCES inventario(id),  -- nullable: no todo item es del inventario
    descripcion         VARCHAR(300)    NOT NULL,
    cantidad            DECIMAL(15,4)   NOT NULL,
    precio_unitario     DECIMAL(15,2)   NOT NULL,
    porcentaje_iva      DECIMAL(5,2)    NOT NULL DEFAULT 0,  -- 0, 5 o 10 (IVA paraguayo)
    subtotal            DECIMAL(15,2)   NOT NULL,            -- cantidad * precio_unitario
    iva_monto           DECIMAL(15,2)   NOT NULL DEFAULT 0
);


-- =============================================================================
-- 7. PAGOS Y COBROS
-- =============================================================================
CREATE TABLE pagos (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    empresa_id          UUID            NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    comprobante_id      UUID            NOT NULL REFERENCES comprobantes(id) ON DELETE CASCADE,
    numero_recibo       VARCHAR(50),                         -- número del recibo de pago externo
    fecha_pago          DATE            NOT NULL,
    monto_pagado        DECIMAL(15,2)   NOT NULL,
    medio_pago          VARCHAR(30)     NOT NULL DEFAULT 'efectivo'
                        CHECK (medio_pago IN ('efectivo','transferencia','cheque','tarjeta','otro')),
    cuenta_banco_id     UUID,                               -- FK a cuentas_banco (definida abajo)
    notas               TEXT,
    usuario_id          UUID            REFERENCES usuarios(id),
    fecha_creacion      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);


-- =============================================================================
-- 8. CUENTAS BANCARIAS Y MOVIMIENTOS
-- =============================================================================
CREATE TABLE cuentas_banco (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    empresa_id          UUID            NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    banco               VARCHAR(100)    NOT NULL,
    numero_cuenta       VARCHAR(50),
    tipo                VARCHAR(20)     NOT NULL DEFAULT 'corriente'
                        CHECK (tipo IN ('corriente','ahorro','caja_chica')),
    moneda              VARCHAR(10)     NOT NULL DEFAULT 'PYG',
    saldo_actual        DECIMAL(15,2)   NOT NULL DEFAULT 0,
    activa              BOOLEAN         NOT NULL DEFAULT TRUE,
    fecha_creacion      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- FK diferida de pagos.cuenta_banco_id (ahora que existe la tabla)
ALTER TABLE pagos
    ADD CONSTRAINT fk_pagos_cuenta_banco
    FOREIGN KEY (cuenta_banco_id) REFERENCES cuentas_banco(id);

CREATE TABLE movimientos_banco (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    empresa_id          UUID            NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    cuenta_banco_id     UUID            NOT NULL REFERENCES cuentas_banco(id) ON DELETE CASCADE,
    fecha               DATE            NOT NULL,
    tipo                VARCHAR(10)     NOT NULL CHECK (tipo IN ('debito','credito')),
    monto               DECIMAL(15,2)   NOT NULL,
    descripcion         VARCHAR(300)    NOT NULL,
    referencia          VARCHAR(100),                        -- número de transferencia, cheque, etc.
    comprobante_id      UUID            REFERENCES comprobantes(id),  -- opcional: vinculado a factura
    usuario_id          UUID            REFERENCES usuarios(id),
    fecha_creacion      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);


-- =============================================================================
-- 9. SALDOS DE CUENTAS CORRIENTES (resumen por cliente/proveedor)
-- =============================================================================
-- Vista materializable para saldo rápido por cliente
-- v_saldo_clientes: usa subquery pre-agregada para evitar multiplicación 1:N
-- entre comprobantes y pagos cuando un comprobante tiene varios pagos parciales.
CREATE VIEW v_saldo_clientes AS
SELECT
    c.empresa_id,
    c.id                                        AS cliente_id,
    c.nombre                                    AS cliente,
    COALESCE(SUM(cp.monto_total), 0)            AS total_facturado,
    COALESCE(SUM(COALESCE(pag.cobrado, 0)), 0)  AS total_cobrado,
    COALESCE(SUM(cp.saldo_pendiente), 0)         AS saldo_pendiente
FROM clientes c
LEFT JOIN comprobantes cp ON cp.cliente_id = c.id AND cp.empresa_id = c.empresa_id
LEFT JOIN (
    SELECT comprobante_id, SUM(monto_pagado) AS cobrado
    FROM pagos
    GROUP BY comprobante_id
) pag ON pag.comprobante_id = cp.id
GROUP BY c.empresa_id, c.id, c.nombre;

-- v_saldo_proveedores: misma corrección anti-duplicación
CREATE VIEW v_saldo_proveedores AS
SELECT
    pr.empresa_id,
    pr.id                                       AS proveedor_id,
    pr.nombre                                   AS proveedor,
    COALESCE(SUM(cp.monto_total), 0)            AS total_facturado,
    COALESCE(SUM(COALESCE(pag.pagado, 0)), 0)   AS total_pagado,
    COALESCE(SUM(cp.saldo_pendiente), 0)         AS saldo_pendiente
FROM proveedores pr
LEFT JOIN comprobantes cp ON cp.proveedor_id = pr.id AND cp.empresa_id = pr.empresa_id
LEFT JOIN (
    SELECT comprobante_id, SUM(monto_pagado) AS pagado
    FROM pagos
    GROUP BY comprobante_id
) pag ON pag.comprobante_id = cp.id
GROUP BY pr.empresa_id, pr.id, pr.nombre;


-- =============================================================================
-- 10. LOG DE AUDITORÍA (registro de acciones del sistema y del chatbot)
-- =============================================================================
CREATE TABLE auditoria_log (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    empresa_id          UUID            NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    usuario_id          UUID            REFERENCES usuarios(id),
    accion              VARCHAR(20)     NOT NULL CHECK (accion IN ('INSERT','UPDATE','DELETE','SELECT','IA_ACTION')),
    tabla_afectada      VARCHAR(100),
    registro_id         UUID,                               -- ID del registro afectado
    datos_anteriores    JSONB,                              -- snapshot antes del cambio
    datos_nuevos        JSONB,                              -- snapshot después del cambio
    origen              VARCHAR(20)     NOT NULL DEFAULT 'ui'
                        CHECK (origen IN ('ui','chatbot','api','sync')),
    ip_origen           VARCHAR(45),
    fecha               TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE auditoria_log IS 'Registro completo de cambios. Las acciones del chatbot IA se marcan como origen=chatbot.';


-- =============================================================================
-- 11. SYNC QUEUE (cache offline — cola simple unidireccional)
--     Solo usada cuando la App Principal pierde internet momentáneamente.
--     No es sync bidireccional — solo App Principal → Supabase.
-- =============================================================================
CREATE TABLE sync_queue (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    empresa_id          UUID            NOT NULL,
    dispositivo_id      VARCHAR(100)    NOT NULL,            -- identificador del PC operador
    tabla_destino       VARCHAR(100)    NOT NULL,
    operacion           VARCHAR(10)     NOT NULL CHECK (operacion IN ('INSERT','UPDATE','DELETE')),
    payload             JSONB           NOT NULL,
    estado              VARCHAR(20)     NOT NULL DEFAULT 'pendiente'
                        CHECK (estado IN ('pendiente','sincronizado','error')),
    intentos            INTEGER         NOT NULL DEFAULT 0,
    error_detalle       TEXT,
    fecha_creacion      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    fecha_sync          TIMESTAMPTZ
);


-- =============================================================================
-- 12. ÍNDICES DE PERFORMANCE
-- =============================================================================
-- Los más consultados por empresa
CREATE INDEX idx_comprobantes_empresa     ON comprobantes (empresa_id);
CREATE INDEX idx_comprobantes_cliente     ON comprobantes (cliente_id);
CREATE INDEX idx_comprobantes_proveedor   ON comprobantes (proveedor_id);
CREATE INDEX idx_comprobantes_fecha       ON comprobantes (fecha_emision);
CREATE INDEX idx_comprobantes_estado      ON comprobantes (estado_validacion);
CREATE INDEX idx_detalle_comprobante      ON detalle_comprobantes (comprobante_id);
CREATE INDEX idx_pagos_comprobante        ON pagos (comprobante_id);
CREATE INDEX idx_inventario_empresa       ON inventario (empresa_id);
CREATE INDEX idx_movimientos_banco_cuenta ON movimientos_banco (cuenta_banco_id);
CREATE INDEX idx_auditoria_empresa_fecha  ON auditoria_log (empresa_id, fecha);
CREATE INDEX idx_sync_queue_estado        ON sync_queue (estado, fecha_creacion);
CREATE INDEX idx_usuarios_empresa         ON usuarios (empresa_id);
CREATE INDEX idx_plan_cuentas_empresa     ON plan_cuentas (empresa_id, codigo);


-- =============================================================================
-- 13. DATOS SEMILLA (seed mínimo para arrancar)
-- =============================================================================
DO $$
DECLARE
    v_empresa_id UUID := uuid_generate_v4();
    v_rol_admin  UUID;
    v_rol_op     UUID;
    v_tipo_compra UUID;
    v_tipo_venta  UUID;
BEGIN
    -- Empresa demo
    INSERT INTO empresas (id, nombre, ruc, moneda_principal)
    VALUES (v_empresa_id, 'Empresa Demo SRL', '80012345-6', 'PYG');

    -- Roles
    SELECT id INTO v_rol_admin FROM roles_usuario WHERE nombre = 'admin';
    SELECT id INTO v_rol_op    FROM roles_usuario WHERE nombre = 'operador';

    -- Usuario admin demo
    INSERT INTO usuarios (empresa_id, nombre, email, password_hash, id_rol)
    VALUES (v_empresa_id, 'Administrador', 'admin@demo.com',
            '$2b$12$PLACEHOLDER_HASH_BCRYPT', v_rol_admin);

    -- Usuario operador demo
    INSERT INTO usuarios (empresa_id, nombre, email, password_hash, id_rol)
    VALUES (v_empresa_id, 'Operador Demo', 'operador@demo.com',
            '$2b$12$PLACEHOLDER_HASH_BCRYPT', v_rol_op);

    -- Tipos de comprobante base
    INSERT INTO tipos_comprobante (empresa_id, nombre) VALUES
        (v_empresa_id, 'Factura de Compra'),
        (v_empresa_id, 'Factura de Venta'),
        (v_empresa_id, 'Nota de Crédito'),
        (v_empresa_id, 'Nota de Débito'),
        (v_empresa_id, 'Recibo de Cobro'),
        (v_empresa_id, 'Recibo de Pago');

    -- Categorías de inventario base
    INSERT INTO categorias_inventario (empresa_id, nombre) VALUES
        (v_empresa_id, 'Materia Prima'),
        (v_empresa_id, 'Insumos'),
        (v_empresa_id, 'Producto Terminado'),
        (v_empresa_id, 'Mercadería para Reventa');

    -- Plan de cuentas mínimo (estructura base paraguaya)
    INSERT INTO plan_cuentas (empresa_id, codigo, nombre, tipo, naturaleza, es_hoja) VALUES
        (v_empresa_id, '1',       'ACTIVO',                        'activo',     'deudora',   FALSE),
        (v_empresa_id, '1.1',     'Activo Corriente',              'activo',     'deudora',   FALSE),
        (v_empresa_id, '1.1.01',  'Caja y Bancos',                 'activo',     'deudora',   TRUE),
        (v_empresa_id, '1.1.02',  'Cuentas por Cobrar Clientes',   'activo',     'deudora',   TRUE),
        (v_empresa_id, '1.1.03',  'Inventario',                    'activo',     'deudora',   TRUE),
        (v_empresa_id, '2',       'PASIVO',                        'pasivo',     'acreedora', FALSE),
        (v_empresa_id, '2.1',     'Pasivo Corriente',              'pasivo',     'acreedora', FALSE),
        (v_empresa_id, '2.1.01',  'Cuentas por Pagar Proveedores', 'pasivo',     'acreedora', TRUE),
        (v_empresa_id, '2.1.02',  'IVA por Pagar',                 'pasivo',     'acreedora', TRUE),
        (v_empresa_id, '3',       'PATRIMONIO',                    'patrimonio', 'acreedora', FALSE),
        (v_empresa_id, '3.1.01',  'Capital Social',                'patrimonio', 'acreedora', TRUE),
        (v_empresa_id, '4',       'INGRESOS',                      'ingreso',    'acreedora', FALSE),
        (v_empresa_id, '4.1.01',  'Ventas',                        'ingreso',    'acreedora', TRUE),
        (v_empresa_id, '5',       'EGRESOS',                       'egreso',     'deudora',   FALSE),
        (v_empresa_id, '5.1.01',  'Costo de Mercadería Vendida',   'egreso',     'deudora',   TRUE),
        (v_empresa_id, '5.2.01',  'Gastos Administrativos',        'egreso',     'deudora',   TRUE),
        (v_empresa_id, '5.2.02',  'Gastos de Venta',               'egreso',     'deudora',   TRUE);

END $$;
