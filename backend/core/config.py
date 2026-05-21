"""
Configuración del backend cloud (ERP_Web v5.0).

Lee variables de entorno desde el sistema o desde `backend/.env` (modo dev).
En producción (Railway), las env vars se inyectan directamente — no se usa archivo.

Sin fallback a SQLite ni lógica Electron — esto es cloud-native puro.
"""
from __future__ import annotations
import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


# Path al .env de dev (relativo al paquete backend). En producción no existe.
_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    # ─── Base de datos (Supabase Postgres) ─────────────────────────────────
    # Formato: postgresql+asyncpg://postgres:PASSWORD@db.PROYECTO.supabase.co:5432/postgres?ssl=require
    # Usar puerto 5432 (Session mode) — no 6543 (Transaction mode) sin la receta de NullPool.
    DATABASE_URL: str

    # Supabase URLs (para Storage y validaciones)
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""  # Service role — NUNCA exponer al cliente

    # ─── Auth ──────────────────────────────────────────────────────────────
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 480  # 8 horas

    # ─── Gemini API (OCR + chatbot) ────────────────────────────────────────
    # Configurar `GEMINI_API_KEY` en el panel de Render (o en `.env` local).
    # Nunca hardcodear: el repo es público.
    GEMINI_API_KEY: str = ""

    # ─── Email transaccional (Resend) ──────────────────────────────────────
    RESEND_API_KEY: str = ""
    EMAIL_FROM: str = "no-reply@example.com"

    # URL pública del frontend (para construir links en emails de reset/invitación)
    APP_URL: str = "http://localhost:3000"

    # ─── App ───────────────────────────────────────────────────────────────
    APP_NAME: str = "ERP Universal"
    VERSION: str = "5.0.0"
    DEBUG: bool = False

    # ─── CORS ──────────────────────────────────────────────────────────────
    # JSON array como string. Se parsea en main.py.
    # Default cubre dev local; en producción setear el dominio de Vercel.
    CORS_ORIGINS: str = '["http://localhost:3000","http://127.0.0.1:3000","https://erp-web-app-delta.vercel.app"]'

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE) if _ENV_FILE.exists() else None,
        env_file_encoding="utf-8",
        extra="ignore",  # ignora vars legacy (OLLAMA_*, ERP_RESOURCES_DIR, etc.)
    )


settings = Settings()
