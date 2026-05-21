-- =============================================================================
-- MIGRATION: Fase K - action tokens del chatbot
-- Fecha: 2026-05-13
-- Proposito: persistir previews de acciones del chatbot para confirmar escrituras
-- con TTL, uso unico y aislamiento por empresa/usuario.
-- =============================================================================

CREATE TABLE IF NOT EXISTS chatbot_action_tokens (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    empresa_id      UUID        NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    usuario_id      UUID        NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    token_hash      TEXT        NOT NULL UNIQUE,
    accion          VARCHAR(50) NOT NULL,
    payload         JSONB       NOT NULL,
    expires_at      TIMESTAMPTZ NOT NULL,
    used_at         TIMESTAMPTZ NULL,
    fecha_creacion  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chatbot_action_tokens_tenant_exp
    ON chatbot_action_tokens (empresa_id, usuario_id, expires_at);

CREATE INDEX IF NOT EXISTS idx_chatbot_action_tokens_cleanup
    ON chatbot_action_tokens (expires_at)
    WHERE used_at IS NULL;

COMMENT ON TABLE chatbot_action_tokens IS
    'Tokens efimeros de confirmacion para acciones de escritura del chatbot.';

COMMENT ON COLUMN chatbot_action_tokens.token_hash IS
    'SHA-256 del token entregado al frontend. El token plano nunca se persiste.';
