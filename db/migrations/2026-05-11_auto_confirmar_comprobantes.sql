-- =============================================================================
-- Migración: Eliminar doble confirmación de comprobantes
-- Fecha: 2026-05-11
-- Motivo: A partir de ahora todo comprobante cargado por OCR/Excel queda en
--         estado 'confirmado' directamente. Esta migración promueve los
--         comprobantes existentes que quedaron en 'pendiente_revision' para
--         que aparezcan en el listado y no inflen "Cuentas por pagar" como
--         deuda fantasma invisible.
-- =============================================================================

UPDATE comprobantes
   SET estado_validacion = 'confirmado',
       fecha_modificacion = NOW()
 WHERE estado_validacion = 'pendiente_revision';
