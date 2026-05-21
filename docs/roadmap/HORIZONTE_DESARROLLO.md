# Horizonte de Desarrollo — ERP_Web

> **Última actualización**: 2026-05-05
> **Versión**: v5.0-cloud
> **Estado general**: 65 % completado · MVP en producción · pendiente hardening + features de negocio

Este documento es la **fuente única de verdad** del trabajo restante. Cada item tiene prioridad (P0–P4), estimación, dependencias y criterio de aceptación.

---

## 0 · Resumen ejecutivo

```
┌──────────────────────────────────────────────────────────────────┐
│  ✅ Hecho               │  🟡 En curso       │  ⏳ Pendiente     │
├──────────────────────────────────────────────────────────────────┤
│  • Stack cloud-native   │  • Estado de pago  │  • Seguridad      │
│  • Datos productivos    │  • NC vinculadas   │  • Pagos reales   │
│  • UI fintech moderna   │                    │  • Reportes IVA   │
│  • Auth + invitaciones  │                    │  • OCR end-to-end │
│  • Storage adjuntos     │                    │  • CI/CD + tests  │
└──────────────────────────────────────────────────────────────────┘
```

**Tiempo estimado restante**: 80–110 horas hasta versión "comercial vendible".

**URLs en producción ahora mismo**:
- Frontend: https://erp-web-cyan-delta.vercel.app
- Backend: https://erp-web-backend-i5zv.onrender.com
- Repo: https://github.com/gfcarlos04-del/ERP-WEB (`develop`)

---

## 1 · Estado actual (lo que YA funciona)

### Infraestructura ✅
| Componente | Servicio | Estado |
|---|---|---|
| Frontend Next.js 14 | Vercel | LIVE (auto-deploy en push a `develop`) |
| Backend FastAPI | Render free | LIVE (cold start ~30 s) |
| Postgres | Supabase | 12 migraciones aplicadas |
| Storage adjuntos + logos | Supabase Storage | OK con signed URLs |
| Repo + CI básico | GitHub Actions | backend-deploy + frontend-ci + backend-test |

### Datos productivos ✅
| Tabla | Cantidad |
|---|---:|
| Clientes | 58 |
| Proveedores | 20 |
| Inventario (MP + insumos + productos) | 114 |
| Facturas históricas (2023–2026) | 243 |
| Detalles de items (productos por factura) | 1 578 |
| Saldo total por cobrar | ₲ 706.021.873 |

### Funcionalidades core ✅
- ✅ Login / logout con JWT
- ✅ Reset password por email (Resend en modo DRY-RUN, falta API key real)
- ✅ Invitación de usuarios por email (admin → operador / viewer)
- ✅ Roles: admin / operador / viewer (RBAC en 24 routers)
- ✅ Modo Básico / Avanzado (toggle en sidebar, persiste en BD)
- ✅ Asistente IA flotante (Gemini + 22 tools)
- ✅ OCR Gemini configurado (key en Render, falta validar end-to-end)
- ✅ Dashboard con sparkline + quick actions + timeline
- ✅ Listado de comprobantes con estado de pago
- ✅ Notas de crédito vinculadas (UI + backend)
- ✅ Cuentas corrientes (clientes y proveedores)
- ✅ Inventario con código + categoría
- ✅ BottomNav mobile + responsive
- ✅ Adjuntos PDF/imagen a facturas + recibos

---

## 2 · Pendientes priorizados

### P0 — Crítico antes de uso productivo real

#### 2.1 · Hardening de seguridad (12 h)
**Plan ya diseñado**: `~/.claude/plans/jiggly-swinging-candle.md`

| Tarea | Tiempo | Detalle |
|---|---:|---|
| Política estricta de password (8+ ch, mayús, núm, símbolo) | 1 h | `backend/core/password_policy.py` |
| Rate limiting `5/min` en `/auth/token` (SlowAPI) | 1 h | `backend/middleware/rate_limit.py` |
| Lockout de cuenta 15 min tras 5 fallos + email al usuario | 2 h | columnas en `usuarios`, integración con `email.py` |
| Fix de timing attack en login (bcrypt siempre con dummy hash) | 30 min | `auth.py:login` |
| Security headers middleware (HSTS, CSP, X-Frame-Options, etc.) | 1.5 h | `backend/middleware/security_headers.py` |
| Auditoría enriquecida con IP + User-Agent | 2 h | `audit.py` recibe `Request` opcional |
| Cron diario para borrar IPs > 90 días (privacidad) | 30 min | función SQL + Render cron |
| Idle timeout frontend (30 min sin actividad → logout) | 1.5 h | `frontend/src/lib/idle-timeout.ts` |
| Strength meter visual en seteo/reset password (zxcvbn-ts) | 1 h | `PasswordStrength.tsx` |
| Página "Mi seguridad" con últimos accesos + cambio pwd | 2 h | `(app)/perfil/seguridad/page.tsx` |
| Endpoints `/usuarios/me/exportar-datos` + `DELETE /usuarios/me` | 1 h | privacidad GDPR-like |
| **Rotación de secrets que aparecieron en chat** (JWT + Supabase) | 30 min | `docs/ROTACION_SECRETS.md` |

**Criterio de aceptación**: securityheaders.com → calificación A; 5 logins fallidos disparan lockout + email; password "abc12345" rechazada con mensaje claro.

#### 2.2 · Configurar Resend para emails reales (30 min)
- Crear cuenta en https://resend.com (free 3 000 emails/mes)
- Verificar dominio (DNS SPF/DKIM) o usar `onboarding@resend.dev` para tests
- Pegar `RESEND_API_KEY` en Render env vars
- Setear `EMAIL_FROM` y `APP_URL` con dominios reales

**Criterio**: pedir reset password → llega email real al inbox.

#### 2.3 · Personalización empresa (1 h)
- Cambiar nombre "Mi Empresa" placeholder por el real desde `/admin/empresa`
- Subir logo desde la UI → se ve en sidebar y en emails
- (Opcional) Branding personalizado: color principal, nombre comercial

---

### P1 — UX que necesita pulido visible

#### 2.4 · Modal "Ver detalle de factura" con items (2 h)
Hoy el listado muestra el primer item (preview). Falta:
- Click en una fila → modal con todos los items: cantidad, descripción, precio unitario, subtotal, IVA
- Total por IVA (10 % / 5 % / 0 %)
- Botón "Imprimir / PDF"
- Mobile: modal full-screen con cards

**Archivos**: `frontend/src/components/DetalleFacturaModal.tsx` (nuevo), integrar en `(app)/comprobantes/page.tsx`.

#### 2.5 · Tour de bienvenida (1.5 h)
Componente `<TourBienvenida>` con `react-joyride` ya planeado. 5 pasos:
1. Inicio (dashboard)
2. Cargar factura con foto
3. Lista de clientes
4. Pagos y cobros
5. Asistente IA

**Trigger**: `localStorage.tourCompletado !== 'true'` la primera vez.

#### 2.6 · Tooltips de ayuda contextual (1 h)
Componente `<Ayuda texto="..." />` ya creado. Falta integrarlo en:
- Campos del modal Nuevo Comprobante (RUC, IVA, condición)
- Crear cliente (RUC, dirección)
- OCR (qué pasa cuando subo una foto)

#### 2.7 · Mensajes de error humanos (1 h)
Reemplazar 8–10 mensajes técnicos por copy amigable:
| Antes | Después |
|---|---|
| "Internal Server Error" | "Algo falló del lado nuestro. Probá de nuevo en un minuto." |
| "Network Error" | "Sin conexión. Tu cambio se guardó y se sincronizará al volver." |
| "401 Unauthorized" | "Tu sesión venció, volvé a iniciar." (auto-redirect) |

---

### P2 — Funcionalidades core que el negocio necesita

#### 2.8 · Registro real de pagos / cobros (3 h)
Hoy las facturas tienen `saldo_pendiente` pero no hay UI para "cobrar / pagar".
- Botón "Registrar cobro" en cada factura de venta
- Botón "Registrar pago" en cada factura de compra
- Modal con: monto, fecha, medio de pago, recibo N°, adjunto opcional
- Trigger en BD que recalcula `saldo_pendiente` automáticamente
- Adjuntar comprobante de pago (PDF/imagen) → Storage

**Archivos**: `frontend/src/components/RegistrarPagoModal.tsx`, validar trigger SQL.

#### 2.9 · OCR end-to-end con cámara (2 h)
Botón "📸 Cargar factura" en dashboard YA existe. Falta validar:
- Mobile: abre cámara nativa del celular
- Foto se manda a `/ocr/extraer` (Gemini Vision)
- Form pre-llenado con: RUC, número, fecha, monto, items
- HITL (Human In The Loop) para confirmar antes de guardar
- Adjuntar la foto al comprobante creado

**Estado**: backend OK, falta probar UX completa en celular real.

#### 2.10 · Reportes IVA RG90 / DNIT (3 h)
Páginas ya existen (`/reportes/iva`, `/reportes/aging`) pero falta:
- Validar que las queries calculen bien en producción con datos reales
- Botón "Exportar a Excel" funcional
- Filtros por mes / rango de fechas

#### 2.11 · Conciliación bancaria (4 h)
Tabla `cuentas_banco` y `movimientos_banco` ya existen.
- CRUD bancos en `/bancos`
- Importar extracto bancario (CSV/Excel)
- Match automático con pagos registrados
- Marcar movimientos conciliados

#### 2.12 · Notas de crédito/débito UI completa (2 h)
Backend YA soporta. Falta UI:
- Botón "Emitir NC" en factura → modal con monto/motivo
- Lista de NC vinculadas en cada factura
- Estado de pago refleja NCs aplicadas

---

### P3 — Robustez operacional

#### 2.13 · CI/CD + tests automatizados (4 h)
| Item | Estado |
|---|---|
| GitHub Actions: backend-test (pytest) | configurado, falta tests reales |
| Tests pytest del chatbot guardrails | ya existían en desktop |
| Tests E2E con Playwright | TODO — login, crear comprobante, pagar |
| Frontend lint en cada PR | configurado |
| Coverage report | TODO |

**Criterio**: cada PR a develop corre suite verde antes de merge.

#### 2.14 · Mergear `develop` → `main` (15 min)
- Crear PR `develop → main`
- Mergear como squash o merge commit
- Cambiar Vercel + Render `productionBranch` a `main`
- `develop` queda como branch de integración continua

#### 2.15 · Monitoreo y alertas (1 h)
- UptimeRobot: ping a `/health` cada 5 min (mantiene Render free awake)
- Alerta por email si el servicio cae > 3 min
- Sentry para frontend (errores en runtime) — opcional

#### 2.16 · Backup automático Supabase (1 h)
- Free tier: backup manual semanal con `pg_dump` + script en cron de Render
- Pro tier ($25/mes): backups diarios automáticos de Supabase
- Documentar procedimiento de restore en `docs/BACKUP_RESTORE.md`

#### 2.17 · Documentación operativa (2 h)
| Doc | Contenido |
|---|---|
| `docs/DEPLOY.md` | Cómo deployar de cero (Render + Vercel + Supabase) |
| `docs/ROTACION_SECRETS.md` | Procedimiento para rotar JWT, password Supabase, etc. |
| `docs/BACKUP_RESTORE.md` | Cómo hacer/restaurar backups |
| `docs/TROUBLESHOOTING.md` | Errores comunes y cómo arreglarlos |
| `docs/ARQUITECTURA.md` | Diagrama de servicios + flujo de auth |

---

### P4 — Mejoras a futuro / nice-to-have

#### 2.18 · Modo Básico/Avanzado completo (2 h)
Toggle ya funciona. Falta:
- Diccionario `i18n-simple.ts` con más términos (~150 vs 60 actuales)
- Aplicar `useT()` en TODAS las páginas (hoy solo Sidebar)
- Validar UX en mobile

#### 2.19 · Asistente IA mejorado (3 h)
- Sugerencias contextuales según la página actual
- Acciones desde el chat ("Crear cliente Juan con RUC 123") — function calling escritura
- Historial de conversaciones persistido
- Modo voz (opcional)

#### 2.20 · Dashboard personalizable (3 h)
- Widgets arrastrables (drag & drop)
- Selector de qué KPIs mostrar
- Comparación vs período anterior

#### 2.21 · Búsqueda global (2 h)
- `Cmd/Ctrl + K` abre buscador
- Busca en clientes, proveedores, facturas, inventario
- Resultados con preview + atajo

#### 2.22 · Notificaciones (2 h)
- Email diario con facturas que vencen mañana
- Notificación in-app cuando se confirma un cobro
- WebSocket para updates en tiempo real (opcional)

#### 2.23 · PWA con offline real (4 h)
- Dexie ya está (offline queue de mutaciones)
- Falta: service worker que cachea assets + páginas
- Manifest para "Instalar en pantalla principal" (iPhone/Android)

#### 2.24 · Emisión propia de facturas (Timbrado DNIT) (15+ h)
**Bloqueante**: requiere convenio con DNIT + certificado digital + investigación SIFEN.
- Tabla `timbrados` (rangos vigentes)
- Generar XML según especificación SIFEN
- Firma digital
- Envío a SIFEN, captura CDC
- PDF KuDE (representación gráfica)

#### 2.25 · Multi-empresa (8 h)
Hoy es single-tenant. Para venderlo como producto:
- Onboarding self-service ("Crear mi empresa")
- Aislamiento estricto por `empresa_id` (ya está, validar)
- Plan free / paid (Stripe / pagos paraguayos)
- Subdominio por empresa (opcional)

---

## 3 · Plan de ejecución sugerido (orden cronológico)

### Sprint 1 — Hardening + UX final (2 semanas, ~25 h)
1. Hardening seguridad completo (P0 · 12 h)
2. Resend en producción + personalizar empresa (1.5 h)
3. Modal detalle factura + tour bienvenida + tooltips (4.5 h)
4. Mensajes de error humanos (1 h)
5. Mergear `develop` → `main` (15 min)
6. Monitoreo + backup + docs operativas (4 h)

**Resultado**: producto seguro, profesional, listo para uso real diario por el cliente.

### Sprint 2 — Core de negocio (2 semanas, ~14 h)
7. Registro de pagos/cobros con UI completa (3 h)
8. OCR validado end-to-end en celular real (2 h)
9. Reportes IVA RG90 + exportar Excel (3 h)
10. Conciliación bancaria (4 h)
11. NC/ND UI completa (2 h)

**Resultado**: ERP plenamente funcional con todos los flujos contables paraguayos.

### Sprint 3 — CI/CD + Robustez (1 semana, ~6 h)
12. Tests E2E Playwright (3 h)
13. Coverage + alertas (1.5 h)
14. Documentación operativa final (1.5 h)

**Resultado**: producto mantenible, con confianza para iterar sin romper.

### Sprint 4+ — Crecimiento (variable)
- Modo simple completo
- Asistente mejorado
- Dashboard personalizable
- PWA offline
- Emisión DNIT (cuando haya convenio)
- Multi-empresa (si se vuelve producto)

---

## 4 · Riesgos y mitigaciones

| Riesgo | Probabilidad | Mitigación |
|---|---|---|
| Render free se desconecta sin uso → primer login lento (30 s) | Alta | UptimeRobot ping cada 5 min · upgrade a $7/mes |
| Supabase free 500 MB se llena con adjuntos | Media | Monitorear · plan Pro $25/mes cuando supere 400 MB |
| JWT_SECRET en chat → riesgo si el chat se filtra | Alta | **Rotar inmediatamente** (P0 task) |
| Cliente reporta bug crítico en producción | Media | CI/CD sólido · rollback con un revert + push |
| Pérdida de datos por backup ausente | Alta | Backup semanal automático · documentar restore |
| Costo mensual escala más rápido que ingresos | Media | Mantener stack free hasta tener primeros pagos |

---

## 5 · Métricas de éxito

| Métrica | Meta |
|---|---|
| Uptime backend | > 99 % |
| Tiempo respuesta `/auth/token` | < 500 ms (p95) |
| Tiempo carga dashboard frontend | < 2 s |
| Errores 5xx en backend | < 0.1 % de requests |
| Tests CI passing | 100 % |
| securityheaders.com calificación | A |
| Lighthouse mobile | > 90 |

---

## 6 · Referencias cruzadas

- **Plan de seguridad detallado**: `~/.claude/plans/jiggly-swinging-candle.md`
- **Auditoría datos Excel**: `docs/AUDITORIA_DATOS_EXCEL.md`
- **Auditoría sistema contable**: `docs/AUDITORIA_SISTEMA_CONTABLE.md`
- **Migraciones SQL**: `db/migrations/`
- **Bitácora colaborativa**: `BITACORA_COLABORATIVA.md`

---

## 7 · Cambios desde la última versión del plan

**2026-05-05**:
- Estado actual actualizado: 12 migraciones aplicadas, 1.578 items reales en facturas
- Agregado P2.12 (NC/ND UI completa) tras commit `29a7ea1`
- Reflejados commits del usuario: estabilización frontend, auditoría Excel, NC vinculadas
- Tiempo total restante: 80–110 h (antes era 100+ h)

