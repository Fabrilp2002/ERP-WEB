-- Medio de pago directo en comprobantes al contado.
-- Cuando condicion='contado', la factura se cobra/paga en el acto y NO requiere
-- un recibo separado — solo se registra el medio de pago sobre la factura misma.
-- Cuando condicion='credito', este campo queda NULL y se manejan recibos en la tabla pagos.

ALTER TABLE comprobantes
  ADD COLUMN IF NOT EXISTS medio_pago_contado VARCHAR(30);

-- Check de valores permitidos (mismos medios que tabla pagos)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'comprobantes_medio_pago_contado_check'
  ) THEN
    ALTER TABLE comprobantes
      ADD CONSTRAINT comprobantes_medio_pago_contado_check
      CHECK (medio_pago_contado IS NULL
             OR medio_pago_contado IN ('efectivo','transferencia','cheque','tarjeta','otro'));
  END IF;
END$$;

-- Backfill: facturas contado viejas se asumen "efectivo" (valor más común)
UPDATE comprobantes
   SET medio_pago_contado = 'efectivo'
 WHERE condicion = 'contado'
   AND medio_pago_contado IS NULL
   AND estado_validacion <> 'anulado';

COMMENT ON COLUMN comprobantes.medio_pago_contado IS
  'Medio de pago usado cuando la factura es al contado. NULL si es a crédito (se manejan recibos separados en tabla pagos).';
