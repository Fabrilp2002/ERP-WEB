-- Estado de pago visible para facturas y notas vinculadas.
-- Incluye todos los estados de validacion para que la UI pueda distinguir
-- pendiente, rechazado, anulado y pago financiero sin perder trazabilidad.

CREATE OR REPLACE VIEW v_estado_pago_comprobantes AS
SELECT
    c.id AS comprobante_id,
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
        WHEN c.estado_validacion = 'anulado' THEN 'anulado'
        WHEN c.estado_validacion = 'rechazado' THEN 'rechazado'
        WHEN c.monto_total <= 0 THEN 'no_aplica'
        WHEN c.saldo_pendiente >= c.monto_total THEN 'no_pagado'
        WHEN c.saldo_pendiente <= 0 THEN 'pagado'
        ELSE 'pago_parcial'
    END AS estado_pago
FROM comprobantes c;

COMMENT ON VIEW v_estado_pago_comprobantes IS
    'Estado de pago dinamico de comprobantes: pagado / pago_parcial / no_pagado / anulado / rechazado / no_aplica.';
