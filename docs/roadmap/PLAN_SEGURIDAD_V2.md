# Plan de Seguridad v2 — Siguiente capa de hardening

> **Versión:** v2.0 · 2026-05-13
> **Autor:** Claude (auditoría) · Aprobación pendiente: PM
> **Estado:** 📋 Planificado — sin implementar todavía
> **Sucesor de:** `PLAN_SEGURIDAD.md` (Sprint 1, ya implementado 2026-05-06)
> **Tiempo estimado:** 14–18 h reales · escalonable en 3 sprints cortos

---

## 0. Resumen ejecutivo (para el PM, sin código)

El ERP **no está vulnerable de forma obvia**. Sprint 1 (mayo 2026) ya cubrió las capas básicas: contraseñas fuertes, bloqueo por intentos fallidos, headers de seguridad, auditoría con IP y JWT firmado. Para una PyME en Paraguay esto está **por encima del promedio**.

Sin embargo, hay **6 brechas reales** que conviene cerrar antes de invitar más usuarios o aumentar el valor de los datos que maneja:

| # | Brecha | Riesgo si no se hace | Esfuerzo |
|---|---|---|---|
| 1 | **Secretos sin rotar** desde la primera puesta en producción | Si alguno quedó en un log o chat, alguien podría usarlos | 30 min |
| 2 | **Sin alertas de vulnerabilidades** en las dependencias | Una librería con bug crítico puede pasar meses sin parchearse | 5 min |
| 3 | **Aislamiento entre empresas depende 100% del código** | Un bug en una query nueva podría exponer datos de una empresa a otra | 4–6 h |
| 4 | **Token de sesión guardado en el navegador** (localStorage) | Cualquier script malicioso inyectado puede robarlo | 2–3 h |
| 5 | **Sin firewall web** (WAF) ni protección contra ataques de tráfico | Un ataque de fuerza bruta o DDoS básico tumba el servicio | 1 h |
| 6 | **Sin segundo factor de autenticación** (2FA) | Si alguien obtiene una contraseña, entra sin obstáculo adicional | 6 h |

Las primeras dos son **gratis y se hacen esta semana**. Las cuatro siguientes son inversiones más grandes, ordenadas por impacto.

---

## 1. Estado actual — qué ya está hecho (Sprint 1)

✅ **Aplicado y en producción desde 2026-05-06:**

| Capa | Implementación |
|---|---|
| Hash de passwords | bcrypt cost 12 |
| Política de password | 8+ chars, mayúscula, minúscula, número, símbolo |
| Bloqueo por fuerza bruta | 5 fallos / 10 min → 15 min lockout + email |
| Timing attack | Hash dummy en login fallido |
| Rate limit | Login 5/min, reset 5/min, confirm 10/min |
| JWT | HS256, 2 horas de vida (`JWT_EXPIRE_MINUTES=120`) |
| Security headers | HSTS, CSP, X-Frame-DENY, nosniff, Referrer, Permissions |
| Headers también en Vercel | Vía `next.config.js` |
| CORS | Solo dominio Vercel autorizado |
| Idle timeout | 30 min sin actividad → cierre con aviso |
| Auditoría con IP/UA | XFF último IP (no falsificable), retención 90 días |
| Roles | admin/operador/viewer chequeados en backend |
| Acciones del chatbot | Two-Phase con `action_token` TTL 60s + uso único |
| DELETE /pagos | Admin-only (K.1) |
| Soft-delete | Clientes, proveedores, inventario, recetas — `activo=false` |
| Anulación de comprobantes | Bloqueada si tiene cobros/pagos |

**Calificación esperada en securityheaders.com:** A

---

## 2. Brechas identificadas y plan de cierre

### 🔴 P0 — Esta semana, gratis

#### 2.1 Rotar secretos antiguos

**Por qué:** la bitácora del 2026-05-09 menciona que `.render-token` debía rotarse y borrarse del disco local. No hay confirmación de que se hizo. Cualquier secreto que alguna vez estuvo en chat, log o commit antiguo es potencialmente conocido.

**Qué rotar:**

| Secreto | Dónde | Cómo |
|---|---|---|
| `JWT_SECRET_KEY` | Render env vars | Generar nuevo con `openssl rand -hex 32` |
| `GEMINI_API_KEY` | Render env vars | Revocar en Google AI Studio + generar uno nuevo |
| Service Role Key de Supabase | Render env vars | Project Settings → API → Reset |
| Token de Render API | Local + Render | Render → Account → API Keys → Regenerate |
| `RESEND_API_KEY` (si aplica) | Render env vars | Resend dashboard → API Keys |

**Plan paso a paso:**

1. Generar todos los nuevos secretos primero (sin reemplazar).
2. Actualizar Render env vars (causa un redeploy automático ~2 min).
3. Verificar `/health` y login.
4. Revocar los viejos (este orden evita downtime).
5. Borrar archivos locales: `.render-token`, cualquier `.env` con secretos.
6. Confirmar en bitácora que se ejecutó.

**Tiempo:** 30 min · **Riesgo:** muy bajo si se sigue el orden

---

#### 2.2 Activar alertas automáticas de seguridad de GitHub

**Por qué:** hoy `npm audit` se corre a mano. Una librería con CVE crítico puede tardar semanas en detectarse.

**Qué activar:**

- GitHub → Repo → Settings → **Security & analysis**:
  - ☑ Dependency graph
  - ☑ Dependabot alerts
  - ☑ Dependabot security updates (PR automáticos para fixes)
  - ☑ Code scanning (con CodeQL gratis para repos públicos, o configurar Semgrep en privado)
  - ☑ Secret scanning (avisa si commiteás un token por error)

**Tiempo:** 5 min · **Riesgo:** cero · **Hace falta acceso de admin del repo**

---

### 🟠 P1 — Sprint próximo (4–6 h cada uno)

#### 2.3 Activar Row Level Security (RLS) en Supabase

**Por qué:** hoy el aislamiento entre empresas depende de que **cada query** del backend incluya `WHERE empresa_id = $1`. Es algo que el desarrollador tiene que recordar siempre. Un solo olvido en un endpoint nuevo y los datos de una empresa son visibles para otra.

RLS es una **red de seguridad a nivel base de datos**: aunque el backend olvide el filtro, la DB lo aplica sola.

**Estado actual:** la bitácora del 2026-05-12 confirma que tablas como `clientes`, `comprobantes`, `inventario`, `proveedores` tienen `rowsecurity=false`. RLS está apagado.

**Cómo activarlo:**

1. **Crear migración** `db/migrations/2026-05-14_enable_rls.sql`:

```sql
-- Para cada tabla con empresa_id:
ALTER TABLE clientes ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON clientes
  USING (empresa_id = current_setting('app.current_empresa', true)::uuid);

-- Repetir para: proveedores, inventario, comprobantes, detalle_comprobantes,
-- pagos, recetas, receta_items, lotes_produccion, auditoria_log, etc.
```

2. **Backend setea el contexto por request:**

```python
# backend/middleware/tenant_context.py (NUEVO)
async def tenant_context_middleware(request, call_next):
    user = obtener_usuario_actual(request)
    if user:
        async with db_session() as session:
            await session.execute(
                text("SET LOCAL app.current_empresa = :eid"),
                {"eid": str(user.empresa_id)}
            )
    return await call_next(request)
```

3. **Probar con superuser y con usuario normal:** crear datos de empresa A, loguearse como usuario de empresa B y confirmar que NO los ve.

**Riesgo:** moderado — hay que aplicar migración y probar exhaustivamente. **Hacerlo primero en staging.** Si algo se rompe, `ALTER TABLE ... DISABLE ROW LEVEL SECURITY` lo revierte en segundos.

**Tiempo:** 4–6 h · **Impacto:** alto (cierra una clase entera de bugs futuros)

---

#### 2.4 Cloudflare gratis delante de Vercel + Render

**Por qué:** hoy no hay nada entre el atacante y la app. Cloudflare gratis agrega:

- **WAF básico** (filtra payloads sospechosos: SQL injection, XSS, path traversal)
- **Protección contra DDoS** (los ataques de tráfico básico ni llegan al backend)
- **Bot Fight Mode** (bloquea scrapers y bots maliciosos)
- **Cacheo de assets estáticos** (mejora velocidad además de reducir carga)
- **Country blocking** opcional (si la empresa solo opera en Paraguay, bloquear el resto reduce 99% del ruido)

**Cómo:**

1. Crear cuenta en Cloudflare (gratis).
2. Agregar el dominio (apuntar nameservers de Cloudflare).
3. Configurar:
   - Proxy ON (nube naranja) para Vercel y backend
   - SSL: Full (strict)
   - Bot Fight Mode: ON
   - WAF rules: paquete gratis activado
   - Country block opcional (allow PY, block resto)
4. Verificar que la app sigue funcionando.

**Tiempo:** 1 h · **Costo:** 0 · **Impacto:** alto contra atacantes oportunistas

---

#### 2.5 Migrar JWT de localStorage a httpOnly cookie

**Por qué:** hoy el token vive en `localStorage`. Cualquier JavaScript que ejecute en el dominio puede leerlo con `localStorage.getItem('auth')`. Si alguien logra inyectar un script (paquete npm comprometido, biblioteca CDN, XSS en algún campo), te roba la sesión.

`httpOnly` cookies son **invisibles para JavaScript**. El browser las manda solas en cada request, pero ningún script las puede leer.

**Cómo:**

1. **Backend** (`backend/routers/auth.py`):

```python
@router.post("/token")
async def login(...):
    token = generar_jwt(usuario)
    response.set_cookie(
        key="erp_session",
        value=token,
        httponly=True,
        secure=True,        # solo HTTPS
        samesite="strict",  # no se manda en requests cross-site
        max_age=7200,       # 2 horas
        path="/",
    )
    return {"ok": True, "usuario_id": ..., "rol": ..., "empresa_id": ...}
    # Ya no devolvemos access_token en el body
```

2. **Frontend** (`frontend/src/lib/auth.ts`):
   - Eliminar `localStorage.setItem('auth', token)`.
   - El interceptor de axios ya no agrega `Authorization` header (el cookie va solo).
   - Importante: configurar axios con `withCredentials: true`.

3. **Backend lee el cookie** en vez de el header `Authorization`:

```python
# backend/core/security.py
def obtener_usuario_actual(request: Request) -> Usuario:
    token = request.cookies.get("erp_session")
    if not token:
        # fallback a Authorization para clientes que no soportan cookies
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "): token = auth[7:]
    if not token:
        raise HTTPException(401)
    return verificar_jwt(token)
```

4. **CORS** debe permitir credentials:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],  # NO wildcard con credentials
    allow_credentials=True,
    ...
)
```

**Riesgo:** medio — hay que migrar todo el frontend al mismo tiempo. **Hacerlo primero en staging.**

**Tiempo:** 2–3 h · **Impacto:** medio-alto (cierra el vector principal de XSS-then-steal)

---

### 🟡 P2 — Sprint posterior

#### 2.6 CSP estricta sin `unsafe-inline`

**Por qué:** la CSP actual probablemente tiene `'unsafe-inline'` para scripts (default de Next.js). Eso permite que cualquier `<script>` injectado se ejecute, lo cual es precisamente lo que la CSP debe prevenir.

**Cómo:**

1. Generar nonces por request en Next.js middleware.
2. Inyectar nonce en todos los scripts inline de la app.
3. CSP: `script-src 'self' 'nonce-{random}'` (sin `unsafe-inline`).
4. Probar exhaustivamente — esto rompe cosas si no se hace bien.

**Tiempo:** 2–4 h · **Impacto:** medio

---

#### 2.7 2FA opcional (TOTP)

**Por qué:** si alguien obtiene una contraseña (phishing, leak, post-it), entra. Con 2FA además necesita el celular del usuario.

**Decisión documentada en Sprint 1: NO 2FA.** Razones: pocos usuarios, fricción adicional, prioridad de simplicidad. Esa decisión sigue siendo razonable para 2-3 admins, pero conviene **dejarlo preparado para activarse** cuando la empresa crezca.

**Cómo (modo opcional, no obligatorio):**

1. Página `/perfil/seguridad`: botón "Activar verificación en dos pasos".
2. Backend: `pyotp` + tabla `usuarios_2fa (usuario_id, secret, activo, backup_codes)`.
3. Mostrar QR para escanear con Google Authenticator / Authy.
4. Después del primer login con password correcta, si el usuario tiene 2FA activo, pedir código de 6 dígitos.
5. Generar 10 códigos de respaldo de un solo uso.

**Tiempo:** 6 h · **Impacto:** alto cuando se active

---

#### 2.8 Audit con OWASP ZAP

**Por qué:** lo anterior tapa lo que sabemos. Un escaneo automático con ZAP encuentra cosas que se nos pasaron: parámetros sin sanitizar, errores leaking en respuestas, headers faltantes en endpoints específicos, etc.

**Cómo:**

1. `docker run -t owasp/zap2docker-stable zap-baseline.py -t https://erp-web-cyan-delta.vercel.app`
2. Revisar reporte HTML.
3. Cerrar los hallazgos High y Medium.

**Tiempo:** 2 h primera vez · **Impacto:** medio

---

#### 2.9 Backup verificado de Supabase

**Por qué:** Supabase free retiene backups 7 días. No es lo mismo "haber tenido backup" que "haber probado que se puede restaurar". Conviene hacer un drill anual.

**Cómo:**

1. Crear proyecto staging en Supabase.
2. Restaurar el último backup de producción ahí.
3. Verificar que el frontend conectado a staging funciona.
4. Documentar el procedimiento en `docs/DRP.md`.

**Tiempo:** 2 h · **Impacto:** alto si alguna vez se necesita

---

## 3. Calendario sugerido

### Sprint A (esta semana, ~1 h total)
- 2.1 Rotar secretos
- 2.2 Activar alertas GitHub

### Sprint B (próxima semana, ~5–7 h)
- 2.3 RLS en Supabase
- 2.4 Cloudflare gratis

### Sprint C (mes próximo, ~5 h)
- 2.5 JWT en httpOnly cookie
- 2.6 CSP estricta

### Sprint D (cuando la empresa crezca, ~8 h)
- 2.7 2FA opcional
- 2.8 Audit con ZAP
- 2.9 Drill de backup

---

## 4. Definition of Done por brecha

| # | Brecha cerrada cuando… |
|---|---|
| 2.1 | Todos los secretos rotados; bitácora actualizada confirmando ejecución |
| 2.2 | Settings de GitHub muestra ☑ verde en todos los items de "Security & analysis" |
| 2.3 | Probado: usuario de empresa A no ve datos de empresa B aunque manipule la URL |
| 2.4 | `curl https://app | head -i` muestra `cf-ray` y `cf-cache-status` headers |
| 2.5 | localStorage sin `auth`; cookies muestra `erp_session` con HttpOnly=true |
| 2.6 | CSP header no contiene `'unsafe-inline'` en script-src |
| 2.7 | Login con 2FA activo pide el código; sin código no entra; backup codes funcionan una vez |
| 2.8 | Reporte ZAP sin High/Medium pendiente |
| 2.9 | `docs/DRP.md` con procedimiento testeado y fecha de último drill |

---

## 5. Métricas para medir progreso

- **Calificación en securityheaders.com:** debe mantenerse en A o subir a A+
- **`npm audit`:** 0 high/critical
- **`pip-audit`:** 0 high/critical
- **Dependabot alerts:** 0 abiertas
- **Cloudflare dashboard:** % de requests bloqueadas (espera-ble: 1-5% bots)

---

## 6. Lo que NO entra en este plan (y por qué)

| Tema | Por qué se posterga |
|---|---|
| WebAuthn / passkeys | 2FA TOTP cubre 99% del caso. WebAuthn requiere infra adicional |
| Hardware security keys (Yubikey) | Solo si el PM lo pide explícitamente |
| Pentest profesional pago | $3-8k USD. Vale la pena post 2.1–2.7 |
| Compliance formal (ISO 27001, SOC2) | Requiere auditor externo, 6+ meses |
| Cifrado end-to-end de datos sensibles | Postgres ya cifra en reposo; el costo de implementar E2E supera el riesgo actual |

---

## 7. Cumplimiento normativo Paraguay

- **DNIT timbrado electrónico:** preparado en DB (`timbrado_id` nullable), no activo. Cuando se active, hay requerimientos adicionales que se agregarán a este plan.
- **Ley 1682/2001 — Protección de datos personales:** ya cubierto por export-datos y delete-account (Sprint 1). Mantener funcionando.
- **Resolución BCP 6/2022:** no aplica (no somos institución financiera).

---

## 8. Cosas que el PM debe decidir antes de arrancar

| # | Decisión | Opciones |
|---|---|---|
| A | ¿Activar 2FA ahora o cuando crezca la empresa? | (1) Ahora obligatorio para admin, (2) Ahora opcional para todos, (3) Postponer |
| B | ¿Country-block en Cloudflare? | (1) Solo PY, (2) PY+AR+BR+UY, (3) Sin block |
| C | ¿Migración a Render Pro? | $7/mes elimina cold start y mejora SLA |
| D | ¿Pentest profesional? | Cuando los datos manejen valor mayor |

---

## 9. Estado actual y siguiente paso

- ✅ Plan documentado
- ⏳ Pendiente aprobación del PM y decisiones de la sección 8
- 🚀 Si aprueba P0: arrancar mañana mismo con 2.1 (rotar secretos) — 30 min, sin código nuevo
