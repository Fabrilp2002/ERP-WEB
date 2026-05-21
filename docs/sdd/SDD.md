# SDD — ERP Esplendida PY

> **Spec Driven Development · v7.2 · 2026-05-18**

Especificación técnica del sistema de gestión para **Laboratorio Esplendida PY** — fabricante de bronceadores y cremas. Fuente de verdad para desarrollo, revisión y onboarding.

| Atributo | Valor |
|---|---|
| Versión | **7.2** |
| Fecha | 2026-05-18 |
| Estado | 🟢 Producción |
| Repositorio | `gfcarlos04-del/ERP-WEB` |
| Industria | Cosmética · Paraguay |
| Owners | Carlos García · Fabrizio López |
| Documento rector | Si hay duda entre una idea nueva y este SDD, gana este SDD hasta que el PM apruebe cambiarlo |
| Fuente de trazabilidad | `BITACORA_COLABORATIVA.md` + commits Git |

---

## 📑 Tabla de contenidos

0. [Gobernanza del SDD](#0-gobernanza-del-sdd)
1. [Changelog v5.0 → v6.1](#-changelog-v50--v61)
2. [Registro de autoría y aplicación](#registro-de-autoría-y-aplicación)
3. [Visión del producto](#1-visión-del-producto)
4. [Usuarios y roles](#2-usuarios-y-roles)
5. [Arquitectura general](#3-arquitectura-general)
6. [Módulos funcionales](#4-módulos-funcionales)
7. [BOM (Bill of Materials) — Recetas](#5-bom-bill-of-materials--recetas)
8. [Finanzas avanzadas](#6-finanzas-avanzadas)
9. [Dashboard — Estructura visual](#7-dashboard--estructura-visual)
10. [Flujo de datos](#8-flujo-de-datos)
11. [Modelo de datos](#9-modelo-de-datos)
12. [API — Contratos](#10-api--contratos)
13. [Seguridad](#11-seguridad)
14. [Inteligencia Artificial](#12-inteligencia-artificial)
15. [Modo Offline](#13-modo-offline)
16. [Infraestructura y deploy](#14-infraestructura-y-deploy)
17. [Calidad y pruebas](#15-calidad-y-pruebas)
18. [Reglas de negocio críticas](#16-reglas-de-negocio-críticas)
19. [Glosario técnico](#17-glosario-técnico)

---

## 0. Gobernanza del SDD

Este SDD es la **guía maestra de producto, arquitectura y desarrollo** del ERP. A partir del 2026-05-12, todo cambio importante debe quedar reflejado acá o en un documento enlazado desde `docs/sdd/`.

### Objetivos de este SDD

| Objetivo | Cómo se cumple |
|---|---|
| Definir el producto | Visión, alcance, usuarios, módulos y reglas de negocio |
| Definir arquitectura | Frontend, backend, base de datos, servicios externos y deploy |
| Definir contratos | Rutas UI, endpoints API, modelo de datos, migraciones y flujos |
| Guiar desarrollo | Cada feature nueva debe declarar impacto en UI, API, DB, seguridad y pruebas |
| Evitar regresiones | Reglas críticas, Definition of Done y matriz de autoría |
| Facilitar onboarding | Un nuevo dev debe poder entender qué existe, qué está aplicado y qué falta validar |
| Mantener trazabilidad | Toda aplicación se cruza con `BITACORA_COLABORATIVA.md`, commit y responsable |

### Roles de decisión

| Rol | Persona / agente | Autoridad |
|---|---|---|
| Owner | Carlos García (`gfcar`) | Prioridad de negocio, aprobación final y deploy productivo |
| Owner | Fabrizio López (`Fabri` / `Fabrilp2002`) | Co-propiedad del producto, colaboración técnica y aprobación de cambios compartidos |
| Arquitectura | `Gemini` | Decisiones de estructura, algoritmos y consistencia técnica |
| Desarrollo Codex | `Codex` | Implementación, fixes, verificación y actualización de bitácora |
| Desarrollo histórico | `Claude` | Cambios previos registrados en bitácora y commits |

### Regla de cambio del SDD

1. Si se agrega un módulo, endpoint, tabla, flujo o regla de negocio, se actualiza este SDD en el mismo turno o PR.
2. Si el SDD y el código discrepan, se debe corregir uno de los dos antes de seguir construyendo encima.
3. Si el cambio toca datos productivos, debe indicar migración, rollback posible y verificación ejecutada.
4. Si el cambio fue hecho por un colaborador, debe figurar en el Registro de autoría y aplicación.
5. Ningún roadmap futuro cuenta como implementado hasta que tenga commit, deploy o verificación concreta.

### Definition of Done para nuevas features

Una feature se considera completa solo si cumple:

| Área | Criterio mínimo |
|---|---|
| Producto | La pantalla o flujo existe y responde a una necesidad real del PM |
| Frontend | `npm run lint` y `npm run build` pasan |
| Backend | `python -m compileall backend` pasa; si toca reglas, `pytest` pasa |
| DB | Migración idempotente en `db/migrations/` si cambia schema |
| Seguridad | Roles y multi-tenant revisados; no se exponen secretos |
| Datos | Montos sin `float`; UUIDs; `empresa_id` donde corresponde |
| Documentación | SDD y bitácora actualizados |
| Deploy | Push a `main` o instrucción externa clara si requiere Supabase/Vercel/Render |

---

## ★ Changelog v5.0 → v6.1

### v7.2 — Consolidación /cuentas en /comprobantes + paginación + sort + búsqueda mejorada (2026-05-17 / 2026-05-18)

Bloque grande de UX sobre el listado central de comprobantes y limpieza de redundancias.

**Fase A — Quick wins**
- Dashboard: card "Lo último" eliminada (era ruido visual).
- Sidebar: nuevo grupo "Mi cuenta" (`/perfil/seguridad` + `/actividad`) **sin condicional admin** — visible para todos en desktop.
- Backend `GET /comprobantes/`: `page_size` max 200 → **1000**, nuevo param opt-in `with_total=true` que cambia el shape a `{items, total, suma_monto_total, suma_saldo_pendiente, page, page_size}`. Nuevos filtros: `tipo`, `cliente_id`, `proveedor_id`.
- Frontend: nuevo componente `Paginacion.tsx` reusable con « ‹ › » + selector `50/100/200/Todas`. Página `/comprobantes` ahora server-side. **Las 227 facturas son accesibles**.
- Reverté Tailwind 4 → 3 (la migración de Tailwind 4 cambia toda la sintaxis de `globals.css`, queda como proyecto aparte).

**Fase B — Consolidación**
- Filtros nuevos en `/comprobantes`: combobox contraparte (con `<optgroup>` Clientes + Proveedores), 3 cards de sub-total visible (Facturas filtradas · Suma total · Saldo pendiente). **La suma del listado es ahora el monto real a cobrar/pagar.**
- Nuevas rutas `/clientes/[id]` y `/proveedores/[id]` con score 🟢🟡🔴 + análisis histórico — reusan el componente `AnalisisContraparte` que vivía en `/cuentas/[tipo]/[id]`.
- **Eliminado** `frontend/src/app/(app)/cuentas/*`. Redirects permanentes 301 en `next.config.js` (`/cuentas` → `/comprobantes`, `/cuentas/{tipo}/{id}` → `/{cliente|proveedor}/{id}`).
- Sidebar: grupo "Contactos" eliminado, `/clientes` y `/proveedores` ahora son subitems de "Facturas". BottomNav y TopBar sincronizados.
- `PartyCard` recibe `onClick` que navega a la ficha del contacto.

**Mejoras UX adicionales**
- **Buscador server-side** en `/comprobantes`: matchea **número de comprobante O nombre del cliente O nombre del proveedor** vía ILIKE (antes filtraba solo número client-side dentro de la página visible). Debounce 200ms.
- **Búsqueda insensible a tildes**: `unaccent(lower(...))` en el filtro — "insua" matchea "ÍNSUA", "gonzalez" matchea "González". Requiere extensión `unaccent` aplicada en Supabase.
- **Ordenamiento por columna**: 4 columnas sortables con flecha visual (N° / Fecha / Contraparte / Monto). Click toggle asc/desc. Whitelist `_ORDER_BY_MAP` en backend anti SQL-injection.
- **Pendientes desglosado**: el dashboard separa "Pendientes de cobro" (ventas) de "Pendientes de pago" (compras). Backend `ResumenDashboard` gana `facturas_pendientes_cobrar` y `facturas_pendientes_pagar`.

**Fix saldos fantasma (2026-05-18)**
- Bug detectado: `v_saldo_clientes` y `v_saldo_proveedores` agregaban `saldo_pendiente` de facturas anuladas/rechazadas. Producía saldos visibles en dashboard/listados que el usuario no podía encontrar en `/comprobantes` (donde estado_pago='anulado' las esconde del filtro "no_pagado").
- Migración `db/migrations/2026-05-18_saldos_excluir_anulados.sql` con `CREATE OR REPLACE VIEW` agregando `AND cp.estado_validacion NOT IN ('anulado','rechazado')` en el JOIN.
- `historial_cliente`/`historial_proveedor` sincronizados (excluyen `rechazado` además de `anulado` en el cálculo del saldo agregado).

**Cleanups**
- `dashboardApi.cuentasCorrientes` removido del frontend (endpoint backend sigue vivo por compat).
- `BITACORA_COLABORATIVA.md` con 5 entradas nuevas (Fase A, Fase B, buscador+sort, audit, fix saldos).

### v7.0-rc1 — Fase v7.1 Foundation: trazabilidad de lotes + CPP (2026-05-17 noche)

- 📦 **Lotes de inventario** con vencimiento opcional. Tabla `inventario_lotes` + `inventario_movimientos` (kardex append-only). Stock existente entra como lote `INICIAL` sin vencimiento (migración no destructiva).
- 🧮 **CPP — Costo Promedio Ponderado**. `inventario.costo_unitario` se reinterpreta como CPP vigente. Fórmula `(stock_ant·costo_ant + cant_nueva·costo_nuevo)/(stock_ant+cant_nueva)` aplicada sólo en ingresos. Salidas no modifican CPP.
- 🚪 **FEFO** — al salir stock, el lote con vencimiento más cercano se descuenta primero (NULLs al final, desempate por `fecha_ingreso`). Implementado con `FOR UPDATE` para evitar carreras.
- 🔔 **Alerta de vencimientos** configurable por empresa (`empresas.dias_alerta_vencimiento`, default 30). Card en dashboard linkea a `/inventario/lotes`.
- 🧪 9 tests pytest del servicio (CPP, FEFO, validaciones, vencidos). Pytest 37/37.
- ⚠ **V7.2 pendiente**: integrar `consumir_fefo` automáticamente al facturar una venta. Necesita validación con datos reales antes de tocar `pagos_service.py` / `comprobantes.py`.

### v6.1.7 — Cierre integral: RLS aplicada + chatbot tokens + Render `main` (2026-05-17 noche)

- 🛡️ **P1 RLS Camino A aplicado en Supabase**: política `tenant_isolation` activa en 14+ tablas core (auto-detect por `column_name = 'empresa_id'`). `postgres` y `service_role` ya tenían `rolbypassrls = true`, así que el backend del ERP no se vio afectado. El SQL se ejecuta directamente desde Supabase SQL Editor — no se trackea en `db/migrations/` por decisión del PM.
- 🔑 **Migración `chatbot_action_tokens` aplicada**: Fase K.1 ahora 100% operativa en producción (previews TTL 60s + confirmación + uso único). Tabla con RLS propio.
- ⚙️ **Render unificado a branch `main`**: ya no hay push doble (`main` Vercel + `develop` Render). Toda la entrega se hace contra una sola rama.
- ✅ **Verificación integral**: 76 endpoints publicados, frontend `delta` sirve commit `011777f`, CORS verificado contra origen `erp-web-app-delta.vercel.app`, endpoints clave (`/pagos/analisis-{cliente,proveedor}/{id}`, `/chat/mensaje`, `/chat/mensaje-stream`, `/chat/confirmar-accion`) respondiendo.

### v6.1.6 — K.4.1 streaming + K.4.2 Playwright + P1 RLS preparado (2026-05-17 noche)

- 🌊 **K.4.1 Streaming SSE**: nuevo `chat_stream` async generator + endpoint `POST /chat/mensaje-stream` + frontend `chatApi.enviarMensajeStream` con `fetch().body.getReader()`. Aurora muestra la respuesta letra por letra preservando function calls.
- 🎭 **K.4.2 Playwright**: `@playwright/test` en devDeps, `playwright.config.ts`, suite `e2e/smoke.spec.ts` con 3 tests. Correr con `npm run test:e2e` (primera vez: `test:e2e:install`).
- 🔒 **P1 RLS preparado (no aplicado)**: migración `db/migrations/2026-05-17_enable_rls.sql` para 14+ tablas core con política `tenant_isolation` idempotente. Helper `backend/core/tenant.py` con `get_db_tenant` dependency. Pendiente decisión PM: BYPASSRLS rápido vs refactor routers para adopción gradual.
- 📐 **Fase 5 evaluación**: infraestructura existe (rol `viewer`, `require_escritura`, `puedeEscribir()`); necesita decisión de producto, no código especulativo.

### v6.1.5 — Fix chat key + consolidación Vercel (2026-05-17 tarde)

- 🩹 **Chat 400 resuelto**: `backend/core/key_store.py` reescrito para que la clave Gemini **ignore la env var de Render** y use sólo override-UI o hardcoded. Causa raíz: Render tenía `GEMINI_API_KEY` apuntando a una key revocada que ganaba sobre el default de Pydantic. Trade-off aceptado: repo privado → clave en código, rotación = commit.
- 🌐 **Consolidación Vercel**: PM elimina proyectos duplicados (`erp-web-`, `erp-web`); queda sólo `erp-web-app` con alias `erp-web-app-delta.vercel.app`. Default `CORS_ORIGINS` actualizado. Regex `^https://erp-web[a-z0-9-]*\.vercel\.app$` sigue cubriendo alias futuros.

### v6.1.4 — Sprint Aurora + Análisis Cliente + P0 Seguridad (2026-05-17)

- 🔐 **P0 Seguridad v2 código**: `.github/dependabot.yml` con 4 ecosystems (npm/pip/pip-dev/github-actions) y grupos `next-react`, `fastapi-stack`, `sqlalchemy-stack`. Detección y redacción de **`GEMINI_API_KEY` real expuesta** en `BITACORA_DESKTOP_ARCHIVO.md`; bloque "URGENTE" en `docs/ROTACION_SECRETS.md`. **La clave sigue en git history — pendiente rotación PM.**
- 🌌 **Fase K.2 — Widget Aurora**: nuevo `frontend/src/store/chatStore.ts` con Zustand + `persist` (localStorage `erp.chat.v1`, máx 50 msgs). FAB rebrandeado "Aurora" con gradient `indigo → violet → fuchsia`. Atajo **`Ctrl+J`** (legado `Ctrl+/` se mantiene). El historial sobrevive recarga.
- 💬 **Fase K.3 — `/asistente` rediseñada**: sidebar 288px con grupos por día (`Hoy` / `Ayer` / fecha), buscador case-insensitive, headers sticky por día, toggle del sidebar con `Menu`. Mobile = slide-over con backdrop. Header "Aurora — Asistente" + nota `Ctrl+J`.
- ♿ **Fase K.4 — Pulido a11y + motion + mobile**: `role="dialog"`/`role="log"`/`aria-live`/`aria-modal`/`aria-labelledby` en panel y modales. Escape cierra el modal de devoluciones. `motion-safe:` respeta `prefers-reduced-motion`. Iconos decorativos `aria-hidden`. Focus visible con ring. *(K.4.1 streaming Gemini SSE y K.4.2 suite E2E Playwright quedan como sub-fases futuras.)*
- 📊 **Plan Análisis Cliente — Entrega completa** (A.1 → A.6, ~11.5h estimadas):
  - Backend nuevo `backend/services/analisis_contraparte.py` con CTE `comp_clasificado` que detecta NC/ND por nombre del tipo. Cero migración SQL.
  - Endpoints `GET /pagos/analisis-cliente/{id}` y `GET /pagos/analisis-proveedor/{id}`.
  - Score 🟢🟡🔴 con reglas transparentes (devoluciones, atraso vs plazo, saldo +60 días, dormancia).
  - Componente `AnalisisContraparte.tsx` + `ScoreBadge` con popover de razones.
  - Modal con lista completa de NC y ND. Lenguaje neutro: "Devoluciones" / "Cargos extra".
  - Funciona simétrico cliente/proveedor con prop `esCliente`.
  - 6 tests unitarios nuevos. Pytest 28/28 OK.
- 📐 **Doc sincronización**: SDD actualizado en el mismo turno (no dejarse trabajos sin registrar).

### v6.1.3 — Estabilización producción Vercel/Render (2026-05-14 → 2026-05-15)

- 🧭 **Sidebar consolidada** (`Sidebar.tsx`): 5 grupos / 17 ítems → **7 grupos top-level / 13 ítems sin duplicados**. Cobros y pagos unificados en una sola entrada; Inicio y Asistente como links directos. Reemplaza al plan v6.1.2 "Navegación consolidada" (aplicado, ya no es pendiente).
- 🔁 **BackendKeepalive client-side** (`BackendKeepalive.tsx`): nuevo componente montado en AppLayout que hace `GET /health` cada 4 min mientras hay pestaña visible. Defense in depth con GitHub Actions cron y Vercel Cron.
- 🌐 **CORS Render reforzado**: `allow_origin_regex = ^https://erp-web[a-z0-9-]*\.vercel\.app$` en `backend/main.py`. Render despliega desde `develop` (no `main`) — push a `develop` requerido para que el deploy tome efecto.
- 📸 **OCR robusto**: pipeline PDF→JPEG q82 / 180 DPI / máx 3 páginas (antes PNG 300 DPI / 5 páginas) para evitar OOM y 502 en Render. Frontend sube el archivo **directo al backend** (`${API_BASE_URL}/ocr/extraer`) sin pasar por el proxy serverless de Vercel, eliminando el límite de payload/timeout.
- 🔐 **Vercel SSO desactivado** en proyecto `erp-web-`; alias estable público `https://erp-web-olive.vercel.app`. Proyecto reconfigurado a Framework Next.js + Node 22.x via Vercel API.
- ✅ **Auditoría integral 2026-05-15**: 22 pytest passed, lint + build (30 rutas) OK, smoke autenticado de todos los endpoints (dashboard, clientes/proveedores, comprobantes, pagos, inventario, reportes IVA/aging, OCR real, exportaciones Excel) — todos `200 OK` en producción.
- 🗂️ `.gitignore` agrega `.vercel/` para no subir metadata local de Vercel CLI.

### v6.1.2 — Planes formalizados (2026-05-13)

- 📋 **Plan de análisis por cliente** documentado en [`docs/roadmap/PLAN_ANALISIS_CLIENTE.md`](../roadmap/PLAN_ANALISIS_CLIENTE.md) — sin pestañas, una sola pantalla scrolleable que agrega score 🟢🟡🔴, resumen, hábitos de pago y devoluciones encima de la lista actual de facturas y pagos. Pendiente aprobación PM.
- 🛡️ **Plan de seguridad v2** documentado en [`docs/roadmap/PLAN_SEGURIDAD_V2.md`](../roadmap/PLAN_SEGURIDAD_V2.md) — sucesor del Sprint 1 ya implementado. Identifica 6 brechas en 4 sprints escalonados (P0 rotar secretos + Dependabot, P1 RLS Supabase + Cloudflare, P2 JWT httpOnly + CSP estricta, P3 2FA + ZAP + DRP). Pendiente aprobación PM.
- 🧭 **Plan de navegación consolidada** documentado en [`docs/roadmap/PLAN_NAVEGACION_CONSOLIDADA.md`](../roadmap/PLAN_NAVEGACION_CONSOLIDADA.md) — agrupa la barra superior de 10 ítems en 6 grupos lógicos mediante dropdowns (Facturas / Foto / IVA juntos; Clientes / Proveedores / Cuentas en Contactos). BottomNav mobile a 4 botones + "Más". Cero pérdida de funcionalidad — los 15 destinos siguen accesibles. ~5.5 h. Pendiente aprobación PM.
- 🚀 **Cold start de Render eliminado**: Vercel Cron `*/5 * * * *` a `/api/warmup` + pre-warm en login + auto-retry con countdown. Login pasa de ~50s primera vez a < 3s en uso normal.
- 🏷️ **Owners actualizados**: Carlos García y Fabrizio López declarados formalmente como co-owners en v6.1.1.

### v6.1 — Merge integrado

- Carlos arregló por su cuenta el IVA en paralelo a este SDD — el merge final combina ambos enfoques
- **"Datos maestros editables"** — clientes y proveedores soportan edición inline + soft delete (combinado con cards visuales y mapa)
- Inventario backend con `PUT /{id}` y `DELETE /{id}` activos
- Frontend auto-deploya en Vercel; backend en Railway tras merge del PR #3
- Documentación reorganizada en `/docs/sdd/` con landing page

### v6.0 — BOM y reportes financieros

#### 🧪 BOM (Bill of Materials) — Sistema de recetas

- Nuevas tablas: `recetas`, `receta_items`, `lotes_produccion`
- Nuevas vistas SQL: `v_recetas_detalle`, `v_capacidad_produccion`
- Nuevo router backend `/recetas` con CRUD + cálculo de costo + capacidad de producción
- Nuevas páginas: `/inventario/recetas`, `/inventario/produccion`

#### 💰 Reportes financieros nuevos

- **Aging Report** — antigüedad de saldos con buckets (al día, 1-30, 31-60, 61-90, +90 días)
- **Estado de Resultados (P&L)** — ventas, CMV, utilidad bruta, gastos, resultado neto
- **Forecast de caja** — proyección de posición a 30/60/90 días

#### 📊 Mejoras al dashboard

- Reemplazo de la dona confusa por **balanza de posición de caja**
- **Concentración de clientes** con HHI y análisis de riesgo
- **Comparativa estacional** (toggle vs mismo período año anterior)
- **Donut de capital invertido por categoría** en Inventario

#### 🐛 FIX crítico del cálculo de IVA

- El reporte usaba `subtotal / 11` y `subtotal / 21` asumiendo BRUTO
- El sistema guarda `subtotal` como NETO — fórmulas incompatibles
- Resultado: IVA subestimado en ~9% (tasa 10%) y ~5% (tasa 5%)
- **Fix:** usar `SUM(d.iva_monto)` directamente (valor pre-calculado)
- Archivos: `backend/routers/reportes.py`, `backend/routers/export.py`

#### 🎨 8 componentes reutilizables nuevos

`Sidebar` · `Breadcrumbs` · `Avatar` · `PartyCard` · `ProductCard` · `StockBar` · `SmartSummary` · `CashBalance` · `ClientConcentration` · `StockByCategory` · `PeriodFilter` · `Skeleton` · `EmptyState` · `ParaguayMapReal` (Leaflet)

#### 📅 Timeline

Vista cronológica de comprobantes agrupados por mes con stats por período y filtros.

---

## Registro de autoría y aplicación

Esta matriz resume **qué cambios están aplicados**, quién los hizo o los integró, y cuál es su evidencia. No reemplaza la bitácora: la complementa para que el SDD funcione como guía viva.

| Fecha | Responsable | Evidencia | Cambio aplicado | Estado |
|---|---|---|---|---|
| 2026-05-18 | Claude | `cf47030` | **Fix saldos fantasma** — vistas `v_saldo_clientes`/`v_saldo_proveedores` excluyen `estado_validacion IN ('anulado','rechazado')` en el JOIN. Migración `db/migrations/2026-05-18_saldos_excluir_anulados.sql`. `historial_*` sincronizado | 🚀 Deployado · 🟡 PM aplica vistas en Supabase |
| 2026-05-18 | Claude | `f7e54a7` | **Audit post-Fase B**: unaccent (búsqueda con tildes) + Pendientes desglosado (cobro/pago) en dashboard + cleanup `cuentasCorrientes` huérfano + bitácora con 4 entradas pendientes. Migración `db/migrations/2026-05-17_unaccent_busqueda.sql` | 🚀 Deployado · 🟡 PM aplica extensión unaccent |
| 2026-05-17 | Claude | `d2636a3` | **Comprobantes — buscador server-side multi-campo + sort por columna**. Endpoint con `buscar` (ILIKE sobre número + cliente + proveedor) y `order_by` (whitelist 10 claves). Frontend: debounce 200ms + `SortableTh` con flecha ↕▲▼ | 🚀 Deployado |
| 2026-05-17 | Claude | `30f82b1` | **Fase B — Consolidación /cuentas → /comprobantes**. Filtros nuevos (contraparte/tipo/estado_pago/período) + 3 cards sub-total + nuevas fichas `/clientes/[id]` y `/proveedores/[id]` con `ContraparteDetail`. Borrado `/cuentas/*` con 3 redirects 301. Sidebar simplificado | 🚀 Deployado |
| 2026-05-17 | Claude | `4fc6cfa` | **Fase A — Paginación visible**. Componente `Paginacion.tsx` (« ‹ › » + selector 50/100/200/Todas) en `/comprobantes`. Backend `with_total=true` devuelve `{items, total, page, page_size}`. Borrada card "Lo último" del dashboard. Grupo "Mi cuenta" en sidebar sin condicional admin. Tailwind 4 revert | 🚀 Deployado |
| 2026-05-17 | PM (gfcar) | Supabase SQL Editor | **Aplicación P1 RLS Camino A** — política `tenant_isolation` en 14+ tablas; `postgres`/`service_role` con `rolbypassrls=true` por defecto, backend no se ve afectado. Protege contra accesos vía `authenticator`/PostgREST | ✅ Aplicado |
| 2026-05-17 | PM (gfcar) | Supabase SQL Editor | **Migración `chatbot_action_tokens`** — tabla + 2 índices + policy `tenant_isolation`. Fase K.1 100% operativa | ✅ Aplicado |
| 2026-05-17 | PM (gfcar) | Render panel | **Render branch unificado a `main`** (era `develop`); fin del push doble | ✅ Aplicado |
| 2026-05-17 | Claude | `011777f` | **Migración RLS removida del repo** — PM gestiona RLS sólo desde Supabase SQL Editor | 📐 Doc |
| 2026-05-17 | Claude | `f355797` | **K.4.2 Playwright + P1 RLS preparado** — `@playwright/test`, `playwright.config.ts`, `e2e/smoke.spec.ts` (3 tests), `backend/core/tenant.py` con `get_db_tenant` dependency | 🚀 Deployado |
| 2026-05-17 | Claude | `1f0ba91` | **K.4.1 streaming SSE** — `chat_stream` async gen, `/chat/mensaje-stream`, `chatApi.enviarMensajeStream` con `fetch().body.getReader()`, Aurora muestra respuesta token a token | 🚀 Deployado |
| 2026-05-17 | Claude | `98227d6` | **SDD v6.1.5 + bitácora** con bloque del 17-may | 📐 Doc |
| 2026-05-17 | Claude | `00dd05a` | **Fix chat 400** — `key_store.get_key()` ignora `settings.GEMINI_API_KEY` y usa sólo override-UI o hardcoded en código. Resuelve el caso de env var Render con key revocada que ganaba sobre el default | 🚀 Deployado |
| 2026-05-17 | Claude | `ecccb0e` | **Consolidación Vercel** — default `CORS_ORIGINS` a `erp-web-app-delta.vercel.app`; regex sigue cubriendo cualquier `erp-web*.vercel.app` | 🚀 Deployado |
| 2026-05-17 | Claude | `36c2ebb` | **Hardcode fallback Gemini en `config.py`** + `backend/.env` local | 🚀 Deployado (insuficiente solo, ver `00dd05a`) |
| 2026-05-17 | Claude | `845800b` | **K.4 a11y + motion + mobile** — `role="dialog"`/`log`/`aria-live` en panel y modales; `Escape` cierra; `motion-safe:` respeta `prefers-reduced-motion`; sidebar slide-over en mobile | 🚀 Deployado |
| 2026-05-17 | Claude | `1926935` | **K.3 `/asistente` rediseñada** — sidebar 288px con grupos por día + buscador + headers sticky | 🚀 Deployado |
| 2026-05-17 | Claude | `12ca9c7` | **Plan Análisis Cliente** completo (A.1–A.6) — endpoint `/pagos/analisis-{cliente,proveedor}/{id}` + componente `AnalisisContraparte.tsx` con score, resumen, hábitos, devoluciones (modal), top 5 productos. 6 tests nuevos. Pytest 28/28 OK | 🚀 Deployado |
| 2026-05-17 | Claude | `15a7f7e` | **K.2 widget Aurora** — `chatStore.ts` Zustand+persist, FAB con gradient, atajo `Ctrl+J` | 🚀 Deployado |
| 2026-05-17 | Claude | `c2eca39` | **P0 Seguridad v2 código** — `.github/dependabot.yml` (4 ecosystems), redact `GEMINI_API_KEY` expuesta + bloque URGENTE en ROTACION_SECRETS | 🚀 Deployado · ⚠ rotación clave pendiente PM |
| 2026-05-17 | Claude | `56b649f` | **Sync SDD v6.1.3** con bitácora 2026-05-14/15 | 📐 Doc |
| 2026-05-15 | Codex | `945de0e` | **OCR directo al backend** — `frontend/src/app/(app)/ocr/page.tsx` llama `${API_BASE_URL}/ocr/extraer` desde el navegador, evita proxy Vercel (502 con PDFs reales) | 🚀 Deployado a producción (Vercel `main`) |
| 2026-05-15 | Codex | `4cd70fa` | **Auditoría integral** post-fix OCR/CORS: 22 pytest, lint, build (30 rutas), smoke autenticado completo, exportaciones Excel; Vercel `erp-web-` reconfigurado a Next.js + Node 22.x; `.vercel` agregado a `.gitignore` | ✅ Verificado en producción |
| 2026-05-15 | Codex | `5caceaf` | **Fix OCR 502** — pipeline PDF→JPEG q82 / 180 DPI / máx 3 páginas en `backend/services/ocr.py` | 🚀 Deployado en Render (`develop`) |
| 2026-05-15 | Codex | `2abaa2c` + `40367a6` | **CORS Render** — `allow_origin_regex` para dominios `erp-web*.vercel.app`; push a `develop` (Render no despliega `main`) | 🚀 Deployado, `OPTIONS /auth/login` 200 OK |
| 2026-05-15 | Codex | `1d75fcc` + `b979745` | **Vercel SSO desactivado** en proyecto `erp-web-`; alias estable `erp-web-olive.vercel.app` público | ✅ Verificado |
| 2026-05-14 | Claude | Sidebar.tsx + BackendKeepalive.tsx | **Sidebar 7 grupos sin duplicados** + **BackendKeepalive client-side cada 4 min**; refuerzo GitHub Actions keepalive con 4 reintentos | 🚀 Deployado a producción |
| 2026-05-13 | Claude | `fdb8e5b` | **Plan de análisis por cliente v1.1** (`PLAN_ANALISIS_CLIENTE.md`) — sin pestañas, una pantalla scrolleable con score, resumen, hábitos, devoluciones y top productos | 📋 Plan documentado, pendiente aprobación PM |
| 2026-05-13 | Claude | `2638bfb` | **Plan de seguridad v2** (`PLAN_SEGURIDAD_V2.md`) — 6 brechas identificadas en 4 sprints (P0–P3) | 📋 Plan documentado, pendiente aprobación PM |
| 2026-05-13 | Claude | `706473a` | **Plan de navegación consolidada** (`PLAN_NAVEGACION_CONSOLIDADA.md`) — barra superior de 10 a 6 grupos con dropdowns; mobile a 4 botones + "Más"; 0 funcionalidades eliminadas | 📋 Plan documentado, pendiente aprobación PM |
| 2026-05-13 | Claude | `b05d576` | Fix cold start Render: Vercel Cron `/api/warmup` cada 5 min + pre-warm en login + auto-retry | 🚀 Deployado a producción |
| 2026-05-13 | Codex | `db/migrations/2026-05-13_chatbot_action_tokens.sql` | Fase K.1 backend: `action_token` TTL 60s en DB, `POST /chat/confirmar-accion`, `PATCH /comprobantes/{id}`, `DELETE /pagos/{id}` admin-only | ✅ Backend deployado; pendiente aplicar migración en Supabase |
| 2026-05-12 | Fabri (`Fabrilp2002`) | `9dcdfb0` | BOM/recetas, producción, forecast de caja, aging, P&L, timeline, mapa real, componentes visuales nuevos | Integrado a `main` |
| 2026-05-12 | Codex | `6a68d61` | Merge de cambios de Fabri en `main`, resolución de conflictos y fixes TypeScript para que Vercel compile | Push a `main`; build OK |
| 2026-05-12 | Fabri (`Fabrizio Ivan López Parzajuk`) | `8f546e8` | Reorganización del SDD en `docs/sdd`, landing page, guía Supabase y workflow GitHub Pages | Aplicado por fast-forward |
| 2026-05-12 | Codex | `c7e488f` + ejecución DB | Aplicación real de la migración BOM en Supabase y registro en bitácora | DB verificada |
| 2026-05-11 | Carlos / `gfcarlos04-del` | `a9d5a10` | IVA y datos maestros editables/anulables | En producción |
| 2026-05-10 | Carlos / Claude | `5ea86da`, `647a7ff`, `bba5b5a` | Topbar, tabs de facturas, combobox de cobros/pagos y navegación a facturas por pagar | En producción |
| 2026-05-10 | Carlos / Claude | `29ddcab`, `9b168a6`, `d241d6e` | Confirmación previa, undo global, fix de deploy backend y health check rápido | En producción |
| 2026-05-09 | Carlos / Claude | `4f9c262`, bitácora | Dashboard ampliado, chatbot transaccional, asistente flotante persistente | En producción |

### Estado de aplicación del SDD v7.2

| Área | Aplicado en código | Aplicado en producción/datos | Validación |
|---|---|---|---|
| Frontend Vercel `erp-web-app` (alias `erp-web-app-delta.vercel.app`) | Sí, commit `cf47030` en `main` | Auto-deploy desde `main` | `/api/version` responde con commit actual |
| Backend API Render | Sí, último commit en `main` | Auto-deploy desde **`main`** (consolidado 17-may) | `/health` 200, 78+ endpoints en `/openapi.json` |
| **Consolidación `/cuentas` → `/comprobantes`** | Sí, commit `30f82b1`. Componente compartido `ContraparteDetail`. Redirects 301 en `next.config.js` | Sí | Acceder a `/cuentas` redirige; nuevas fichas `/clientes/[id]` y `/proveedores/[id]` operativas |
| **Paginación visible en `/comprobantes`** | Sí, `Paginacion.tsx` reusable. Backend `with_total=true` | Sí | « ‹ › » + selector 50/100/200/Todas; las 227 facturas accesibles |
| **Búsqueda multi-campo + sort por columna** | Sí, commit `d2636a3`. Buscador server-side ILIKE sobre numero/cliente/proveedor + ordenamiento whitelist | Sí | `SortableTh` con flecha ↕▲▼; sub-totales se ajustan al filtro |
| **Búsqueda insensible a tildes** | Sí, commit `f7e54a7`. `unaccent(lower(...))` | 🟡 PM debe aplicar `CREATE EXTENSION unaccent` en Supabase | "insua" → matchea "ÍNSUA" |
| **Pendientes desglosado (cobro/pago)** | Sí, commit `f7e54a7`. Backend `ResumenDashboard` agrega `facturas_pendientes_{cobrar,pagar}` | Sí | Dashboard muestra 3 cards: IVA / Pendientes cobro / Pendientes pago |
| **Fix saldos fantasma** (vistas excluyen anulados) | Sí, commit `cf47030`. Migración `2026-05-18_saldos_excluir_anulados.sql` | 🟡 PM debe aplicar `CREATE OR REPLACE VIEW` en Supabase | Proveedor con factura anulada deja de aparecer con saldo en dashboard |
| Supabase BOM | Sí, migración `2026-05-11_bom_recetas.sql` | Sí, ejecutada el 2026-05-12 | 3 tablas, 3 columnas y 2 vistas verificadas |
| Supabase RLS multi-tenant | Sí, política `tenant_isolation` | Sí, 14+ tablas con `rowsecurity=true` | `postgres` y `service_role` con `rolbypassrls=true` → backend no afectado |
| Supabase `chatbot_action_tokens` | Tabla + 2 índices + RLS | Sí | Fase K.1 operativa end-to-end |
| Supabase `inventario_lotes` + `inventario_movimientos` (v7.1) | Tablas + RLS + seed INICIAL | Sí | `/inventario/lotes` operativa; CPP recalcula con cada ingreso |
| Dependabot | `.github/dependabot.yml` con npm/pip/actions | Sí, PRs automáticos | Mayoría mergeada; ⚠ rechazar PR de tailwindcss 4.x.x hasta migrar |
| Gemini API key | Hardcoded en `backend/core/key_store.py` (repo privado) | Sí | Override-UI > hardcoded; env var ignorada |
| Streaming chat SSE | `/chat/mensaje-stream` + `chat_stream` generator | Sí | Aurora widget consume `fetch().body.getReader()`; `/asistente` full-page todavía usa endpoint legado |
| Análisis Cliente/Proveedor | Endpoints + componente + score; migrado a `/clientes/[id]` y `/proveedores/[id]` | Sí | 6 tests unitarios; pendiente validación con datos reales |
| Playwright E2E | `playwright.config.ts` + `e2e/smoke.spec.ts` (3 tests) | Sin correr aún en CI | Requiere `npm run test:e2e:install` |
| Docs SDD | Sí, carpeta `docs/sdd` | Pendiente si se quiere sitio público | GitHub Pages requiere Source = GitHub Actions |

### Validaciones pendientes recomendadas

Estas validaciones son manuales porque dependen de sesión real en Vercel y datos productivos:

1. **Aplicar 2 SQL en Supabase**: `CREATE EXTENSION IF NOT EXISTS unaccent;` y la migración de vistas saldos (`db/migrations/2026-05-18_saldos_excluir_anulados.sql`).
2. Abrir `/clientes/{id}` con cliente real (≥10 facturas, ≥1 NC) → ver score 🟢🟡🔴 + devoluciones agrupadas + top 5 productos.
3. En `/comprobantes`: buscar "ínsua" (con o sin tilde) → matchear todas sus facturas. Click en encabezado "Monto" → ordena. Probar paginación 50/100/200/Todas.
4. Confirmar que la suma del listado filtrado (`Suma total` y `Saldo pendiente`) coincide con el monto real a cobrar/pagar.
5. Abrir Aurora con `Ctrl+J`; probar streaming letra-por-letra y confirmar un cobro.
6. Abrir `/inventario/lotes`, `/inventario/recetas`, `/finanzas/forecast`, `/reportes/aging`.
7. Borrar proyectos Vercel duplicados (`erp-web-`, `erp-web` si existen); dejar sólo `erp-web-app`.
8. **Rechazar PR de Dependabot tailwindcss 4.x.x** cuando reaparezca (la migración a Tailwind 4 requiere refactor de `globals.css`, queda como proyecto aparte).

### Planes en evaluación (pendientes de aprobación PM)

Estos planes están formalmente documentados pero **no implementados**. Hasta que el PM apruebe, no cuentan como funcionalidad activa del sistema.

| Plan | Documento | Tiempo | Beneficio |
|---|---|---|---|
| **Seguridad v2 — P2+** | [`PLAN_SEGURIDAD_V2.md`](../roadmap/PLAN_SEGURIDAD_V2.md) | 13 h restantes | ✅ P0 (Dependabot + scan) y P1 RLS aplicados. Pendiente: Cloudflare WAF (1–2 h código + panel) · P2 JWT httpOnly + CSP estricta (5 h) · P3 2FA + ZAP + DRP (8 h) |
| **Fase K Chatbot v2 — pulido residual** | [`FASE_K_CHATBOT_V2.md`](../roadmap/FASE_K_CHATBOT_V2.md) | ~3 h restantes | ✅ K.1–K.4 + K.4.1 streaming + K.4.2 Playwright setup aplicados. Pendiente: migrar página `/asistente` full-page al endpoint streaming (~1 h) · escribir más tests E2E con login real (~2 h) |
| **Navegación consolidada** | [`PLAN_NAVEGACION_CONSOLIDADA.md`](../roadmap/PLAN_NAVEGACION_CONSOLIDADA.md) | ✅ Aplicado en v7.2 | `/cuentas` eliminado, contactos viven bajo `/comprobantes`, sidebar simplificada |
| **Migración Tailwind 3 → 4** | — | 3–5 h | Refactor de `globals.css` (cambia toda la sintaxis de `@tailwind`/`@apply`). Cuando Dependabot reabra el PR, NO mergearlo; aplicarlo como sub-fase explícita. |
| **Fase 5 — Dashboard remoto viewer** | — | Sin estimar | Infraestructura ya existe (rol `viewer`, `require_escritura`, `puedeEscribir()` helper). Falta decisión de producto: qué pantallas ve un viewer, UI gates específicos. |
| **Fase 6 — Timbrado DNIT + emisión propia** | — | Multi-week | Requiere certificación tributaria con DNIT. Schema preparado (`timbrado_id` nullable en `comprobantes`). |
| **v7.1 — Lotes + CPP — Foundation** | [`PLAN_V7_LOTES_CPP.md`](../roadmap/PLAN_V7_LOTES_CPP.md) | ✅ Código aplicado | Tablas + service + endpoints + UI + 9 tests. Migración aplicada en Supabase. |
| **v7.2 — Integración FEFO con ventas** | Sub-fase de V7 | 4–6 h | Consumir FEFO automáticamente al facturar; persistir `lote_id` en `detalle_comprobantes`; reportes COGS y valuación al cierre. Requiere validación con datos reales. |

**Regla:** ningún plan cuenta como implementado hasta que tenga commit, deploy o verificación concreta. La sección "Registro de autoría y aplicación" arriba refleja únicamente lo que ya está en código.

---

## 1. Visión del producto

### ¿Qué es?

Sistema de gestión interno del **Laboratorio Esplendida PY**, empresa paraguaya que fabrica y comercializa cosméticos — con foco en bronceadores y cremas para el cuidado de la piel.

El sistema centraliza todas las operaciones administrativas, contables y de producción del laboratorio:

- 🛒 Compras de materias primas e insumos a proveedores
- 💰 Ventas y cobros a distribuidores, revendedoras y comercios
- 📦 Control de stock de productos terminados y materias primas
- 🧪 Gestión de recetas (BOM) y planeación de producción
- 💸 Seguimiento del flujo de caja y resultados

Todo desde un navegador web, accesible desde cualquier dispositivo.

### Productos

| Producto | Descripción |
|---|---|
| 🧴 **Bronceadores** | Producto estrella de la marca |
| 🫧 **Cremas** | Línea de cuidado de la piel |
| 🏭 **Fabricación propia** | Laboratorio en Paraguay |

### Alcance v6.1 — Incluido

- **Operaciones:** Facturas de venta y compra, cobros y pagos, OCR de facturas
- **Inventario y producción:** Stock, recetas (BOM), capacidad de producción, planeación de lotes
- **Comercial:** Clientes y proveedores con mapa de Paraguay, cuentas corrientes, análisis de concentración
- **Financiero:** Dashboard con storytelling, Aging Report, P&L, Forecast de caja
- **Contabilidad:** Plan de cuentas, resumen IVA (con cálculo corregido), exportación a Excel
- **IA:** Chatbot asistente, OCR Gemini Vision
- **Otros:** Timeline cronológico, multi-empresa, modo offline, auditoría completa

### Fuera de alcance v6.1

- Emisión propia de facturas con Timbrado DNIT *(preparado en DB, no activo)*
- Liquidación de sueldos
- Punto de venta (ventas al mostrador)
- Trazabilidad de lotes con vencimientos *(planificado v7)*
- Costo promedio ponderado (CPP) para valuación de inventario *(planificado v7)*

---

## 2. Usuarios y roles

Cada usuario pertenece a **una sola empresa** y nunca puede ver datos de otras.

| Rol | Quién lo usa | Permisos |
|---|---|---|
| 🔴 **admin** | Dueño / gerencia | Configuración empresa, gestión usuarios, CRUD completo, recetas, reportes financieros |
| 🟡 **operador** | Administración / producción | Cargar facturas, registrar pagos, inventario, recetas (NO gestionar usuarios) |
| 🟢 **viewer** | Contador / gerente externo | Solo lectura: dashboards, reportes, P&L. Sin modificar nada |

---

## 3. Arquitectura general

```
┌──────────────────────────────────────────────────────────────────┐
│                  🌐 USUARIO — NAVEGADOR                          │
│              Celular · PC · Tablet (cualquier OS)                │
└────────────────────────────┬─────────────────────────────────────┘
                             │ HTTPS
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│              ⚛️  FRONTEND — VERCEL                                │
│   Next.js 16 · React 19 · TypeScript · TailwindCSS               │
│   22 páginas · 14 componentes · Cache offline (Dexie)            │
│   TopBar: 10 ítems planos (plan v6.1.2: → 6 grupos con dropdown) │
└────────────────────────────┬─────────────────────────────────────┘
                             │ API REST / JSON
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│              🐍 BACKEND — RAILWAY                                │
│   FastAPI · Python 3.13 · SQLAlchemy async                       │
│   25 routers REST                                                │
└──────────┬──────────────────────────────────────┬────────────────┘
           │ SQL async                            │ SDK
           ▼                                      ▼
┌──────────────────────────┐    ┌──────────────────────────────────┐
│  🗄️  SUPABASE POSTGRES   │    │  ☁️  SERVICIOS EXTERNOS          │
│  PostgreSQL 15           │    │  · Supabase Storage              │
│  Multi-tenant RLS        │    │  · Gemini API (OCR + chatbot)    │
│  33+ tablas · 14 mig.    │    │  · Resend (emails)               │
└──────────────────────────┘    └──────────────────────────────────┘
```

---

## 4. Módulos funcionales

| Módulo | Ruta | Descripción |
|---|---|---|
| 🔐 Autenticación | `/auth` | Login, JWT, recuperación de contraseña |
| 📊 Dashboard | `/dashboard` | KPIs, balanza de caja, concentración, gráficos con filtro |
| 📅 Timeline | `/timeline` | Vista cronológica agrupada por mes |
| 🧾 Comprobantes | `/comprobantes` | Facturas de venta y compra, manual u OCR |
| 💸 Cobros y pagos | `/movimientos` | Pagos parciales o totales |
| 👥 Clientes | `/clientes` (listado), `/clientes/{id}` (ficha) | Catálogo con mapa Paraguay. La ficha tiene score 🟢🟡🔴, análisis histórico, facturas y pagos |
| 🏭 Proveedores | `/proveedores` (listado), `/proveedores/{id}` (ficha) | Catálogo con mapa Paraguay. La ficha tiene score 🟢🟡🔴, análisis histórico, facturas y pagos |
| 📦 Inventario | `/inventario` | Stock por categoría con donut de capital |
| 🧪 **Recetas (BOM)** | `/inventario/recetas` | **Ingredientes y costo real de cada producto** |
| 🏗️ **Capacidad producción** | `/inventario/produccion` | **Cuántas unidades se pueden producir hoy** |
| 📦 **Lotes (v7.1)** | `/inventario/lotes` | **Trazabilidad + vencimientos + CPP** |
| 📒 Contabilidad | `/contabilidad` | Plan de cuentas, libro diario, mayor |
| 🧾 **Cuenta de contacto** | `/clientes/{id}` y `/proveedores/{id}` | Reemplaza la antigua `/cuentas/{tipo}/{id}`. Ficha con score 🟢🟡🔴, análisis histórico, facturas y pagos. (`/cuentas/*` redirige 301) |
| 🕒 **Aging Report** | `/reportes/aging` | **Antigüedad de saldos por cliente/proveedor** |
| 📈 **Estado de Resultados** | `/reportes/resultados` | **P&L con utilidad bruta y margen** |
| 🧮 Resumen IVA | `/reportes/iva` | IVA débito/crédito (cálculo corregido) |
| 🔮 **Forecast de Caja** | `/finanzas/forecast` | **Proyección a 30/60/90 días** |
| 🤖 Asistente IA | `/asistente` | Chatbot conversacional Gemini |
| 📸 OCR Facturas | `/ocr` | Gemini Vision para imagen/PDF |
| 📎 Adjuntos | `/adjuntos` | Upload a Supabase Storage |
| 🛡️ Auditoría | `/actividad` | Log inmutable de acciones |
| ⚙️ Empresa | `/admin/empresa` | Datos, logo, configuración |
| 👤 Usuarios | `/admin/usuarios` | Solo admin. CRUD usuarios |

> 🆕 = Módulos nuevos en v6.0/v6.1

---

## 5. BOM (Bill of Materials) — Recetas

> 🎯 **Por qué importa:** Antes el sistema solo registraba operaciones (facturas, cobros). Ahora puede responder preguntas **productivas**: ¿Cuánto cuesta producir 1 bronceador? ¿Cuántas unidades puedo fabricar hoy? ¿Cuál es el cuello de botella?

### Concepto

Cada producto terminado (bronceadores, cremas) puede tener una **receta** que define qué insumos lo componen y en qué cantidad. Habilita:

- **Cálculo automático del costo unitario** = suma de costos de insumos / rendimiento
- **Margen automático** = (precio venta − costo) / precio venta × 100
- **Capacidad de producción** = con el stock actual, ¿cuántas unidades puedo hacer?
- **Identificación del cuello de botella** = qué insumo limita la producción
- **Planeación de lotes** = batches futuros con fechas y vencimientos

### Ejemplo Esplendida

```
Producto: Bronceador FPS 15 — 200 mL
Receta:   "Fórmula clásica con Uruku" — v1
Rendimiento: 100 unidades por batch

Ingredientes:
  - Extracto de Uruku       :   500 g     (Gs.  90.000)
  - Aceite de coco          :     5 L     (Gs. 125.000)
  - Frasco Oval 200mL       :   100 u     (Gs.  88.000)
  - Tapa Atomizador         :   100 u     (Gs. 210.000)
  - Etiqueta frente         :   100 u     (Gs.  18.000)
  - Etiqueta dorso          :   100 u     (Gs.  15.000)
                                          ──────────────
Costo total batch          :              Gs. 546.000
Costo unitario             :   546.000/100 = Gs. 5.460
Precio venta sugerido      :              Gs. 12.000
Margen                     :              54.5%
```

### Schema de datos

| Tabla / Vista | Propósito | Campos clave |
|---|---|---|
| `recetas` | Cabecera: una receta activa por producto | `producto_id`, `nombre`, `version`, `rendimiento`, `activa` |
| `receta_items` | Ingredientes con cantidad por receta | `receta_id`, `insumo_id`, `cantidad`, `orden`, `es_critico` |
| `lotes_produccion` | Planeación de batches | `numero_lote`, `cantidad_planificada`, `estado`, `fecha_planificada` |
| `inventario` (modificada) | +3 campos para BOM | `es_producto_terminado`, `precio_venta`, `notas_produccion` |
| `v_recetas_detalle` (vista) | Receta enriquecida con costo calculado | `costo_total_receta`, `costo_unitario`, `cantidad_items` |
| `v_capacidad_produccion` (vista) | Cuántos batches puedo producir | `batches_posibles`, `insumo_limitante` |

### Endpoints API

```
GET    /recetas/                       → lista de todas las recetas
GET    /recetas/{id}                   → receta con items + costos calculados
POST   /recetas/                       → crear receta + items
PUT    /recetas/{id}                   → actualizar receta (reemplaza items)
DELETE /recetas/{id}                   → soft delete (activa=false)

GET    /recetas/{id}/capacidad         → cuántas unidades puedo producir
                                          + insumo limitante + status items

POST   /recetas/lotes                  → crear lote de producción planificado
GET    /recetas/lotes/listar?estado=…  → listar lotes
```

---

## 6. Finanzas avanzadas

Tres reportes financieros nuevos que llevan la gestión a nivel gerencial.

### 6.1 Aging Report — Antigüedad de saldos

Endpoint: `GET /reportes/aging?tipo=clientes|proveedores`

| Tramo | Significa | Acción sugerida |
|---|---|---|
| 🟢 **Corriente** | No vencido aún | Sin problemas |
| 🟢 **1-30 días** | Vencido recientemente | Seguimiento |
| 🟡 **31-60 días** | Atraso considerable | Llamar para coordinar |
| 🟠 **61-90 días** | Atraso grave | Insistir cobro |
| 🔴 **+90 días** | Riesgo de incobrabilidad | 🚨 Acciones legales |

La UI muestra: gráfico de barras por tramo, alerta de "riesgo alto" si hay saldos +60 días, tabla por contraparte ordenada por mayor saldo, y detalle de las facturas más vencidas.

### 6.2 Estado de Resultados (P&L)

Pantalla: `/reportes/resultados`

```
  Ventas brutas (facturado)
−  Costo de mercadería vendida (CMV estimado)
=  Utilidad bruta                        [margen %]
−  Gastos operativos (estimado)
=  Resultado operativo                   [margen %]
−  IVA neto a pagar
=  Resultado del período                 [margen neto %]
```

> ⚠️ **Versión simplificada:** CMV se estima en 70% de las compras, gastos operativos en 30%. Para CMV real es necesario el BOM completo + vinculación venta↔producto (planificado v7).

### 6.3 Forecast de Caja

Pantalla: `/finanzas/forecast`

Proyección día por día de la posición de caja a 30/60/90 días, basada en fechas de vencimiento de facturas pendientes.

- **Input:** saldo inicial de caja + cuentas bancarias
- **Procesa:** facturas a cobrar (+) y a pagar (−) en sus vencimientos
- **Output:** gráfico de línea con saldo proyectado + alertas si cae bajo cero + tabla de movimientos día por día
- **Asume escenario optimista:** todos pagan/cobran en fecha

### 6.4 Análisis adicionales del Dashboard

- **Concentración de clientes:** Top 1/3/5, coeficiente HHI, alerta si dependencia > 30%
- **Balanza de caja:** barras horizontales contrapuestas (entrante vs saliente) con neto destacado
- **Comparativa estacional:** toggle para superponer datos del mismo período del año anterior
- **Capital invertido por categoría:** donut con valor de stock por tipo

---

## 7. Dashboard — Estructura visual

El dashboard se compone de 6 secciones (de arriba a abajo):

1. **Header** — saludo personalizado, nombre del usuario, nombre de empresa, fecha actual
2. **3 Hero Cards** — Por cobrar (azul) · Por pagar (rosa) · Ingresos cobrados con mini sparkline (verde)
3. **4 KPIs** — Total cobrado del mes, stock crítico, IVA del período, facturas pendientes
4. **Gráfico principal** — "Ingresos y egresos" con `PeriodFilter` y toggle de "comparar año anterior" + `CashBalance` al costado
5. **ClientConcentration** — análisis de dependencia comercial con Top 1/3/5
6. **Listas** — Top 5 clientes con deuda, Top 5 proveedores con saldo, Últimas 6 facturas
7. **Acciones rápidas** — 8 botones de operaciones más usadas

### Componentes utilizados

| Componente | Función | Tipo |
|---|---|---|
| `HeroCard` | KPI grande con sparkline opcional | Card |
| `CashBalance` 🆕 | Balanza horizontal entrante vs saliente | Barras |
| `ClientConcentration` 🆕 | Top N + HHI + alerta de riesgo | Barras + texto |
| `BarChart` (Recharts) | Ingresos y egresos por mes | Gráfico |
| `PeriodFilter` 🆕 | Mes/Trim/Sem/6M/12M/Año/Todo + custom | Pestañas |

---

## 8. Flujo de datos

### Flujo de carga del Dashboard (8+ llamadas paralelas)

```
Al entrar al dashboard, el frontend dispara simultáneamente:

  ├─ GET /dashboard/resumen                       → KPIs principales
  ├─ GET /dashboard/flujo-mensual?desde&hasta     → barras ingresos/egresos
  ├─ GET /dashboard/flujo-mensual (año anterior)  → comparativa estacional
  ├─ GET /dashboard/ultimos-comprobantes          → últimas 6 facturas
  ├─ GET /pagos/saldos-clientes                   → balanza + concentración
  ├─ GET /pagos/saldos-proveedores                → balanza
  ├─ GET /reportes/iva/liquidacion                → IVA débito-crédito
  ├─ GET /pagos/movimientos?tipo=cobro            → ingresos cobrados del mes
  └─ GET /empresa                                 → nombre/logo

Caché: 30 segundos. Stale-while-revalidate (React Query).
```

### Flujo: Crear receta (BOM)

```
1. Operador en /inventario/recetas → "Nueva receta"
2. Modal RecetaEditor se abre
3. Elige producto → si no es "es_producto_terminado", se marca al guardar
4. Agrega items uno por uno → calculadora en vivo:
     costoTotal     = sum(item.cantidad × insumo.costo_unitario)
     costoUnitario  = costoTotal / rendimiento
     margen         = (precio_venta − costoUnitario) / precio_venta × 100
5. POST /recetas/ con payload completo
6. Backend (Python):
     a. Valida producto existe en empresa
     b. Marca producto como es_producto_terminado=true si no lo era
     c. Desactiva otras recetas activas del mismo producto
     d. INSERT cabecera + N items en transacción
     e. Registra en auditoria_log
7. Frontend invalida caché y refetch
```

### Flujo: Capacidad de producción

```
GET /recetas/{id}/capacidad

Backend ejecuta:
  SELECT
    receta_id, producto_id,
    MIN(FLOOR(stock_insumo / cantidad_requerida)) AS batches_posibles,
    insumo con menor batches → insumo_limitante
  FROM receta_items JOIN inventario USING (insumo_id)
  WHERE receta.activa = TRUE

Resultado:
  {
    batches_posibles: 12,
    unidades_posibles: 1200,   // 12 batches × rendimiento (100)
    insumo_limitante: "Frasco Oval 200mL",
    items_status: [
      { insumo: "Frasco Oval 200mL", stock: 1200, requerido: 100,
        batches_posibles: 12, es_limitante: true },
      { insumo: "Extracto Uruku",     stock: 8000, requerido: 500,
        batches_posibles: 16, es_limitante: false },
      ...
    ]
  }
```

### Flujo: Forecast de caja

```
1. Frontend carga aging de clientes + proveedores
2. Por cada factura pendiente:
     - Día efectivo = max(fecha_vencimiento, hoy)
     - Si en el rango de proyección: suma a movimientos del día
3. Construye serie día a día:
     saldo[día] = saldo[día-1] + entradas[día] − salidas[día]
4. Detecta días con saldo negativo
5. Renderiza AreaChart con ReferenceLine en 0
```

---

## 9. Modelo de datos

### Tablas principales

| Tabla | Propósito | Cambios v6 |
|---|---|---|
| `empresas` | Multi-tenant root | — |
| `usuarios` + `roles_usuario` | Acceso con bcrypt + roles | — |
| `clientes` + `proveedores` | Contrapartes | — |
| `inventario` | Items de stock | **+3 campos:** `es_producto_terminado`, `precio_venta`, `notas_produccion` |
| `recetas` 🆕 | BOM cabecera | NUEVA |
| `receta_items` 🆕 | BOM detalle (ingredientes) | NUEVA |
| `lotes_produccion` 🆕 | Planeación de batches | NUEVA |
| `comprobantes` + `detalle_comprobantes` | Facturas + líneas | — |
| `pagos` | Cobros y pagos | — |
| `cuentas_banco` + `movimientos_banco` | Bancos | — |
| `plan_cuentas` | Plan contable parametrizable | — |
| `auditoria_log` | Trazabilidad inmutable | — |
| `sync_queue` | Cola offline | — |

### Vistas SQL importantes

| Vista | Calcula |
|---|---|
| `v_saldo_clientes` | Saldo pendiente por cliente (subquery pre-agregada) |
| `v_saldo_proveedores` | Saldo pendiente por proveedor |
| `v_recetas_detalle` 🆕 | Receta con costo total y unitario en vivo |
| `v_capacidad_produccion` 🆕 | Batches posibles por receta según stock actual |

### Migraciones

- 13 migraciones previas en `db/migrations/` (v1-v5)
- **v6:** `2026-05-11_bom_recetas.sql` — agrega 3 tablas, modifica inventario, crea 2 vistas

---

## 10. API — Contratos

### Routers (25 totales)

| Router | Prefijo | Descripción |
|---|---|---|
| auth | `/auth` | Login, refresh, reset password |
| clientes / proveedores | `/clientes`, `/proveedores` | CRUD + cuenta corriente |
| comprobantes | `/comprobantes` | CRUD facturas + anulación |
| pagos | `/pagos` | Cobros/pagos + saldos |
| inventario | `/inventario` | CRUD stock (con PUT/DELETE v6.1) |
| **recetas** 🆕 | `/recetas` | BOM: CRUD + capacidad + lotes |
| dashboard | `/dashboard` | KPIs + flujo-mensual |
| reportes | `/reportes` | IVA + **aging** (activado v6) |
| export | `/export` | Exportación Excel |
| ocr | `/ocr` | Gemini Vision |
| chatbot | `/chatbot` | Chat con IA |
| otros (12 más) | … | usuarios, empresa, adjuntos, etc. |

### Endpoints nuevos en v6

```
# BOM
GET    /recetas/                       → listar recetas
GET    /recetas/{id}                   → obtener receta + items + costos
POST   /recetas/                       → crear receta
PUT    /recetas/{id}                   → actualizar receta
DELETE /recetas/{id}                   → desactivar (soft)
GET    /recetas/{id}/capacidad         → cuánto puedo producir
POST   /recetas/lotes                  → planificar lote
GET    /recetas/lotes/listar           → listar lotes

# Aging (backend ya existía, ahora expuesto en frontend)
GET    /reportes/aging?tipo=clientes
GET    /reportes/aging?tipo=proveedores

# Inventario (nuevos PUT y DELETE v6.1)
PUT    /inventario/{id}                → actualizar item
DELETE /inventario/{id}                → soft delete
```

### Convenciones

- **Auth:** `Authorization: Bearer <JWT>` en todos los endpoints excepto `/auth/*` y `/health`
- **Filtro de período:** `?desde=YYYY-MM-DD&hasta=YYYY-MM-DD` o `?mes=YYYY-MM`
- **Pagination:** `?limit=N&offset=M`
- **Errores:** `{ "detail": "mensaje" }` con HTTP code apropiado

---

## 11. Seguridad

### Mecanismos activos (Sprint 1 — implementado 2026-05-06)

| Mecanismo | Función |
|---|---|
| 🔒 **bcrypt** | Contraseñas con costo 12. Nunca texto plano |
| 🎫 **JWT 2h** | Token autocontenido firmado HS256 (reducido de 8h a 2h en hardening 2026-05-09) |
| 🚦 **Rate limiting** | Login 5/min, reset 5/min — protección contra fuerza bruta |
| 🛡️ **Security headers** | HSTS, CSP, X-Frame-DENY, nosniff, Referrer-Policy, Permissions-Policy |
| 🌐 **CORS** | Solo dominio frontend autorizado |
| 🏢 **RLS Supabase** | ⚠️ Preparado pero **rowsecurity=false** en tablas base — plan v2 lo activa |
| 🔑 **Política passwords** | Min 8, 1 mayúscula, 1 minúscula, 1 número, 1 símbolo |
| ⏱️ **Idle timeout** | Cierre automático a 30 min sin actividad |
| 🧾 **Auditoría inmutable** | Log append-only con IP/UA (XFF último), retención 90 días |
| 🚫 **Lockout** | 5 fallos en 10 min → 15 min bloqueo + email de aviso |
| 🤖 **Acciones del chatbot** | Two-Phase Action con `action_token` TTL 60s + uso único (K.1) |

### Plan de hardening v2 — próximos sprints

Documentado en [`docs/roadmap/PLAN_SEGURIDAD_V2.md`](../roadmap/PLAN_SEGURIDAD_V2.md). Resumen de prioridades:

| Sprint | Tarea | Tiempo | Impacto |
|---|---|---|---|
| **P0** | Rotar `JWT_SECRET_KEY`, `GEMINI_API_KEY`, service role Supabase | 30 min | Alto |
| **P0** | Activar Dependabot + secret scanning en GitHub | 5 min | Alto |
| **P1** | Activar RLS en Supabase con políticas por `empresa_id` | 4–6 h | Alto |
| **P1** | Cloudflare gratis delante de Vercel + Render (WAF + DDoS) | 1 h | Medio-Alto |
| **P2** | Migrar JWT de `localStorage` a `httpOnly` cookie | 2–3 h | Medio |
| **P2** | CSP estricta sin `unsafe-inline` (nonce-based) | 2–4 h | Medio |
| **P3** | 2FA opcional con TOTP | 6 h | Alto cuando se active |
| **P3** | Pen test automático con OWASP ZAP | 2 h | Medio |
| **P3** | Drill de restore desde backup Supabase | 2 h | Alto si se necesita |

---

## 12. Inteligencia Artificial

### OCR de facturas

**Motor:** Gemini Vision

**Flujo:** imagen/PDF → OpenCV preprocesa → PyMuPDF convierte PDF a imagen → Gemini extrae JSON estructurado → usuario revisa y confirma.

**Human-in-the-loop:** baja confianza → comprobante queda en `pendiente_revision`.

### Chatbot asistente

**Motor:** Gemini API

Capacidades: consultas en lenguaje natural sobre datos de la empresa, acciones transaccionales según rol del usuario, contexto por tenant. Toda acción se registra en `auditoria_log` con `origen='chatbot'`.

> **Fase K (APROBADA por PM 2026-05-12):** upgrade a "Atajo Inteligente" — escritura completa progresiva con patrón Two-Phase Action. **K.1 backend base implementado el 2026-05-13:** `action_token` TTL 60s persistido en base de datos, `POST /chat/confirmar-accion`, `PATCH /comprobantes/{id}` seguro, `DELETE /pagos/{id}` endurecido a admin y `registrar_cobro`/`registrar_pago` refactorizados a preview + confirmación. Pendiente: widget flotante global (FAB "Aurora", atajo `Ctrl+J`) + página `/asistente` rediseñada. Plan detallado en [`docs/roadmap/FASE_K_CHATBOT_V2.md`](../roadmap/FASE_K_CHATBOT_V2.md).

---

## 13. Modo Offline

Frontend usa **Dexie.js** sobre IndexedDB. Sin conexión: lecturas desde caché local, escrituras encoladas. Al volver conexión: sync automático con Supabase.

**Limitaciones:** OCR y chatbot requieren internet (APIs externas). BOM y reportes financieros funcionan offline si hay caché previo.

---

## 14. Infraestructura y deploy

| Entorno | Frontend | Backend | DB |
|---|---|---|---|
| **Producción** | Vercel (auto desde `main`) | Render/Railway según servicio activo (auto desde `main`) | Supabase prod |
| **Local** | `localhost:3000` | `localhost:8000` | Supabase staging |

### Deploy de la migración BOM

**Estado 2026-05-12:** aplicada en Supabase por Codex y registrada en `schema_migrations`.

1. SQL aplicado: `db/migrations/2026-05-11_bom_recetas.sql`
2. Verificado: tablas `recetas`, `receta_items`, `lotes_produccion`
3. Verificado: columnas `inventario.es_producto_terminado`, `inventario.precio_venta`, `inventario.notas_produccion`
4. Verificado: vistas `v_recetas_detalle`, `v_capacidad_produccion`
5. RLS: no aplicado porque las tablas base del sistema tienen `rowsecurity=false`

Ver [GUIA_SUPABASE_DEPLOY.md](GUIA_SUPABASE_DEPLOY.md) para guía detallada.

### Deploy de documentación SDD

La documentación vive en `docs/sdd/`. Fabri agregó `.github/workflows/deploy-docs.yml` para publicarla con GitHub Pages.

Para activar publicación pública:

1. GitHub → Settings → Pages
2. Source: **GitHub Actions**
3. Ejecutar workflow `Deploy Documentation to GitHub Pages` o pushear cambios en `docs/sdd/**`

---

## 15. Calidad y pruebas

- **Backend:** pytest en `/tests/` — corrida automática en CI
- **Frontend:** TypeScript estricto (`tsc --noEmit`)
- **Build frontend:** `npm run build` debe pasar antes de deploy
- **Smoke DB:** migraciones nuevas deben verificarse con queries de existencia/contrato
- **Bitácora:** toda sesión que toque código, datos productivos o documentación rectora debe registrar fila en `BITACORA_COLABORATIVA.md`

### Última verificación registrada

| Fecha | Verificación | Resultado |
|---|---|---|
| 2026-05-12 | `python -m compileall backend` | OK |
| 2026-05-12 | `python -m pytest -q` | 22 passed en integración Fabri |
| 2026-05-12 | `npm run lint` | OK |
| 2026-05-12 | `npm run build` | OK |
| 2026-05-12 | Migración BOM en Supabase | OK: tablas, columnas y vistas verificadas |

---

## 16. Reglas de negocio críticas

> ⚠️ Estas reglas **no pueden violarse**. Cualquier cambio que las afecte requiere revisión explícita.

### RN-01 — Montos siempre DECIMAL, nunca FLOAT

`DECIMAL(15,2)` en DB, `Decimal` en Python, `decimal.js` en TypeScript.

> ⚠️ **Por qué:** `0.1 + 0.2 = 0.30000000000000004` en float — error inadmisible en contabilidad.

### RN-02 — Soft-delete obligatorio

Clientes, proveedores, inventario, recetas nunca se borran físicamente. Solo se marcan `activo = FALSE`.

### RN-03 — Multi-tenant estricto

Toda query incluye `empresa_id`. JWT define la empresa accesible.

### RN-04 — Un titular por comprobante

`cliente_id` XOR `proveedor_id`. Constraint CHECK en la tabla.

### RN-05 — Saldo pendiente = total − pagado

Suma de pagos no puede superar `monto_total`.

### RN-06 — Auditoría append-only

`auditoria_log` nunca permite UPDATE o DELETE.

### RN-07 — IVA paraguayo: 0%, 5% o 10%

Cualquier otro valor es rechazado en validación.

### RN-08 — Chatbot con trazabilidad completa

Toda acción del chatbot registra en `auditoria_log` con `origen='chatbot'`.

### RN-09 — Una sola receta activa por producto 🆕

`UNIQUE INDEX` en `recetas (empresa_id, producto_id) WHERE activa=TRUE`. Al crear receta nueva, se desactivan las anteriores.

> ⚠️ **Por qué:** el costo unitario debe ser único y trazable a una receta específica.

### RN-10 — IVA report usa `iva_monto` directamente 🆕

Las fórmulas anteriores (`subtotal/11`, `subtotal/21`) asumían BRUTO. Pero el subtotal se guarda como NETO. Fix: usar el campo `iva_monto` que ya está calculado correctamente al crear cada detalle.

> ⚠️ **Por qué:** garantiza consistencia entre lo que ingresa el usuario y lo que reporta IVA.

---

## 17. Glosario técnico

| Término | Significado |
|---|---|
| **BOM (Bill of Materials)** | "Lista de materiales" — receta que define qué insumos y en qué cantidad componen un producto terminado. Permite calcular costo real y planear producción. |
| **Aging Report** | Reporte que clasifica saldos pendientes por antigüedad (días vencidos), típicamente en buckets de 30 días. |
| **P&L (Profit & Loss)** | Estado de Resultados. Muestra ingresos − costos = utilidad del período. |
| **CMV** | Costo de Mercadería Vendida. Lo que cuesta producir lo que vendiste. |
| **Forecast de caja** | Proyección de saldo de caja futuro basada en vencimientos esperados. |
| **HHI (Herfindahl-Hirschman)** | Índice de concentración. Suma de cuadrados de % de cada participante. >2500 = alta concentración. |
| **API REST** | Forma estándar en que el frontend "habla" con el backend usando HTTP y JSON. |
| **JWT** | Credencial digital firmada de 8 horas. |
| **UUID** | Identificador único universal. Permite generar IDs offline sin conflicto. |
| **DECIMAL(15,2)** | Tipo numérico exacto. 15 dígitos, 2 decimales. Sin errores de redondeo binario. |
| **Multi-tenant** | Un sistema sirve a múltiples empresas con datos completamente aislados. |
| **Soft-delete** | Marcar `activo=FALSE` en vez de borrar físicamente. |
| **OCR** | Reconocimiento óptico de caracteres. La IA "lee" una imagen o PDF. |
| **RLS** | Row Level Security. Regla en la DB que filtra automáticamente por empresa. |
| **FastAPI** | Framework Python moderno para APIs REST. Genera Swagger automático en `/docs`. |
| **React Query (TanStack)** | Librería de gestión de llamadas a API: caché, reintentos, stale-while-revalidate. |
| **Recharts** | Librería de gráficos para React. |
| **Cuello de botella** | El insumo que limita la producción. En BOM, el insumo cuyo stock alcanza para menos batches. |
| **RUC** | Registro Único del Contribuyente. Identificador fiscal de empresas en Paraguay. |
| **Timbrado DNIT** | Autorización fiscal paraguaya para emitir facturas legales. Reservado para futura activación. |
| **PYG / Gs.** | Código y símbolo de la moneda paraguaya (Guaraní). |

---

📖 **Más documentación:**

- [Guía de usuario](GUIA_USUARIO.md) — Manual paso a paso para administradores y operadores
- [Análisis de mejoras](ANALISIS_MEJORAS.md) — 24 oportunidades de mejora identificadas
- [Guía de deploy en Supabase](GUIA_SUPABASE_DEPLOY.md) — Cómo aplicar la migración del BOM

> ERP Esplendida PY v6.1 · Mayo 2026 · Propietario — todos los derechos reservados
