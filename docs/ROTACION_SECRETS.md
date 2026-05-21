# Rotación de secrets — ERP_Web

Fecha base: 2026-05-06
Responsable: PM / administrador de infraestructura

## 🔴 URGENTE — 2026-05-17

Durante el scan P0 de seguridad (commit `56b649f` y posteriores) se detectó que `BITACORA_DESKTOP_ARCHIVO.md:109` tenía commiteada una **GEMINI_API_KEY real**. El valor fue redactado del archivo en el commit que acompaña esta nota, pero **la clave sigue accesible en el historial de git** del repositorio público `gfcarlos04-del/ERP-WEB`.

**Acción obligatoria del PM (gfcar):**

1. **Rotar la clave Gemini YA**: Google AI Studio → API keys → revocar la clave que empieza con `AIzaSyD26...` → generar una nueva → actualizar `GEMINI_API_KEY` en Render env vars → redeploy.
2. (Opcional, recomendado) reescribir el historial de git con `git filter-repo --replace-text` o `bfg-repo-cleaner` y hacer `force-push` a `main`, `develop`. Esto invalida los hashes — coordinar con cualquier worktree/CI activo antes.
3. Confirmar en bitácora el reemplazo cuando esté hecho.

Mientras no se rote, cualquier persona con acceso al repo (público) puede usar la clave y consumir cuota de Gemini de la cuenta del proyecto.

## Cuándo rotar

Rotar inmediatamente si un secreto apareció en chat, capturas, logs, issues o cualquier canal no seguro.

## 1. JWT_SECRET_KEY

1. Generar nuevo secreto:

   ```bash
   python -c "import secrets; print(secrets.token_hex(64))"
   ```

2. Render Dashboard → servicio backend → Environment → reemplazar `JWT_SECRET_KEY`.
3. Redeploy del backend.
4. Efecto esperado: todos los usuarios quedan deslogueados y deben iniciar sesión de nuevo.

## 2. Password de Supabase Postgres

1. Supabase Dashboard → Project Settings → Database → Reset database password.
2. Copiar la nueva contraseña.
3. Actualizar `DATABASE_URL` en Render con la nueva password.
4. Redeploy del backend.
5. Verificar `/health` y login.

## 3. Supabase service role key

1. Supabase Dashboard → Project Settings → API.
2. Regenerar service role si se sospecha exposición.
3. Actualizar `SUPABASE_KEY` en Render.
4. Probar adjuntos/logo/storage.

## 4. Gemini / Resend

- Gemini: regenerar API key en Google AI Studio y actualizar `GEMINI_API_KEY`.
- Resend: crear nueva API key, reemplazar `RESEND_API_KEY` y revocar la anterior.

## Checklist de verificación

```bash
curl -I https://TU_BACKEND/health
curl -X POST https://TU_BACKEND/auth/token \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=ADMIN_EMAIL&password=PASSWORD'
```

Confirmar:

- Backend responde `200` en `/health`.
- Login funciona con credenciales válidas.
- Password reset envía email real si `RESEND_API_KEY` está configurado.
- Adjuntos/logos siguen funcionando si se rotó Supabase key.
