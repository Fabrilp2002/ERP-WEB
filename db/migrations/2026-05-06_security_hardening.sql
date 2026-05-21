-- Security hardening Sprint 1 (Fase A/B inicial)
-- Idempotente: agrega columnas para lockout de login y auditoría enriquecida.

ALTER TABLE usuarios
  ADD COLUMN IF NOT EXISTS failed_login_attempts INT NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS last_failed_login TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS locked_until TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS password_changed_at TIMESTAMPTZ DEFAULT NOW();

ALTER TABLE auditoria_log
  ADD COLUMN IF NOT EXISTS user_agent VARCHAR(255);

CREATE INDEX IF NOT EXISTS idx_auditoria_usuario_fecha
  ON auditoria_log (usuario_id, fecha DESC);


CREATE OR REPLACE FUNCTION limpiar_ips_viejas() RETURNS void AS $$
BEGIN
  UPDATE auditoria_log
  SET ip_origen = NULL,
      user_agent = NULL
  WHERE fecha < NOW() - INTERVAL '90 days'
    AND (ip_origen IS NOT NULL OR user_agent IS NOT NULL);
END;
$$ LANGUAGE plpgsql;
