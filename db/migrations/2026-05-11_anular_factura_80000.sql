-- =============================================================================
-- Limpieza puntual: eliminar el Gs. 80.000 fantasma de cuentas por pagar
-- Fecha: 2026-05-11
-- Pedido del PM: la factura de proveedor con saldo Gs. 80.000 no se localiza
--   en el flujo normal y se quiere sacarla del total "Por pagar".
-- Estrategia: ANULAR (no DELETE) para conservar trazabilidad y auditoria.
--   Anular setea estado_validacion='anulado'; el dashboard ya excluye
--   anulados de monto_por_pagar.
-- =============================================================================

-- PASO 1 — DIAGNOSTICO: ejecutar primero esta consulta para ver candidatos.
-- Mostrara TODAS las facturas de proveedor con saldo_pendiente exacto = 80.000
-- o monto_total exacto = 80.000.
--
-- SELECT c.id, c.numero_comprobante, c.fecha_emision,
--        c.monto_total, c.saldo_pendiente, c.estado_validacion,
--        c.metodo_carga, c.condicion, c.fecha_creacion,
--        pr.nombre AS proveedor, c.notas
--   FROM comprobantes c
--   LEFT JOIN proveedores pr ON pr.id = c.proveedor_id
--  WHERE c.proveedor_id IS NOT NULL
--    AND c.estado_validacion NOT IN ('anulado', 'rechazado')
--    AND (c.saldo_pendiente = 80000 OR c.monto_total = 80000)
--  ORDER BY c.fecha_creacion DESC;

-- PASO 2 — ANULACION: anula factura(s) de proveedor con saldo exacto 80.000.
-- Si el diagnostico devuelve UNA sola fila, ejecutar este UPDATE.
-- Si devuelve varias, agregar AND c.id = '<uuid>' para anular solo una.

UPDATE comprobantes
   SET estado_validacion = 'anulado',
       motivo_anulacion = 'Limpieza PM 2026-05-11 — factura no identificable; eliminada del total Por pagar',
       fecha_anulacion = NOW(),
       fecha_modificacion = NOW(),
       saldo_pendiente = 0
 WHERE proveedor_id IS NOT NULL
   AND estado_validacion NOT IN ('anulado', 'rechazado')
   AND saldo_pendiente = 80000;

-- PASO 3 — VERIFICACION: confirmar que el monto Por pagar ya no incluye los 80.000.
--
-- SELECT COALESCE(SUM(saldo_pendiente), 0) AS monto_por_pagar
--   FROM comprobantes
--  WHERE proveedor_id IS NOT NULL
--    AND saldo_pendiente > 0
--    AND estado_validacion NOT IN ('anulado', 'rechazado');
