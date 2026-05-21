# Plan de Seguridad — ERP_Web

> **Última actualización**: 2026-05-05
> **Estado**: Aprobado · pendiente de implementación
> **Autor**: gfcar (PM) · Claude Sonnet 4.6 (auditoría + diseño)
> **Tiempo estimado**: 12 horas distribuidas en 5 fases

---

## 0 · Resumen ejecutivo

`ERP_Web` ya está en producción y manejará datos sensibles de un negocio paraguayo: clientes, RUC, montos, facturas, adjuntos. Una auditoría inicial dio **7/10**: tiene fundamentos sólidos pero faltan defensas perimetrales. Este plan eleva la calificación a **9.5/10** sin agregar fricción visible al usuario.

### Decisiones de producto (confirmadas con el PM)

| Pregunta | Decisión |
|---|---|
| ¿2FA / segundo factor? | **No** — solo contraseña como factor único |
| ¿Política de password? | **Estricta clásica**: 8+ chars, ≥1 mayús, ≥1 número, ≥1 símbolo |
| ¿Lockout? | **5 fallos en 10 min → cuenta bloqueada 15 min + email al usuario** |
| ¿Privacidad / auditoría? | **Auditoría completa con IP + dispositivo · IPs borradas tras 90 días** |

### Lo que NO se cambia

- Auth: **JWT custom** (HS256 + bcrypt) — no migrar a OAuth ni Supabase Auth.
- Sesiones: JWT en `localStorage` (compromiso: mitigado con CSP + idle timeout).
- Login flow: **solo usuario + contraseña** — sin Google login, sin magic link.

---

## 1 · Auditoría inicial (estado actual: 7/10)

### ✅ Fortalezas detectadas
- Bcrypt 12 rounds en hashing de passwords
- JWT HS256 con TTL 8 h, claims `sub` + `empresa_id` + `rol`
- RBAC robusto (admin/operador/viewer) en 24/24 routers
- Tokens de reset / invitación: single-use, hash SHA-256 en BD, expiración 24 h / 7 días
- ORM con bound parameters (sin SQL injection real)
- Supabase Storage privado para adjuntos con signed URLs (TTL 1 h)
- Pydantic v2.11 con validación tipo + constraints
- `.env` en `.gitignore`, secrets no se loguean

### ⚠️ Gaps críticos (la lista de hardening)
1. Sin rate limiting → vulnerable a fuerza bruta en `/auth/token`
2. Sin lockout de cuenta tras N fallos
3. Sin security headers (HSTS, CSP, X-Frame-Options, etc.)
4. Auditoría no captura IP origen ni User-Agent (ya hay columna `ip_origen` pero nunca se llena)
5. Login con timing attack: bcrypt no se ejecuta para usuarios inexistentes → diferencia de tiempo medible
6. JWT_SECRET y password Supabase aparecieron en chat → necesitan rotación
7. Sin idle timeout frontend
8. Sin política de retención (logs crecen sin límite)
9. Sin endpoints de export/delete account (privacidad GDPR-like)

---

## 2 · Stack y herramientas a sumar

| Necesidad | Librería | Tamaño | Notas |
|---|---|---:|---|
| Rate limiting | `slowapi==0.1.9` | ~30 KB | wrapper de Starlette |
| Security headers | middleware custom | 0 KB | sin libs externas |
| Detección dispositivo | `user-agents==2.2.0` | ~150 KB | parser User-Agent → "Chrome en Windows" |
| Frontend strength meter | `@zxcvbn-ts/core` | ~50 KB | lazy-loaded |
| Geolocalización IP (opcional) | `ipinfo` API gratis | — | 50 k req/mes free tier |

**Costo**: $0/mes adicionales.

---

## 3 · Plan de implementación por fases

### Fase A — Hardening crítico backend (4 h)

#### A.1 · Política estricta de password
**Archivo nuevo**: `backend/core/password_policy.py`

```python
def validar_password(pwd: str) -> tuple[bool, list[str]]:
    """Devuelve (ok, errores). Reglas: 8+ chars, ≥1 mayús, ≥1 minús, ≥1 dígito, ≥1 símbolo."""
```

Integrar en:
- `backend/routers/auth.py:reset_password_confirm`
- `backend/routers/auth.py:seteo_password_confirm`
- `backend/routers/usuarios.py:crear_usuario`
- `backend/routers/usuarios.py:actualizar_usuario` (cuando viene `password`)

Mensajes en español: "Falta una mayúscula", "Agregá al menos un símbolo (!@#$%)".

#### A.2 · Rate limiting + lockout en login
**Archivos**: `backend/middleware/rate_limit.py` (nuevo), `backend/routers/auth.py` (modificar).

- SlowAPI: límite global `5/minute` por IP en `/auth/token`.
- **Lockout por cuenta**: tras 5 fallos consecutivos en 10 min → bloquear cuenta 15 min.
- Email automático cuando se dispara el lock (servicio existente `services/email.py`).

**Migración SQL**:
```sql
ALTER TABLE usuarios
  ADD COLUMN IF NOT EXISTS failed_login_attempts INT NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS last_failed_login TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS locked_until TIMESTAMPTZ;
```

#### A.3 · Fix timing attack
**Archivo**: `backend/routers/auth.py:login`.

Hoy si el usuario NO existe, no se ejecuta bcrypt → tiempo de respuesta diferente. Fix: ejecutar `bcrypt.checkpw` SIEMPRE con un hash dummy si el user no existe.

```python
DUMMY_HASH = bcrypt.hashpw(b"dummy_for_timing_attack", bcrypt.gensalt(12))

if user is None:
    bcrypt.checkpw(password.encode(), DUMMY_HASH)  # mismo costo de tiempo
    raise HTTPException(401, "Credenciales incorrectas")
```

#### A.4 · Security headers middleware
**Archivo nuevo**: `backend/middleware/security_headers.py`

```
Strict-Transport-Security: max-age=31536000; includeSubDomains
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(self), microphone=(), geolocation=()
Content-Security-Policy:
  default-src 'self';
  img-src 'self' https://*.supabase.co data:;
  connect-src 'self' https://erp-web-backend-i5zv.onrender.com https://*.supabase.co;
  script-src 'self' 'unsafe-inline';
  style-src 'self' 'unsafe-inline';
  frame-ancestors 'none';
```

Quitar header `Server: uvicorn` (information leak).

**Verificación**: tras deploy, https://securityheaders.com debe dar **calificación A**.

---

### Fase B — Auditoría enriquecida (2 h)

#### B.1 · Captura de IP + User-Agent
**Archivos**: `backend/services/audit.py` (modificar), `db/migrations/2026-05-XX_security_hardening.sql`.

```sql
ALTER TABLE auditoria_log ADD COLUMN IF NOT EXISTS user_agent VARCHAR(255);
```

Helper centralizado:
```python
async def audit_with_request(request: Request, **kwargs):
    ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or \
         (request.client.host if request.client else None)
    ua = request.headers.get("user-agent", "")[:255]
    await registrar(ip_origen=ip, user_agent=ua, **kwargs)
```

Modificar **8 routers críticos** para pasar `request` al helper:
- `auth.py` (login, reset, invitar)
- `comprobantes.py`
- `pagos.py`
- `usuarios.py`
- `empresa.py`
- `adjuntos.py`
- `admin_sistema.py`
- `contabilidad.py`

#### B.2 · Refactor SQL dinámico admin_sistema
**Archivo**: `backend/routers/admin_sistema.py`.

Reemplazar `text(f"SELECT * FROM {t}")` con dict literal:
```python
QUERIES_BACKUP = {
    "clientes": "SELECT * FROM clientes WHERE empresa_id = :eid",
    "comprobantes": "SELECT * FROM comprobantes WHERE empresa_id = :eid",
    # ...
}
```

Sin riesgo de SQL injection ni siquiera teórico.

#### B.3 · Sanitizar logs de excepciones
**Archivo**: `backend/services/audit.py:85`.

Reemplazar `print(f"...: {e}")` con un logger que enmascara campos sensibles:

```python
import re
SENSITIVE = re.compile(r'(password|token|secret|key)["\']?\s*[:=]\s*["\']?[^"\'\s,}]+', re.IGNORECASE)

def sanitizar(msg: str) -> str:
    return SENSITIVE.sub(r'\1=***', msg)

logger.error("[audit] fallo: %s", sanitizar(str(e)))
```

---

### Fase C — UX de seguridad (3 h)

#### C.1 · Idle timeout frontend
**Archivo nuevo**: `frontend/src/lib/idle-timeout.ts`

```typescript
export function useIdleTimeout(minutos: number = 30) {
  // Listener global mousemove/keydown/click
  // Tras N min sin actividad → modal "Vas a salir en 60s"
  // Si no responde → logout()
}
```

Integrar en `app/(app)/layout.tsx`.

#### C.2 · Strength meter visual
**Archivo nuevo**: `frontend/src/components/PasswordStrength.tsx`

Usa `@zxcvbn-ts/core`:
- Barra de progreso roja (0-1) → amarilla (2) → verde (3-4)
- Mensajes en español: "Demasiado fácil — agregá un número y un símbolo"
- Lazy-loaded (solo carga en páginas de cambio password)

Integrar en:
- `auth/seteo-password/page.tsx`
- `auth/reset-password/page.tsx`
- `(app)/admin/usuarios/page.tsx` (al crear/cambiar password)

#### C.3 · Página "Mi seguridad"
**Archivo nuevo**: `frontend/src/app/(app)/perfil/seguridad/page.tsx`

Muestra:
- **Últimos 10 accesos** (de `auditoria_log` filtrado por `accion='login'`):
  - Fecha + hora
  - IP (opcional resolver a ciudad con ipinfo si está dentro de los 90 días)
  - Dispositivo ("Chrome en Windows" parseado de User-Agent)
- **Cambiar contraseña** (form con strength meter)
- **Cerrar sesión en otros dispositivos** (botón) — invalida JWTs anteriores
- Notificación visible si hubo intentos fallidos recientes

#### C.4 · Email al cambiar password / lockout
**Archivo**: `backend/services/email.py` (extender con templates).

```python
def enviar_password_cambiada(to: str, nombre: str, ip: str, dispositivo: str): ...
def enviar_cuenta_bloqueada(to: str, nombre: str, ip: str, dispositivo: str): ...
```

Disparar desde `auth.py` y `usuarios.py`.

---

### Fase D — Privacidad (2 h)

#### D.1 · Endpoints "/me" para privacidad
**Archivo**: `backend/routers/usuarios.py` (extender).

```python
@router.get("/me/exportar-datos")
async def exportar_datos(...) -> StreamingResponse:
    """ZIP con todos los datos del usuario en JSON: comprobantes, pagos, adjuntos URLs."""

@router.delete("/me")
async def eliminar_cuenta(...):
    """Anonimiza: email='<deleted-USERID>', nombre='Usuario Eliminado', activo=FALSE.
    No borra registros relacionados (preserva auditoría)."""
```

#### D.2 · Cron de retención (borrar IPs > 90 días)
**SQL**:
```sql
CREATE OR REPLACE FUNCTION limpiar_ips_viejas() RETURNS void AS $$
BEGIN
  UPDATE auditoria_log
  SET ip_origen = NULL
  WHERE fecha_creacion < NOW() - INTERVAL '90 days'
    AND ip_origen IS NOT NULL;
END;
$$ LANGUAGE plpgsql;
```

**Render cron job** (`render.yaml`):
```yaml
- type: cron
  name: limpiar-ips-90d
  schedule: "0 3 * * *"   # diario 3 AM
  buildCommand: pip install -r backend/requirements.txt
  startCommand: python -c "import asyncio,asyncpg,os; asyncio.run((lambda:asyncpg.connect(os.environ['DATABASE_URL']).then(c:c.execute('SELECT limpiar_ips_viejas()')))())"
```

---

### Fase E — Rotación de secrets + verificación (1 h)

#### E.1 · Rotar credenciales que aparecieron en chat

**Procedimiento documentado en `docs/ROTACION_SECRETS.md`**:

1. **JWT_SECRET_KEY** (vigente: aparecida en chat 2026-05-03)
   - Generar nuevo: `python -c "import secrets; print(secrets.token_hex(64))"`
   - Actualizar en Render env vars
   - **Efecto**: invalida todos los JWT actuales → todos los usuarios re-loguean (deseado)

2. **Supabase password** (vigente: `erpweb202602` en chat)
   - Supabase Dashboard → Settings → Database → Reset Password
   - Actualizar `DATABASE_URL` en Render con la nueva password
   - **Efecto**: backend se reinicia y se conecta con la nueva

3. (Opcional, no urgente) **Service Role Key Supabase**
   - Si se sospecha leak, regenerar desde Settings → API
   - Actualizar `SUPABASE_KEY` en Render

#### E.2 · Verificación end-to-end

```bash
# 1. Password fuerte requerida
curl -X POST .../auth/reset-password/confirm \
  -d '{"token":"X","password_nueva":"abc12345"}'
# → 400 con mensaje "Falta una mayúscula"

# 2. Lockout
for i in {1..6}; do
  curl -X POST .../auth/token -d "username=admin&password=mal"
done
# → 6° intento devuelve 423 Locked + email al usuario

# 3. Headers de seguridad
curl -I https://erp-web-backend-i5zv.onrender.com/health
# → debe mostrar HSTS, X-Content-Type-Options, X-Frame-Options, CSP

# 4. Test online
# https://securityheaders.com/?q=erp-web-cyan-delta.vercel.app
# → calificación A esperada
```

---

## 4 · Migración SQL única

`db/migrations/2026-05-06_security_hardening.sql` — toca 2 tablas, idempotente:

```sql
ALTER TABLE usuarios
  ADD COLUMN IF NOT EXISTS failed_login_attempts INT NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS last_failed_login TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS locked_until TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS password_changed_at TIMESTAMPTZ DEFAULT NOW();

ALTER TABLE auditoria_log
  ADD COLUMN IF NOT EXISTS user_agent VARCHAR(255);

CREATE INDEX IF NOT EXISTS idx_audit_login
  ON auditoria_log (usuario_id, fecha_creacion DESC)
  WHERE accion IN ('LOGIN','LOGIN_FALLIDO','LOGIN_BLOQUEO');

CREATE OR REPLACE FUNCTION limpiar_ips_viejas() RETURNS void AS $$
BEGIN
  UPDATE auditoria_log SET ip_origen = NULL
  WHERE fecha_creacion < NOW() - INTERVAL '90 days' AND ip_origen IS NOT NULL;
END;
$$ LANGUAGE plpgsql;
```

---

## 5 · Archivos críticos por fase

### Fase A
| Archivo | Acción |
|---|---|
| `backend/core/password_policy.py` | Crear |
| `backend/middleware/rate_limit.py` | Crear |
| `backend/middleware/security_headers.py` | Crear |
| `backend/main.py` | Editar (registrar middlewares) |
| `backend/routers/auth.py` | Editar (lockout + timing fix + password policy) |
| `backend/routers/usuarios.py` | Editar (password policy en crear/actualizar) |
| `db/migrations/2026-05-06_security_hardening.sql` | Crear |
| `backend/requirements.txt` | + `slowapi==0.1.9`, `user-agents==2.2.0` |

### Fase B
| Archivo | Acción |
|---|---|
| `backend/services/audit.py` | Editar (helper con Request) |
| 8 routers críticos | Editar (pasar `request` al helper) |
| `backend/routers/admin_sistema.py` | Editar (refactor SQL dinámico) |

### Fase C
| Archivo | Acción |
|---|---|
| `frontend/src/lib/idle-timeout.ts` | Crear |
| `frontend/src/components/PasswordStrength.tsx` | Crear |
| `frontend/src/app/(app)/perfil/seguridad/page.tsx` | Crear |
| `frontend/src/app/auth/seteo-password/page.tsx` | Editar (strength meter) |
| `frontend/src/app/auth/reset-password/page.tsx` | Editar (strength meter) |
| `frontend/src/app/(app)/layout.tsx` | Editar (idle timeout) |
| `frontend/package.json` | + `@zxcvbn-ts/core` |
| `backend/services/email.py` | Editar (templates `password_changed`, `account_locked`) |

### Fase D
| Archivo | Acción |
|---|---|
| `backend/routers/usuarios.py` | + endpoints `/me/exportar-datos`, `DELETE /me` |
| `render.yaml` | + cron service `limpiar-ips-90d` |

### Fase E
| Archivo | Acción |
|---|---|
| `docs/ROTACION_SECRETS.md` | Crear (procedimiento) |
| Render env vars | Rotar `JWT_SECRET_KEY`, actualizar `DATABASE_URL` |

---

## 6 · Riesgos y mitigaciones

| Riesgo | Probabilidad | Mitigación |
|---|---|---|
| Lockout abusable (atacante bloquea cuentas legítimas con emails conocidos) | Media | Lockout es por (IP + email); si crece el problema, sumar CAPTCHA tras 3 fallos |
| HSTS preload bloquea acceso si dominio cambia | Baja | NO subir a hstspreload.org hasta tener dominio definitivo |
| Cron de retención falla → IPs no se borran | Baja | Render cron tiene logs; alertar por email si falla |
| Idle timeout molesta a usuarios poco técnicos | Media | 30 min es generoso; modal con botón "Seguir trabajando" |
| `zxcvbn-ts` agrega 50 KB al bundle | Baja | Aceptable; lazy-load solo en páginas de cambio pwd |
| Rotar `JWT_SECRET` desloguea a todos | Cierto, deseado | Avisar al usuario con anticipación (ideal en horario de poco uso) |
| **JWT en localStorage vulnerable a XSS** si llegase a haber un bug | Baja-Media | CSP estricto + idle timeout + revisar `dangerouslySetInnerHTML` |

---

## 7 · Compromiso pragmático: localStorage vs httpOnly cookies

**Tema**: el JWT está en `localStorage`. Si un atacante inyecta JavaScript (XSS), puede leerlo.

**Por qué dejarlo así por ahora**:
- El frontend NO usa `dangerouslySetInnerHTML` ni `eval` (bajo riesgo XSS).
- CSP estricto bloquea scripts externos.
- Idle timeout 30 min limita ventana de exposición.
- Migrar a cookies httpOnly requiere reescribir auth + agregar CSRF tokens (~6 h adicionales).

**Cuándo migrar a httpOnly cookies**:
- Si se detecta un bug XSS real
- Si el sistema crece a >50 usuarios
- Si maneja montos > ₲ 100.000.000

---

## 8 · Métricas de éxito post-implementación

| Métrica | Meta |
|---|---|
| securityheaders.com calificación | **A** |
| Tiempo respuesta login (p95) | < 600 ms |
| Diferencia de tiempo user-existente vs inexistente | < 50 ms |
| Tasa de cuentas con password fuerte | 100 % (forzado por validación) |
| Tasa de logs con `ip_origen` poblada | > 95 % |
| Tasa de IPs > 90 días con valor NULL | 100 % (cron job) |

---

## 9 · Próximas iteraciones (post v1)

Si el sistema crece o aparecen requerimientos nuevos, considerar:

1. **2FA opcional** (TOTP con app authenticator) — opt-in por usuario
2. **WebAuthn** (passkey, login biométrico) — UX moderno, máxima seguridad
3. **HttpOnly cookies + CSRF** (cuando el sistema escale)
4. **Sentry / Logtail** para captura de errores en producción con alertas
5. **WAF (Web Application Firewall)** — Cloudflare gratis o Vercel WAF
6. **Pen testing externo** — antes de cualquier release público
7. **Compliance**: si se manejan datos médicos o financieros sensibles (LFPDPPP / GDPR-like)

---

## 10 · Cumplimiento normativo (Paraguay)

- **DNIT**: facturas con timbrado vigente (módulo Fase 6 del roadmap general).
- **Ley 1682/2001 de Protección de Datos**: proveer endpoints de export/delete (Fase D ✓).
- **Resolución BCP** (si maneja info bancaria): backup encriptado + auditoría → cubierto.

---

## 11 · Histórico de cambios

| Fecha | Versión | Cambio | Autor |
|---|---|---|---|
| 2026-05-04 | v0.1 | Plan inicial diseñado en plan mode | Claude Sonnet 4.6 |
| 2026-05-05 | v1.0 | Plan formalizado en `docs/roadmap/` para registro permanente | Claude Opus 4.7 |

---

## 12 · Referencias

- **Plan de implementación detallado**: `~/.claude/plans/jiggly-swinging-candle.md` (versión local)
- **Horizonte general de desarrollo**: `docs/roadmap/HORIZONTE_DESARROLLO.md`
- **Auditoría sistema contable**: `docs/AUDITORIA_SISTEMA_CONTABLE.md`
- **OWASP Top 10**: https://owasp.org/Top10/
- **Mozilla Web Security**: https://infosec.mozilla.org/guidelines/web_security
