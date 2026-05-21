-- Almacenamiento fisico + adjuntos (imagenes de factura/recibo)

ALTER TABLE comprobantes
  ADD COLUMN IF NOT EXISTS ubicacion_fisica VARCHAR(200);
-- ruta_archivo ya existe en comprobantes (según schema v4)

ALTER TABLE pagos
  ADD COLUMN IF NOT EXISTS ruta_adjunto VARCHAR(500);

COMMENT ON COLUMN comprobantes.ubicacion_fisica IS
  'Lugar fisico donde esta archivada la factura en papel (ej: Bibliorato Rojo, Caja 2024).';
COMMENT ON COLUMN pagos.ruta_adjunto IS
  'Ruta relativa al adjunto del recibo (imagen o PDF).';
