# ERP_Web — ERP Esplendida PY en la nube

Versión web (cloud-native) del ERP para el **Laboratorio Esplendida PY** (fabricante de bronceadores y cremas). Sin instalación, sin Electron, accesible desde cualquier dispositivo con un navegador.

> **Nota:** este es un proyecto **paralelo** a `Empresa 1\` (la versión desktop). Ambos conviven sin interferir hasta que la versión cloud esté validada.

---

## 📚 Documentación del proyecto

| Documento | Para qué sirve |
|---|---|
| 📐 **[SDD — Especificación técnica](docs/sdd/SDD.md)** | Fuente de verdad. Arquitectura, módulos, BOM, finanzas, API, modelo de datos, reglas de negocio |
| 📖 **[Guía de usuario](docs/sdd/GUIA_USUARIO.md)** | Manual paso a paso para administradores y operadores |
| 🎯 **[Análisis de mejoras](docs/sdd/ANALISIS_MEJORAS.md)** | 24 oportunidades de mejora identificadas + roadmap de 10 semanas |
| 🚀 **[Guía de deploy en Supabase](docs/sdd/GUIA_SUPABASE_DEPLOY.md)** | Paso a paso para aplicar la migración del BOM |

> 💡 **Versión actual:** `v6.1.1` · 2026-05-12 · [Ver changelog](docs/sdd/SDD.md#-changelog-v50--v61)

---

## Visión

ERP contable + facturación + inventario + cuentas corrientes pensado para PyMEs paraguayas. Misma funcionalidad que la versión desktop, pero:

- 📱 Funciona en celular y desktop por igual
- 🌐 No requiere instalación — solo URL
- 🤖 Asistente IA flotante en cualquier pantalla
- 📸 OCR de facturas con la cámara (Gemini Vision)
- 🟢 Modo Básico (8 ítems) / ⚙️ Modo Avanzado (28 ítems) — toggle por usuario
- 💬 Lenguaje llano por defecto ("Lo que me deben" en vez de "Saldo pendiente")

---

## Stack

| Componente | Servicio |
|---|---|
| Base de datos | Supabase Postgres |
| Storage (adjuntos + logos) | Supabase Storage |
| Backend | FastAPI en Railway |
| Frontend | Next.js 14 en Vercel |
| Autenticación | JWT custom (HS256 + bcrypt) |
| Email transaccional | Resend |
| OCR + Chatbot IA | Gemini API |
| Offline | Dexie / IndexedDB (browser-side) |

---

## Quick start (desarrollo local)

### Pre-requisitos

- Python 3.13+
- Node.js 20+
- Cuenta en Supabase (free tier OK)
- API key de Gemini ([aistudio.google.com](https://aistudio.google.com))

### Setup

1. **Clonar el repo:**
   ```bash
   git clone https://github.com/gfcarlos04-del/ERP-WEB.git
   cd ERP-WEB
   ```

2. **Crear proyecto Supabase:**
   - https://supabase.com → New project
   - Copiar la URL y las keys (anon + service_role)
   - En SQL Editor, ejecutar `db/esquema_bd.sql` y luego cada archivo de `db/migrations/` en orden cronológico.

3. **Backend:**
   ```bash
   cd backend
   python -m venv .venv
   .venv/Scripts/activate          # Windows
   # source .venv/bin/activate     # macOS/Linux
   pip install -r requirements.txt
   cp ../.env.example .env
   # Editar .env con DATABASE_URL, SUPABASE_*, GEMINI_API_KEY, etc.
   uvicorn main:app --reload --port 8000
   ```

4. **Frontend:**
   ```bash
   cd frontend
   npm install
   cp ../.env.example .env.local
   # Editar .env.local: NEXT_PUBLIC_API_URL=http://localhost:8000
   npm run dev
   ```

5. **Bootstrap admin** (primera vez):
   ```bash
   cd backend
   python ../scripts/bootstrap_admin.py --email admin@miempresa.com --password "TuPassword123" --empresa "Mi Empresa SRL"
   ```

6. Abrir http://localhost:3000 → login.

---

## Deploy en producción

Ver `docs/DEPLOY.md` para guías detalladas de:
- Vercel (frontend)
- Railway (backend)
- Supabase (DB + Storage)
- Resend (emails)

---

## Estructura

```
ERP_Web/
├── backend/          # FastAPI + SQLAlchemy async
│   ├── core/         # config, database, security, storage
│   ├── routers/      # 24 endpoints REST
│   ├── services/     # OCR, chatbot, email, audit
│   └── models/       # schemas Pydantic
├── frontend/         # Next.js 14 (App Router)
│   ├── src/
│   │   ├── app/      # rutas
│   │   ├── components/
│   │   └── lib/      # api, auth, offline (Dexie), i18n-simple
│   └── public/
├── db/
│   ├── esquema_bd.sql
│   └── migrations/   # 13 migraciones SQL incrementales
├── scripts/          # bootstrap_admin, migrar_datos
├── tests/            # pytest
├── docs/             # guías técnicas y de usuario final
└── .github/
    └── workflows/    # CI/CD
```

---

## Workflow de colaboración

Ver [`CONTRIBUTING.md`](CONTRIBUTING.md). Resumen:

- `main` ← producción (auto-deploy a Vercel + Railway)
- `develop` ← integración (hacer todas las PRs acá)
- `feature/<nombre>`, `fix/<nombre>` ← branches de trabajo
- Cada cambio entra por PR con mínimo 1 review

---

## Documentos clave

### 📚 Documentación principal

- 📐 **[SDD — Especificación técnica completa](docs/sdd/SDD.md)** — Arquitectura, módulos, BOM, finanzas, API, reglas de negocio (v6.1.1)
- 📖 **[Guía de usuario](docs/sdd/GUIA_USUARIO.md)** — Manual para administradores y operadores
- 🎯 **[Análisis de mejoras](docs/sdd/ANALISIS_MEJORAS.md)** — 24 oportunidades + roadmap de 10 semanas
- 🚀 **[Deploy en Supabase](docs/sdd/GUIA_SUPABASE_DEPLOY.md)** — Aplicar la migración del BOM

### 📁 Otros archivos

- [`PLAN_MIGRACION_V5.md`](PLAN_MIGRACION_V5.md) — plan técnico completo de la migración cloud
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — reglas de branches, PRs, commits
- [`docs/`](docs/) — guías técnicas, manuales históricos, diagramas

---

## Licencia

Proprietario. Todos los derechos reservados.
