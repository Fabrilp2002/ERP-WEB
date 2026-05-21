# Evolución ERP v4.0.0 a v5.0 Cloud

El objetivo es migrar el sistema de una aplicación de escritorio local (PostgreSQL local + Electron) a una aplicación web en la nube (PostgreSQL en Supabase + Next.js en Vercel), simplificando la interfaz de usuario para dispositivos móviles y evolucionando la lógica de facturación.

---

## Revisión de Factibilidad

> Revisión realizada por Claude Sonnet 4.6 el 2026-04-30, contra el código real de `Empresa 1`.

### Correcciones Factuales

El plan original contenía tres afirmaciones que no coinciden con el estado actual del código:

| Afirmación original | Realidad en el código |
|---|---|
| "Migrar de SQLite → Supabase" | La BD ya es **PostgreSQL local** (asyncpg, `localhost:5432`). La migración real es **PG local → Supabase PG** — considerablemente más simple |
| "Agregar soporte para NC/ND" | Fase I (✅ completada) ya implementó Notas de Crédito vinculadas en `backend/routers/pagos.py` |
| "Agregar SUPABASE_URL y SUPABASE_KEY como variables nuevas" | Ya existen en `backend/core/config.py`, solo están vacías — solo hay que llenarlas |

Estos tres puntos simplifican significativamente el trabajo real.

### Evaluación por Sección

#### Sección 1 — Migración de Persistencia (local PG → Supabase) — ✅ VIABLE, baja complejidad
- `config.py` ya tiene `SUPABASE_URL` y `SUPABASE_KEY` definidas
- `database.py` usa SQLAlchemy async con URL configurable por env var — el cambio es solo la cadena de conexión
- Las vistas SQL (`v_saldo_clientes`, `v_saldo_proveedores`) deben existir en el esquema de Supabase — correr `db/migrations/` allí
- **Tiempo estimado:** 1–2 horas

#### Sección 2 — Evolución de Facturación (`estado_pago`) — ✅ VIABLE, complejidad media
- `pagos.py` ya rastrea `saldo_pendiente`; la vista `v_estado_pago_comprobantes` es una extensión directa
- Antes de implementar NC/ND: auditar qué de Fase I ya está para no duplicar
- **Tiempo estimado:** 3–5 horas

#### Sección 3 — UI Mobile-First + Remoción de Electron — ⚠️ VIABLE, mayor complejidad
- Next.js ya tiene `output: 'standalone'` → compatible con Vercel sin cambios en `next.config.js`
- Electron está en `frontend/electron/` (main.js, preload.js, splash.html) y en `package.json` — removerlo requiere limpiar también los scripts de build y las refs a `window.electronAPI`
- El `Sidebar.tsx` ya tiene menú desplegable ("Herramientas Avanzadas") — la Bottom Tab Bar es adición nueva
- **Tiempo estimado:** 8–12 horas

### Punto Ciego Crítico — Almacenamiento de Archivos en la Nube

**El plan original no menciona esto y es bloqueante para producción.**

**Aclaración técnica importante**: el OCR **no** requiere Storage. Las imágenes que llegan a `/ocr/extraer` se convierten a base64 en memoria y se envían directo a Gemini (`backend/services/ocr.py:778–819`), nunca tocan disco. Storage solo se necesita para:

- `adjuntos/comprobantes/` (subidas vinculadas a `backend/routers/adjuntos.py`)
- `adjuntos/pagos/` (idem)
- `logos/` (logo de empresa, gestionado en `backend/routers/empresa.py`)

Archivos a tocar para reemplazar disco por Storage:
- `backend/routers/adjuntos.py` — reescribir subida/borrado/URL
- `backend/routers/empresa.py` — idem para logo
- `backend/main.py` — quitar `app.mount("/static", ...)` (ya no sirve archivos locales)
- `backend/core/paths.py` — eliminar tras la migración

| Opción | Complejidad | Costo |
|---|---|---|
| Supabase Storage | Baja | Gratis hasta 1 GB |
| Cloudflare R2 | Media | Gratis hasta 10 GB |
| Mantener solo referencias URL | Baja | Sin almacenamiento nuevo |

**Recomendación:** Supabase Storage. Bucket `adjuntos` privado con signed URLs (datos sensibles), bucket `logos` público.

---

## Decisiones de Arquitectura

| Componente | Decisión | Notas |
|---|---|---|
| **Auth** | JWT custom (`python-jose` HS256 + bcrypt) — permanece | Ver `backend/core/security.py:4,32,37`. **No** migrar a Supabase Auth |
| **Modo offline** | Dexie/IndexedDB permanece sin cambios | Browser-side (`frontend/src/lib/offline.ts`); funciona idéntico en Vercel |
| **Backend** | FastAPI long-running en Railway o Render | NO usar Vercel Functions: el server es stateful + async + con pool de conexiones |
| **Frontend** | Next.js 14 en Vercel Hobby | Ya tiene `output: 'standalone'` |
| **DB** | Supabase Postgres puerto **5432 (Session mode)** | Recomendado para `asyncpg` long-running |
| **Storage** | Supabase Storage | `adjuntos` (privado, signed URLs) + `logos` (público) |
| **Chatbot** | Stateless, migra automáticamente con la BD | `backend/services/chatbot.py` no requiere cambios |

### Apéndice — Connection pooling con pgBouncer (puerto 6543)

Solo si en algún momento se mueve a serverless. `asyncpg` rompe con prepared statements bajo pgBouncer en modo Transaction:

```python
# backend/core/database.py — configuración alternativa para puerto 6543
from sqlalchemy.pool import NullPool
engine = create_async_engine(
    DATABASE_URL,
    poolclass=NullPool,
    connect_args={"statement_cache_size": 0, "prepared_statement_cache_size": 0},
)
```

**Por defecto, usar 5432.** El puerto 6543 sin esta receta produce `DuplicatePreparedStatementError`.

---

## Migración de Datos Productivos

1. **Dump del PG local**:
   ```bash
   pg_dump --no-owner --no-acl --clean --if-exists -d erp_db -f dump.sql
   ```
2. **Crear proyecto Supabase**, anotar `DATABASE_URL` (puerto 5432).
3. **Restaurar el dump** (alternativa schema+data):
   ```bash
   psql "$SUPABASE_DB_URL" -f dump.sql
   ```
   Alternativa schema-first: ejecutar las 10 migraciones en orden cronológico (ver `db/migrations/` ordenado por fecha) + nueva migración #11 (`v_estado_pago_comprobantes`).
4. **Verificar conteos** post-restore en cada tabla crítica:
   - `clientes`, `comprobantes`, `asientos_contables`, `pagos`, `usuarios`, `empresas`, `productos`
5. **Migrar archivos físicos** de `resources/adjuntos/**` y `resources/logos/**` a Supabase Storage con script único (nuevo: `tools/scripts/migrar_adjuntos_a_storage.py`).
6. **Reescribir rutas** en BD: `UPDATE comprobantes SET ruta_adjunto = REPLACE(ruta_adjunto, '/static/adjuntos/', 'https://<proj>.supabase.co/storage/v1/object/public/adjuntos/')` (idem para `pagos.ruta_adjunto`).

---

## Variables de Entorno Completas

| Variable | Backend / Frontend | Notas |
|---|---|---|
| `DATABASE_URL` | Backend | `postgresql+asyncpg://postgres:<pwd>@<host>:5432/postgres?ssl=require` |
| `SUPABASE_URL` | Backend + Frontend | `https://<proj>.supabase.co` |
| `SUPABASE_KEY` | Backend (service role) | **Nunca** exponer al cliente |
| `NEXT_PUBLIC_SUPABASE_URL` | Frontend | Solo si se accede a Storage desde el browser |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Frontend | Idem (anon key, no service role) |
| `JWT_SECRET_KEY` | Backend | **Rotar** vs el local antes del primer deploy |
| `JWT_ALGORITHM` | Backend | `HS256` |
| `GEMINI_API_KEY` | Backend | También vive en `key_store` |
| `CORS_ORIGINS` | Backend | JSON array con dominio Vercel exacto |
| `NEXT_PUBLIC_API_URL` | Frontend | URL pública del backend en Railway/Render |

---

## Estrategia de Desarrollo Paralelo

El desarrollo v5 se hace **en una carpeta separada**, sin tocar `Empresa 1` en ningún momento.

### Carpeta destino

```
C:\Users\gfcar\Desktop\IA\ERP_v5_Cloud\
```

### Pasos para inicializar el entorno

1. **Copiar la carpeta** `C:\Users\gfcar\Desktop\IA\Empresa 1` completa a `C:\Users\gfcar\Desktop\IA\ERP_v5_Cloud` (copiar/pegar en el Explorador de Windows)
2. **Editar `backend/.env`** en la nueva carpeta → llenar `SUPABASE_URL` y `SUPABASE_KEY` con las credenciales reales del proyecto Supabase
3. **Editar `frontend/.env.local`** → cambiar `NEXT_PUBLIC_API_URL` a `http://localhost:8001` (puerto distinto al de `Empresa 1`)
4. **Arrancar el backend** en puerto 8001: `uvicorn main:app --port 8001`
5. **Arrancar el frontend** normalmente: `npm run dev`

**Lo que NO se toca en `Empresa 1`:**
- El `.env` de `Empresa 1` no se modifica
- La BD PostgreSQL local de `Empresa 1` no se altera
- Los dos proyectos pueden correr simultáneamente en puertos distintos (8000 y 8001)

---

## Cambios Propuestos (Plan Original Actualizado)

### 1. Migración de Persistencia (local PG → Supabase)

Se invierte la prioridad de la base de datos. Supabase (PostgreSQL en la nube) será la base principal y SQLite quedará solo como fallback de desarrollo sin conexión.

#### [MODIFY] `backend/core/config.py`
- Llenar `SUPABASE_URL` y `SUPABASE_KEY` con las credenciales del proyecto Supabase
- Ampliar `ALLOWED_ORIGINS` para incluir el dominio de Vercel
- La lógica para construir la cadena de conexión PG ya existe

#### [MODIFY] `backend/core/database.py`
- Actualizar para usar dinámicamente SQLite (dev sin conexión) o Supabase PG según las env vars

#### [MODIFY] `backend/core/paths.py`
- Reemplazar lógica `%APPDATA%` por Supabase Storage para adjuntos y logos

#### [NEW] `db/migrations/2026-04-30_estado_pago_nc_nd.sql`
- Vista `v_estado_pago_comprobantes` que calcula dinámicamente si una factura está pagada, parcialmente pagada o no pagada
- Correr también todas las migraciones previas (`db/migrations/`) en el proyecto de Supabase

---

### 2. Evolución de la Facturación

Se reemplaza el estado "confirmado" como indicador de pago por el campo dinámico `estado_pago`.

#### [MODIFY] `backend/models/schemas.py`
- Agregar `estado_pago: str` y `comprobante_origen_id: UUID | None` a los schemas de lectura

#### [MODIFY] `backend/routers/comprobantes.py`
- La consulta SQL para el listado devolverá `estado_pago` calculado desde la vista
- Endpoints NC/ND: auditar primero qué de Fase I ya está implementado

#### [MODIFY] `backend/routers/pagos.py`
- Al registrar un pago, la respuesta devolverá el nuevo `estado_pago` actualizado

---

### 3. UI/UX Simplificada y Mobile-First

El frontend se despliega en Vercel, eliminando la dependencia de Electron.

#### [MODIFY] `frontend/package.json`
- Eliminar: `electron`, `electron-builder`, `concurrently` (usado para correr Electron)
- Limpiar scripts de build NSIS
- Mantener: Next.js, React, Tailwind, TanStack Query, Zustand

#### [MODIFY] `frontend/next.config.js`
- Mantener `output: 'standalone'` (compatible con Vercel)
- Habilitar optimización de imágenes (quitar `unoptimized: true`)
- Configurar `NEXT_PUBLIC_API_URL` para apuntar al backend desplegado

#### [DELETE] `frontend/electron/` (carpeta completa)
- Eliminar `main.js`, `preload.js`, `splash.html`
- Eliminar referencias a `window.electronAPI` en el código frontend

#### [MODIFY] `frontend/src/components/Sidebar.tsx`
- **Mobile** (`<768px`): Bottom Tab Bar con 4–5 accesos rápidos + ícono de hamburguesa
- **Desktop**: Sidebar izquierdo existente (sin cambios estructurales)
- Módulos avanzados agrupados en desplegable "Más herramientas"

#### [MODIFY] `frontend/src/app/(app)/layout.tsx` & `frontend/src/app/globals.css`
- Safe area padding inferior para Bottom Tab Bar en móviles
- Dark mode refinado, tipografía Inter, Glassmorphism
- Badges semánticos dinámicos para `estado_pago`: `pagado` (verde) / `pago_parcial` (amarillo) / `no_pagado` (rojo)

#### [MODIFY] `frontend/src/app/(app)/comprobantes/page.tsx`
- Reemplazar badge "Confirmado" por badge dinámico de `estado_pago`

---

## Orden de Implementación

1. **Copia de carpeta** `Empresa 1` → `ERP_v5_Cloud`. Editar `backend/.env` y `frontend/.env.local` con valores Supabase.
2. **Crear proyecto Supabase** y correr las 10 migraciones SQL en orden cronológico (`db/migrations/` por fecha) + nueva migración `v_estado_pago_comprobantes`.
3. **Validar conexión local**: `uvicorn` apuntando a Supabase puerto 5432, test de endpoints CRUD básicos.
4. **Migración de datos** (sección "Migración de Datos Productivos").
5. **Auditar NC/ND existentes (Fase I)**: confirmar que las vinculaciones siguen consistentes en Supabase antes de implementar `v_estado_pago_comprobantes`.
6. **Reescribir `backend/routers/adjuntos.py`** para Supabase Storage (subida + delete + URL firmada).
7. **Reescribir manejo de logo** (`backend/routers/empresa.py`) con el mismo patrón.
8. **Quitar `app.mount("/static", ...)`** de `backend/main.py` y eliminar usos de `backend/core/paths.py`.
9. **Frontend**: ajustar `NEXT_PUBLIC_API_URL` y deploy a Vercel.
10. **Backend**: deploy a Railway/Render con health check `/health`.
11. **Smoke test end-to-end** (sección "Definition of Done").
12. **Eliminar archivos del build desktop** (sección "Archivos a Eliminar").

---

## Archivos Críticos a Modificar

| Archivo | Cambio | Complejidad |
|---|---|---|
| `backend/core/config.py` | Llenar Supabase vars; ampliar CORS; limpiar overrides Electron | Baja |
| `backend/core/database.py` | URL Supabase + parámetros SSL/pool | Baja |
| `backend/core/paths.py` | Eliminar tras migrar adjuntos y logos a Storage | Baja |
| `backend/main.py` | Quitar `app.mount("/static", ...)` | Baja |
| `backend/routers/adjuntos.py` | **Reescribir completo** para Supabase Storage | Alta |
| `backend/routers/empresa.py` | Logo de empresa a Storage | Media |
| `backend/services/chatbot.py` | Verificar que sigue funcionando con BD nueva (sin cambios esperados) | Nula |
| `backend/models/schemas.py` | Agregar `estado_pago`, `comprobante_origen_id` | Baja |
| `backend/routers/comprobantes.py` | Devolver `estado_pago`; revisar NC/ND | Media |
| `backend/routers/pagos.py` | Devolver `estado_pago` actualizado | Baja |
| `db/migrations/` | Nueva migración `v_estado_pago_comprobantes` | Baja |
| `frontend/package.json` | Eliminar Electron + scripts NSIS | Media |
| `frontend/next.config.js` | Ajustar para Vercel | Baja |
| `frontend/electron/` | Eliminar carpeta completa | Baja |
| `frontend/src/components/Sidebar.tsx` | Bottom Tab Bar mobile | Alta |
| `frontend/src/app/(app)/layout.tsx` | Safe area + Dark mode | Media |
| `frontend/src/app/(app)/comprobantes/page.tsx` | Badges dinámicos estado_pago | Baja |

---

## Registro de Riesgos

| Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|
| Supabase free tier 500 MB se queda corto con adjuntos | Media | Alto | Monitorear bucket; plan Pro $25/mes si hace falta |
| Cold start backend Railway free tier | Alta | Medio | Plan paid $5–7/mes o keep-alive ping cada 5 min |
| `asyncpg` rompe con pgBouncer si alguien cambia a 6543 sin la receta | Media | Alto | Documentar en `database.py`; ver apéndice connection pooling |
| Latencia OCR (Gemini desde Railway) | Baja | Medio | Ya existe `timeout=120s` en `_extraer_gemini` |
| Pérdida de offline por la migración | Nula | — | Verificado: Dexie es browser-side y no se toca |
| URLs `/static/adjuntos/...` rotas en datos viejos | Alta | Medio | Script de migración + `UPDATE` SQL para reescribir `comprobantes.ruta_adjunto` y `pagos.ruta_adjunto` |
| `JWT_SECRET_KEY` reutilizada del local | Media | Alto | Rotar antes del primer deploy |

---

## Archivos a Eliminar en la versión cloud

- `frontend/electron/` (carpeta completa)
- `backend.spec`
- `tools/build_exe.py`
- `tools/CREAR_ACCESO_DIRECTO.ps1`
- `INSTALADOR_README.md`
- `INSTALAR_ACCESO_DIRECTO.bat`
- `INICIAR_ERP.vbs`
- `start_all.bat`, `start_backend.bat`, `start_frontend.bat`
- `pyinstaller_out.txt`, `pyinstaller_out2.txt`
- En `frontend/package.json`: bloque `"build"` (electron-builder), scripts `electron:dev` y `electron:build`, devDeps `electron`, `electron-builder`, `wait-on`, `concurrently` (verificar que no se usen en otros scripts)
- `backend/core/paths.py` tras migrar adjuntos y logos
- En `backend/core/config.py`: lógica de `ERP_ENV_FILE` y `ERP_RESOURCES_DIR` (simplificar a `.env` plano)

---

## Estimación

**Tiempo de desarrollo**: ~25–35h totales
- Storage rewrite (adjuntos + logos): ~8h
- Migración de datos productivos: ~4h
- Deploy + smoke test: ~4h
- Limpieza de archivos desktop: ~3h
- UI mobile-first (Bottom Tab Bar + badges): ~6h
- Contingencia: ~10h

**Costo mensual estimado**:
- Supabase free: $0 (500 MB DB + 1 GB Storage). Pro $25/mes si crece.
- Vercel Hobby: $0.
- Railway/Render: $0 con cold start, o $5–7/mes always-on.

---

## Definition of Done

- [ ] Backend en Railway responde 200 a `/health`
- [ ] Frontend Vercel carga en <3s en cold cache
- [ ] Login + JWT funciona desde móvil real (CORS + HTTPS validados)
- [ ] Crear comprobante + pago + ver `estado_pago` actualizado
- [ ] Subir adjunto y descargarlo desde URL Supabase Storage (público o firmado)
- [ ] OCR end-to-end con factura real
- [ ] Chatbot devuelve datos reales de la BD migrada
- [ ] Modo offline (Dexie) sigue encolando mutaciones sin internet y sincroniza al volver
- [ ] Conteos de filas en Supabase = conteos en local (clientes, comprobantes, asientos, pagos, usuarios, empresas, productos)
- [ ] Bitácora actualizada con la entrada de migración

---

## Verificación Planificada

### Pruebas Locales
- **Backend**: `uvicorn` en puerto 8001 apuntando a Supabase — validar CRUD completo con SQLite local como fallback
- **Frontend**: `npm run dev` y `npm run build` sin errores, sin referencias a Electron

### Verificación Manual
1. Abrir `http://localhost:3000` en PC → Sidebar colapsable funciona
2. DevTools → vista móvil → Bottom Tab Bar visible, navegación correcta
3. Cargar una factura + registrar pago parcial → badge "Pago Parcial" aparece
4. Subir un adjunto → verificar que se guarda en Supabase Storage
5. Aplicar NC sobre una factura → saldo pendiente se reduce correctamente

### Verificación en Producción (post-deploy)
- Backend en Railway/Render responde en la URL de producción
- Frontend en Vercel conecta correctamente al backend
- Login funciona desde móvil real
- Imágenes adjuntas accesibles desde URL de Supabase Storage
