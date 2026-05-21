-- Agrega condición de pago (contado/credito) a comprobantes.
-- Idempotente: se puede correr varias veces sin romper.
BEGIN;

ALTER TABLE comprobantes
    ADD COLUMN IF NOT EXISTS condicion VARCHAR(10) NOT NULL DEFAULT 'credito';

ALTER TABLE comprobantes DROP CONSTRAINT IF EXISTS comprobantes_condicion_check;
ALTER TABLE comprobantes
    ADD CONSTRAINT comprobantes_condicion_check
    CHECK (condicion IN ('contado', 'credito'));

-- Backfill: si saldo_pendiente = 0 y monto_total > 0, asumir contado
UPDATE comprobantes
   SET condicion = 'contado'
 WHERE saldo_pendiente = 0
   AND monto_total > 0
   AND condicion = 'credito';

CREATE INDEX IF NOT EXISTS idx_comprobantes_condicion ON comprobantes (empresa_id, condicion);

COMMIT;
