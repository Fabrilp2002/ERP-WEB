# Estructura del Proyecto — Mapa Visual

> **Actualizado:** 2026-04-20 por Gemini — refleja estado post-Fase G

```
erp-empresa-1/
│
├── 📁 .claude/                       ← Configuración del harness Claude Code
│   └── settings.local.json
│
├── 📁 .git/                          ← Repositorio Git
│
├── 📁 docs/                          ← 📚 DOCUMENTACIÓN CENTRALIZADA
│   ├── arquitectura/
│   │   └── README.md                 ← Hub & Spoke, decisiones de diseño
│   ├── roadmap/
│   │   └── README.md                 ← Fases, timeline, KPIs
│   ├── especificaciones/
│   │   └── README.md                 ← Convenciones, estándares, modelos
│   ├── api/
│   │   └── API_REFERENCE.md          ← Endpoint reference (Swagger)
│   ├── diagramas/
│   │   ├── diagrama.mmd              ← Diagrama Mermaid
│   │   ├── diagrama.png              ← Diagrama renderizado
│   │   ├── diagrama_formal.mmd       ← Diagrama formal Mermaid
│   │   └── diagrama_formal.png       ← Diagrama formal renderizado
│   ├── manuales/
│   │   ├── Guia_Implementacion_Ollama_Claude.pdf  ← (histórico)
│   │   └── Manual_Operacion_Ollama_Usuario.pdf    ← (histórico)
│   ├── API_REFERENCE.md              ← Documentación API (copia raíz docs/)
│   ├── Documento_Maestro_ERP_v3.pdf  ← Documento maestro v3
│   ├── Documento_Maestro_ERP_v4.pdf  ← Documento maestro v4
│   ├── REPORTE_MEJORAS_ARTEFACTO.md  ← Reporte de mejoras (artefacto)
│   ├── REPORTE_MEJORAS_PROYECTO.md   ← Reporte de mejoras (proyecto)
│   └── REPORTE_MEJORAS_PROYECTO.pdf  ← Reporte de mejoras (PDF)
│
├── 📁 backend/                       ← ⚙️ FASTAPI + SQLALCHEMY (ASYNC)
│   ├── core/
│   │   ├── config.py                 ← Settings: DB, JWT, Gemini API
│   │   ├── database.py               ← AsyncSession, get_db()
│   │   ├── security.py               ← JWT, bcrypt, require_escritura(), require_admin()
│   │   ├── key_store.py              ← Gestión API key Gemini (persiste en .env)
│   │   └── __init__.py
│   ├── models/
│   │   ├── schemas.py                ← Pydantic (Decimal, IVA, condicion, adjuntos)
│   │   └── __init__.py
│   ├── routers/                      ← 16 ROUTERS (~60 endpoints)
│   │   ├── auth.py                   ← Login + ultimo_acceso + auditoría
│   │   ├── clientes.py               ← CRUD clientes + auditoría
│   │   ├── proveedores.py            ← CRUD proveedores + auditoría
│   │   ├── comprobantes.py           ← CRUD + anulación + condicion contado/crédito
│   │   ├── inventario.py             ← CRUD inventario + alertas stock
│   │   ├── dashboard.py              ← KPIs + flujo mensual + top clientes + medios pago
│   │   ├── ocr.py                    ← /extraer, /confirmar, /procesar, /importar-excel, /articulo-lookup
│   │   ├── export.py                 ← /comprobantes, /cuentas-corrientes, /inventario (Excel)
│   │   ├── chatbot.py                ← /chat/mensaje, /chat/estado (Gemini function calling)
│   │   ├── configuracion.py          ← /config/gemini-key (PUT/GET)
│   │   ├── pagos.py                  ← CRUD pagos + historial cliente/proveedor + saldos
│   │   ├── usuarios.py               ← CRUD usuarios (admin) + cambio password
│   │   ├── admin_sistema.py          ← Stats, backup JSON, wipe datos (admin)
│   │   ├── empresa.py                ← Datos empresa + logo (upload/delete)
│   │   ├── adjuntos.py               ← Upload/delete imágenes para comprobantes y pagos
│   │   └── __init__.py
│   ├── services/
│   │   ├── ocr.py                    ← Motor OCR: Gemini Vision + parser robusto JSON
│   │   ├── export.py                 ← Excel generation (openpyxl, estilos profesionales)
│   │   ├── chatbot.py                ← Gemini function calling (7 herramientas)
│   │   ├── audit.py                  ← Auditoría universal no-bloqueante (JSONB)
│   │   ├── preprocesado.py           ← OpenCV: deskew + CLAHE + denoise (disponible, no activo)
│   │   └── __init__.py
│   ├── main.py                       ← FastAPI app, CORS, 15 routers, StaticFiles
│   ├── requirements.txt              ← Dependencias Python
│   └── .env                          ← Variables de entorno (gitignored)
│
├── 📁 frontend/                      ← 🎨 NEXT.JS 14 + ELECTRON
│   ├── src/
│   │   ├── app/
│   │   │   ├── (app)/                ← Layout auth-guarded
│   │   │   │   ├── dashboard/        ← KPIs + Recharts (barras, pie, top clientes)
│   │   │   │   ├── comprobantes/     ← Lista + NuevoComprobanteModal + Anular + Pago
│   │   │   │   ├── ocr/              ← Upload multi-imagen + HITL confianza + Excel import
│   │   │   │   ├── exportar/         ← 5 opciones de descarga Excel
│   │   │   │   ├── cuentas/          ← Cuentas corrientes clientes/proveedores
│   │   │   │   │   └── [tipo]/[id]/  ← Detalle individual con facturas + pagos
│   │   │   │   ├── asistente/        ← Chat IA con Gemini function calling
│   │   │   │   ├── clientes/         ← CRUD clientes
│   │   │   │   ├── proveedores/      ← CRUD proveedores
│   │   │   │   ├── inventario/       ← CRUD inventario + alertas stock
│   │   │   │   └── admin/
│   │   │   │       ├── usuarios/     ← Gestión usuarios (crear, rol, password, activar)
│   │   │   │       ├── sistema/      ← Stats, backup JSON, wipe datos
│   │   │   │       ├── auditoria/    ← Visor log auditoría (filtros, badges acción)
│   │   │   │       └── empresa/      ← Datos empresa + upload logo
│   │   │   ├── login/                ← Página de login
│   │   │   ├── api/                  ← Proxies Next.js → FastAPI (OCR, adjuntos)
│   │   │   │   └── ocr/
│   │   │   │       ├── route.ts      ← Proxy /ocr/extraer
│   │   │   │       ├── confirmar/route.ts  ← Proxy /ocr/confirmar
│   │   │   │       └── importar-excel/route.ts  ← Proxy /ocr/importar-excel
│   │   │   ├── layout.tsx
│   │   │   ├── globals.css           ← Design system: paleta enterprise + componentes
│   │   │   ├── page.tsx              ← Redirect a /dashboard
│   │   │   └── providers.tsx         ← TanStack Query setup
│   │   ├── components/
│   │   │   └── Sidebar.tsx           ← Nav + logo empresa + status + logout
│   │   └── lib/
│   │       ├── types.ts              ← Tipos TypeScript (montos en string)
│   │       ├── auth.ts               ← Zustand store persistido
│   │       ├── api.ts                ← Axios + interceptors + todos los API clients
│   │       └── offline.ts            ← Dexie.js IndexedDB (cola offline)
│   ├── electron/
│   │   ├── main.js                   ← BrowserWindow (sin Ollama)
│   │   └── preload.js                ← contextIsolation API
│   ├── public/
│   │   ├── icon.ico                  ← Ícono ERP (7 tamaños, generado)
│   │   └── icon.png                  ← Ícono ERP (512px)
│   ├── package.json                  ← Next 14 + Electron 33 + Recharts
│   ├── tsconfig.json
│   ├── postcss.config.js             ← PostCSS + Tailwind + Autoprefixer
│   ├── tailwind.config.ts
│   ├── next.config.js
│   ├── .env.local
│   └── node_modules/                 ← (gitignored — reside en C:\erp_deps\)
│
├── 📁 db/                            ← 🗄️ SCRIPTS SQL
│   ├── esquema_bd.sql                ← PostgreSQL schema v4 + seed (12+ tablas, 2 vistas)
│   └── migrations/                   ← 6 migraciones incrementales idempotentes
│       ├── 2026-04-18_anulacion_comprobantes.sql
│       ├── 2026-04-18_apellido_usuarios.sql
│       ├── 2026-04-18_condicion_venta.sql
│       ├── 2026-04-19_adjuntos_y_ubicacion_fisica.sql
│       ├── 2026-04-19_empresa_logo_y_usuarios_datos.sql
│       └── 2026-04-19_medio_pago_contado.sql
│
├── 📁 config/                        ← ⚙️ ARCHIVOS DE CONFIGURACIÓN (histórico)
│
├── 📁 tools/                         ← 🛠️ SCRIPTS Y UTILIDADES
│   ├── scripts/
│   │   ├── setup.sh                  ← Instalación automatizada (bash)
│   │   └── setup_admin.bat           ← Setup admin (Windows)
│   ├── generar_icono.py              ← Genera icon.ico + icon.png
│   └── CREAR_ACCESO_DIRECTO.ps1      ← Crea "ERP Universal.lnk" en Escritorio
│
├── 📁 resources/                     ← 📦 ARCHIVOS ESTÁTICOS SERVIDOS POR FASTAPI
│   ├── logos/                        ← Logos de empresa (subidos via /empresa/logo)
│   └── adjuntos/                     ← Imágenes adjuntas
│       ├── comprobantes/             ← Facturas escaneadas
│       └── pagos/                    ← Recibos escaneados
│
├── 📁 archive/                       ← 📦 CÓDIGO OBSOLETO (v1-v3)
│
├── 📁 "Datos Generales de la empresa"  ← Documentación del cliente
├── 📁 "SOFTWARE CONTABLE"            ← Referencias de sistemas existentes
│
├── 📄 README.md                      ← 🏠 PÁGINA DE INICIO DEL PROYECTO
├── 📄 BITACORA_COLABORATIVA.md       ← 📋 REGISTRO DE AUDITORÍA (OBLIGATORIO)
├── 📄 CLAUDE.md                      ← 🤖 INSTRUCCIONES AUTOMÁTICAS CLAUDE CODE
├── 📄 ESTRUCTURA_PROYECTO.md         ← Este archivo
├── 📄 GUIA_RAPIDA.md                 ← Guía rápida de inicio
├── 📄 .env.example                   ← Template de variables de entorno
├── 📄 .gitignore                     ← Qué NO trackear en Git
├── 📄 .gitattributes                 ← Configuración Git
│
├── 📄 start_all.bat                  ← Inicia backend + frontend
├── 📄 start_backend.bat              ← Inicia solo FastAPI
├── 📄 start_frontend.bat             ← Inicia solo Next.js
├── 📄 INICIAR_ERP.vbs                ← Lanzador sin ventana CMD + abre Chrome
└── 📄 INSTALAR_ACCESO_DIRECTO.bat    ← Crea acceso directo en Escritorio
```

---

## Reglas de Organización

### ✅ DO's
- Documentación centralizada en `docs/`
- Código separado: `backend/`, `frontend/`
- Scripts en `tools/`
- Variables de entorno en `.env` (gitignored)
- Comentarios en BITACORA cuando se crea código
- Imágenes/adjuntos en `resources/` (servidos via `/static/`)

### ❌ DON'Ts
- NO codigo suelto en raíz
- NO archivos `.env` trackeados en Git
- NO documentación dispersa (centralizar en docs/)
- NO archivos obsoletos sin mover a `archive/`
- NO referencias a Ollama (eliminado en Fase E)

---

## Consulta Rápida

| Necesito... | Ubicación |
|-------------|-----------|
| Entender la arquitectura | `docs/arquitectura/` |
| Ver endpoints de API | `docs/api/API_REFERENCE.md` o `/docs` (Swagger) |
| Saber qué fase estamos | `CLAUDE.md` → Estado de Fases |
| Editar backend | `backend/` |
| Editar frontend | `frontend/src/` |
| Correr el ERP | `INICIAR_ERP.vbs` o `start_all.bat` |
| Ver registro de trabajo | `BITACORA_COLABORATIVA.md` |
| Variables de entorno | `.env.example` |
| Migraciones SQL | `db/migrations/` |
| Administración | Frontend: `/admin/sistema`, `/admin/usuarios`, `/admin/empresa` |
