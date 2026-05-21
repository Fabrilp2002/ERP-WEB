# Plan de Migración v5.0 — Registro de Tarea Pendiente

> **Estado:** Aprobado por Ultraplan, aprobado por PM (gfcar). Ejecución pendiente.
> **Fecha de registro:** 2026-04-30
> **Equipo:** PM gfcar · Arquitecto Gemini · Desarrollador Claude Sonnet 4.6

---

## Resumen Ejecutivo

Migrar el ERP Universal v4.0 (aplicación de escritorio Electron + PostgreSQL local) a una versión 5.0 cloud (Supabase + Vercel + Railway/Render) sin afectar la versión actual en producción.

El trabajo se ejecuta en una carpeta **paralela** (`C:\Users\gfcar\Desktop\IA\ERP_v5_Cloud\`) — la carpeta `Empresa 1` queda intacta hasta que v5 esté validado.

## Documentos vinculados

| Documento | Propósito |
|---|---|
| `PLAN_MIGRACION_V5.md` (raíz del proyecto) | Plan técnico completo (secciones A–J + tablas) |
| `Plan_Migracion_v5.pdf` (Escritorio del PM) | Versión PDF amigable del plan |
| `BITACORA_COLABORATIVA.md` | Entrada del 2026-04-30 con el resumen de la planificación |
| Este archivo | Registro permanente como tarea pendiente del roadmap |

## Disparadores para arrancar la ejecución

La ejecución de este plan se debe iniciar cuando **alguna** de estas condiciones se cumpla:

- [ ] PM solicita explícitamente arrancar la migración
- [ ] Aparece la necesidad de acceso desde múltiples PCs / sucursales
- [ ] Aparece la necesidad de uso desde móvil
- [ ] El instalador desktop deja de cubrir un caso de uso crítico

## Pre-condiciones

Antes de empezar la ejecución, verificar:

- [ ] Cuenta Supabase creada (free tier OK para arrancar)
- [ ] Cuenta Vercel Hobby creada
- [ ] Cuenta Railway o Render creada
- [ ] Decidir si se usa free tier (cold start) o $5–7/mes always-on
- [ ] `JWT_SECRET_KEY` nueva generada (no reutilizar la del local)
- [ ] Backup de la BD local actual (`pg_dump`) realizado y guardado

## Próximo paso al arrancar

Seguir el **Orden de Implementación** de `PLAN_MIGRACION_V5.md` (12 pasos). Empezar por el **Paso 1**:

1. Copiar la carpeta `C:\Users\gfcar\Desktop\IA\Empresa 1` → `C:\Users\gfcar\Desktop\IA\ERP_v5_Cloud`
2. Editar `backend/.env` y `frontend/.env.local` con valores Supabase
3. Continuar con los pasos 2–12 según el plan

## Estimación

- **Tiempo dev:** 25–35 horas
- **Costo mensual estimado:** $0 (free tier) o $5–7 (always-on)

## Notas importantes

1. **No tocar `Empresa 1`** durante la ejecución. La regla del PM es absoluta: ambos proyectos coexisten hasta que v5 esté validado.
2. **No usar Git/GitHub** para el setup inicial (regla del PM). La copia de carpeta es directa.
3. **Auth permanece JWT custom** — no migrar a Supabase Auth.
4. **Dexie/IndexedDB no se toca** — funciona idéntico en navegador.
5. **OCR no requiere Storage** — las imágenes van en base64 directo a Gemini.

## Histórico de aprobación

| Fecha | Autor | Acción |
|---|---|---|
| 2026-04-30 | Claude | Revisión inicial del plan original PLAN_MIGRACION_V5.md, detectados 3 errores factuales |
| 2026-04-30 | Claude | Plan mejorado con 10 secciones (A–J) y enviado a Ultraplan |
| 2026-04-30 | Ultraplan | Plan refinado con detalle técnico de pgBouncer + correcciones |
| 2026-04-30 | gfcar (PM) | Plan aprobado en sesión remota |
| 2026-04-30 | Claude | Implementación de las 10 secciones en PLAN_MIGRACION_V5.md + PDF generado |
| — | gfcar (PM) | **Ejecución: pendiente** |
