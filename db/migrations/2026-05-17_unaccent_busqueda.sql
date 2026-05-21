-- =============================================================================
-- MIGRATION: extension unaccent para busqueda insensible a tildes
-- Fecha: 2026-05-17
--
-- Necesaria para que el filtro `buscar` del endpoint GET /comprobantes/
-- matchee "Insua" con "ÍNSUA", "Gonzalez" con "González", etc.
--
-- Una sola sentencia idempotente — Supabase trae el paquete pero la
-- extension no esta habilitada por defecto.
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS unaccent;

-- Verificacion: deberia devolver "INSUA"
-- SELECT unaccent('ÍNSUA');
