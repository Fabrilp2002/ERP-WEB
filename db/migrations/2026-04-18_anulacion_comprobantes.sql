-- Migración: Fase B — Anulación de comprobantes
-- Fecha: 2026-04-18
-- Autor: Claude
--
-- Agrega 'anulado' al check de estado_validacion y columnas de auditoría para
-- registrar quién, cuándo y por qué se anuló un comprobante.
--
-- Idempotente: seguro de re-ejecutar.

BEGIN;

-- 1. Agregar columnas de auditoría de anulación (si no existen)
ALTER TABLE comprobantes
    ADD COLUMN IF NOT EXISTS motivo_anulacion     TEXT,
    ADD COLUMN IF NOT EXISTS fecha_anulacion      TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS usuario_anulacion_id UUID REFERENCES usuarios(id);

-- 2. Reescribir el check constraint para incluir 'anulado'
ALTER TABLE comprobantes
    DROP CONSTRAINT IF EXISTS comprobantes_estado_validacion_check;

ALTER TABLE comprobantes
    ADD CONSTRAINT comprobantes_estado_validacion_check
    CHECK (estado_validacion IN ('pendiente_revision','confirmado','rechazado','anulado'));

COMMENT ON COLUMN comprobantes.motivo_anulacion     IS 'Razón textual ingresada por el usuario al anular el comprobante.';
COMMENT ON COLUMN comprobantes.fecha_anulacion      IS 'Momento exacto en que se anuló.';
COMMENT ON COLUMN comprobantes.usuario_anulacion_id IS 'Usuario que ejecutó la anulación (auditoría).';

COMMIT;
