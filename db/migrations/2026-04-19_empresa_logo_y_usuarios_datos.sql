-- Logo de empresa + datos personales de usuarios
-- (telefono, cargo, y email ya es NOT NULL por diseño)

ALTER TABLE empresas
  ADD COLUMN IF NOT EXISTS logo_url VARCHAR(500);

ALTER TABLE usuarios
  ADD COLUMN IF NOT EXISTS telefono VARCHAR(30),
  ADD COLUMN IF NOT EXISTS cargo VARCHAR(100);

COMMENT ON COLUMN empresas.logo_url IS
  'Ruta relativa al logo de la empresa (servida por backend estatico).';
COMMENT ON COLUMN usuarios.telefono IS 'Telefono de contacto del usuario.';
COMMENT ON COLUMN usuarios.cargo    IS 'Cargo o puesto del usuario dentro de la empresa.';
