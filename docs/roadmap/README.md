# Roadmap — ERP Universal v4.0+

## 📋 Planes activos (2026-05)

| Plan | Estado | Tiempo estimado |
|---|---|---|
| [PLAN_ANALISIS_CLIENTE.md](./PLAN_ANALISIS_CLIENTE.md) | 📋 Pendiente aprobación PM | ~11.5 h |
| [PLAN_SEGURIDAD_V2.md](./PLAN_SEGURIDAD_V2.md) | 📋 Pendiente aprobación PM | 14–18 h |
| [PLAN_NAVEGACION_CONSOLIDADA.md](./PLAN_NAVEGACION_CONSOLIDADA.md) | 📋 Pendiente aprobación PM | ~5.5 h |
| [FASE_K_CHATBOT_V2.md](./FASE_K_CHATBOT_V2.md) | 🔄 K.1 hecho (backend), K.2–K.4 pendiente | Resto: 6–8 h |
| [HORIZONTE_DESARROLLO.md](./HORIZONTE_DESARROLLO.md) | 📚 Documento maestro | — |
| [PLAN_SEGURIDAD.md](./PLAN_SEGURIDAD.md) | ✅ Sprint 1 ya implementado | — |

---

## Timeline

### ✅ Fase 1 — Cimientos SQL (Completada)
- Schema PostgreSQL completo (12 tablas + 2 vistas)
- Backend FastAPI con Swagger
- Seed data (demo empresa, roles, tipos comprobante)
- **Entrega:** db/esquema_bd.sql + backend/routers/*

### ✅ Fase 2 — App Desktop (Completada)
- Frontend Next.js 14 con todas las páginas
- Electron wrapper + auto-start Ollama
- Sistema offline con Dexie.js
- Sidebar + routing + auth guard
- **Entrega:** frontend/src/** + electron/**

### ✅ Fase 3 — OCR + Exportación (Completada)
- Motor OCR dual (Ollama local + Gemini fallback)
- Extracción de datos de facturas
- Human-in-the-Loop validación
- Exportación Excel profesional (5 reportes)
- **Entrega:** backend/services/{ocr,export}.py + frontend/ocr + frontend/exportar

### ⏳ Fase 4 — Chatbot IA (En progreso)
- Gemma4 E2B con Function Calling
- Mapeo de funciones del sistema a tools
- UI de chat integrada en app
- Memoria de contexto por sesión
- **Timeline:** ~2 semanas
- **Archivos:** backend/services/chatbot.py, frontend/chat/page.tsx

### 📋 Fase 5 — Acceso Remoto (Futuro)
- Build web de Next.js sin Electron
- Autenticación Supabase web (Magic Link / OAuth)
- Dashboard multiplataforma responsive
- Exportación desde web
- **Timeline:** ~3 semanas

### 🚀 Fase 6 — Timbrado DNIT (Futuro)
- Integración con SET (Servicio de Impuestos)
- Emisión propia de facturas
- Numeración automática por rango
- Validación de autorización de rango
- **Timeline:** ~4 semanas
- **Bloqueante:** Credenciales SET (MRE, clave)

### 📊 Fase 7 — Análisis Financiero (Futuro)
- Flujo de caja proyectado
- Análisis de tendencias
- Reportes gerenciales avanzados
- Dashboard ejecutivo
- **Timeline:** ~3 semanas

---

## Milestones Próximos

| Hito | Fecha | Descripción |
|------|-------|---|
| **Fase 4 MVP** | 2026-04-15 | Chatbot básico funcionando |
| **Build Electron** | 2026-04-17 | Empaquetado .exe con installer |
| **Beta Testing** | 2026-04-20 | Pruebas internas con gfcar |
| **Fase 5 Launch** | 2026-05-01 | Web remota en producción |

---

## Backlog Técnico

### Prioridad Alta
- [ ] Validación de duplicados (numero_comprobante + empresa)
- [ ] Logging estructurado (toda operación)
- [ ] Rate limiting en API
- [ ] Tests unitarios (core services)
- [ ] CI/CD pipeline (GitHub Actions)

### Prioridad Media
- [ ] Dark mode en frontend
- [ ] Internacionalización (ES/EN/PT)
- [ ] Soporte para múltiples monedas
- [ ] Webhook outbound (integraciones)
- [ ] API public con rate limit

### Prioridad Baja
- [ ] Mobile app nativa (React Native)
- [ ] Voice commands (reconocimiento voz)
- [ ] AR factura preview
- [ ] Blockchain audit trail

---

## Riesgos y Mitigación

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|--------|-----------|
| Gemma4 lento en OCR | Media | Alto | Fallback Gemini siempre listo |
| Ollama crash en Electron | Baja | Alto | Auto-restart + health check |
| Sync conflict offline | Muy baja | Medio | Write-only offline, unique constraints |
| RLS bypass en Supabase | Muy baja | Crítico | Auditoría log + JWT validation |
| User loses offline data | Baja | Alto | Dexie persistence + local backup |

---

## KPIs de Éxito

- ✅ Sistema arranca sin errores en nueva PC
- ✅ OCR detecta 90%+ de campos correctamente
- ✅ Sync offline completa <5s en reconexión
- ✅ Operador puede trabajar 4h sin internet
- ✅ Chat IA responde en <3s
