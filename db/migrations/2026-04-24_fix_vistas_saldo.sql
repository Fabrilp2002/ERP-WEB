-- =============================================================================
-- Migración: Corrección de vistas v_saldo_clientes y v_saldo_proveedores
-- Fecha: 2026-04-24
-- Problema: El LEFT JOIN entre comprobantes y pagos multiplicaba monto_total
--           por la cantidad de pagos parciales (bug de doble conteo 1:N).
-- Solución: Subquery pre-agregada de pagos antes del JOIN.
-- =============================================================================

-- Recrear v_saldo_clientes sin multiplicación
DROP VIEW IF EXISTS v_saldo_clientes;
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

-- Recrear v_saldo_proveedores sin multiplicación
DROP VIEW IF EXISTS v_saldo_proveedores;
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
