-- =============================================================================
-- MIGRATION: vistas de saldo excluyen facturas anuladas y rechazadas
-- Fecha: 2026-05-18
--
-- Bug: v_saldo_clientes y v_saldo_proveedores sumaban saldo_pendiente de TODAS
-- las facturas del contacto, incluso si estaban anuladas o rechazadas. Eso
-- producia un "saldo fantasma" en el dashboard / mapa / listados de contactos
-- que el usuario no podia encontrar en /comprobantes porque alli se mostraba
-- con estado_pago='anulado' o 'rechazado'.
--
-- Fix: agregar la condicion `cp.estado_validacion NOT IN ('anulado','rechazado')`
-- en el JOIN (no en el WHERE, para preservar contactos sin facturas validas).
--
-- Idempotente: CREATE OR REPLACE VIEW.
-- =============================================================================

CREATE OR REPLACE VIEW v_saldo_clientes AS
SELECT
    c.empresa_id,
    c.id                                        AS cliente_id,
    c.nombre                                    AS cliente,
    COALESCE(SUM(cp.monto_total), 0)            AS total_facturado,
    COALESCE(SUM(COALESCE(pag.cobrado, 0)), 0)  AS total_cobrado,
    COALESCE(SUM(cp.saldo_pendiente), 0)        AS saldo_pendiente
FROM clientes c
LEFT JOIN comprobantes cp
       ON cp.cliente_id = c.id
      AND cp.empresa_id = c.empresa_id
      AND cp.estado_validacion NOT IN ('anulado', 'rechazado')
LEFT JOIN (
    SELECT comprobante_id, SUM(monto_pagado) AS cobrado
    FROM pagos
    GROUP BY comprobante_id
) pag ON pag.comprobante_id = cp.id
GROUP BY c.empresa_id, c.id, c.nombre;


CREATE OR REPLACE VIEW v_saldo_proveedores AS
SELECT
    pr.empresa_id,
    pr.id                                       AS proveedor_id,
    pr.nombre                                   AS proveedor,
    COALESCE(SUM(cp.monto_total), 0)            AS total_facturado,
    COALESCE(SUM(COALESCE(pag.pagado, 0)), 0)   AS total_pagado,
    COALESCE(SUM(cp.saldo_pendiente), 0)        AS saldo_pendiente
FROM proveedores pr
LEFT JOIN comprobantes cp
       ON cp.proveedor_id = pr.id
      AND cp.empresa_id = pr.empresa_id
      AND cp.estado_validacion NOT IN ('anulado', 'rechazado')
LEFT JOIN (
    SELECT comprobante_id, SUM(monto_pagado) AS pagado
    FROM pagos
    GROUP BY comprobante_id
) pag ON pag.comprobante_id = cp.id
GROUP BY pr.empresa_id, pr.id, pr.nombre;

-- =============================================================================
-- LIMPIEZA HISTORICA: facturas anuladas/rechazadas con saldo > 0
-- Estas quedaron con saldo_pendiente sin resetear desde antes del fix del
-- endpoint /anular (que ahora pone saldo=0 al anular). Resetearlas evita
-- que sigan apareciendo en agregaciones aunque las vistas ya filtren por
-- estado_validacion.
-- =============================================================================

UPDATE comprobantes
SET saldo_pendiente = 0,
    fecha_modificacion = NOW()
WHERE estado_validacion IN ('anulado', 'rechazado')
  AND saldo_pendiente <> 0;

-- Diagnostico opcional: ver cuantas filas quedaron en 0 (deberia ser 0 ahora)
-- SELECT COUNT(*) FROM comprobantes
-- WHERE estado_validacion IN ('anulado','rechazado') AND saldo_pendiente <> 0;
