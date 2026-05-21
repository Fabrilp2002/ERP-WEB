-- ═══════════════════════════════════════════════════════════════════════════
-- ERP_Web v5.0 — Migración inicial cloud
-- Fecha: 2026-05-02
--
-- Cambios:
--   1. Vista v_estado_pago_comprobantes — calcula estado de pago dinámico
--      (pagado / pago_parcial / no_pagado / sobre_pagado) basado en saldo.
--   2. Columna usuarios.modo_ui — preferencia de menú Básico/Avanzado.
--   3. Tabla password_reset_tokens — para flujo de reset password por email.
-- ═══════════════════════════════════════════════════════════════════════════


-- ─── 1. Vista v_estado_pago_comprobantes ─────────────────────────────────
-- Lee saldo_pendiente que ya se mantiene actualizado por triggers existentes
-- (ver fix_vistas_saldo.sql). Más eficiente que recalcular sumando pagos.
CREATE OR REPLACE VIEW v_estado_pago_comprobantes AS
SELECT
    c.id                                          AS comprobante_id,
    c.empresa_id,
    c.cliente_id,
    c.proveedor_id,
    c.numero_comprobante,
    c.fecha_emision,
    c.fecha_vencimiento,
    c.monto_total,
    GREATEST(c.monto_total - c.saldo_pendiente, 0) AS monto_pagado,
    c.saldo_pendiente,
    CASE
        WHEN c.estado_validacion = 'anulado'         THEN 'anulado'
        WHEN c.monto_total <= 0                       THEN 'no_aplica'
        WHEN c.saldo_pendiente >= c.monto_total       THEN 'no_pagado'
        WHEN c.saldo_pendiente <= 0                   THEN 'pagado'
        ELSE                                                'pago_parcial'
    END                                            AS estado_pago
FROM comprobantes c
WHERE c.estado_validacion IN ('confirmado', 'anulado');

COMMENT ON VIEW v_estado_pago_comprobantes IS
    'Estado de pago dinámico de comprobantes: pagado / pago_parcial / no_pagado / anulado / no_aplica. '
    'Lee saldo_pendiente actualizado por triggers existentes — sin recalcular pagos.';


-- ─── 2. Columna usuarios.modo_ui (Básico/Avanzado) ───────────────────────
-- Preferencia por usuario para mostrar menú reducido (8 ítems) o completo (28).
-- Default: 'basico' — pensado para usuarios con poco conocimiento digital.
ALTER TABLE usuarios
    ADD COLUMN IF NOT EXISTS modo_ui VARCHAR(10) NOT NULL DEFAULT 'basico'
        CHECK (modo_ui IN ('basico', 'avanzado'));

COMMENT ON COLUMN usuarios.modo_ui IS
    'Modo de UI: basico (8 ítems del menú) o avanzado (todos los 28 ítems). '
    'Default basico para usuarios nuevos.';


-- ─── 3. Tabla password_reset_tokens ──────────────────────────────────────
-- Almacena tokens de reset password con hash + expiración.
-- El email se manda con el token plano; en la BD solo guardamos el hash.
CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario_id      UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    token_hash      VARCHAR(64) NOT NULL,                  -- SHA-256 hex del token
    expires_at      TIMESTAMPTZ NOT NULL,
    used_at         TIMESTAMPTZ,                           -- NULL = no usado aún
    fecha_creacion  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    proposito       VARCHAR(20) NOT NULL DEFAULT 'reset'
        CHECK (proposito IN ('reset', 'invitacion'))       -- distingue reset vs seteo inicial
);

CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_hash
    ON password_reset_tokens (token_hash) WHERE used_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_usuario
    ON password_reset_tokens (usuario_id);

COMMENT ON TABLE password_reset_tokens IS
    'Tokens de reset password (flujo "olvidé contraseña") y de invitación '
    '(seteo inicial al crear usuario). El token plano solo vive en el email.';
