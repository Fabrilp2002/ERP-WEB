# CLAUDE.md — ERP Universal v4.0
> Instrucciones de sesión para Claude Code. Este archivo se carga automáticamente al inicio de cada conversación.

---

## Equipo de Desarrollo

| Rol | Identificador | Responsabilidad |
|-----|--------------|-----------------| 
| **Project Manager** | `gfcar` | Dirección del producto, validación de negocio, aprobaciones finales |
| **Arquitecto** | `Gemini` | Estructura, decisiones de alto nivel, ecosistema, algoritmos |
| **Desarrollador** | `Claude` | Código limpio, UI/UX, backend, implementación |

---

## PROTOCOLO OBLIGATORIO DE ATRIBUCIÓN

**TODA modificación de código o documentación DEBE registrarse con autoría explícita.**

### 1. Bitácora — registro OBLIGATORIO al final de cada turno

Cada vez que Claude termina trabajo en una sesión, debe agregar una fila en `BITACORA_COLABORATIVA.md` con el formato:

```
| YYYY-MM-DD | Claude | <Resumen técnico breve> | <archivos modificados> | <Estado para la siguiente IA> |
```

**No cerrar el turno sin actualizar la bitácora.**

### 2. Firma en commits

Todo commit generado por Claude debe incluir:

```
Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
```

### 3. Auditoría cruzada antes de avanzar

Antes de escribir código nuevo, Claude **debe leer la última entrada de la bitácora**. Si hay trabajo de Gemini pendiente de revisión, auditarlo primero y dejar el resultado ("Aprobado" / "Necesita Ajustes") antes de continuar.

### 4. No avanzar sin aprobación del PM

Si una fase está marcada como "Pendiente revisión Gemini" o "Pendiente aprobación PM", **no empezar la siguiente fase** hasta recibir confirmación explícita del usuario (gfcar).

---

## Contexto del Proyecto

- **Ubicación activa:** `C:\Users\gfcar\Desktop\IA\Empresa 1`
- **Repositorio GitHub:** `gfcarlos04-del/Proyecto_empresa1`
- **Stack:** FastAPI + SQLAlchemy (async) | Next.js 14 + Electron | PostgreSQL/Supabase | Gemini API (motor único IA — OCR + Chatbot)

### Estado de Fases

| Fase | Descripción | Estado |
|------|------------|--------|
| 1 | Cimientos SQL + Backend FastAPI | ✅ Completada |
| 2 | Frontend Next.js 14 + Electron | ✅ Completada |
| 3 | OCR (Gemini Vision) + Exportación Excel | ✅ Completada |
| 3.5 | Reorganización estructural del proyecto | ✅ Completada |
| 4 | Chatbot IA (Gemini function calling) | ✅ Completada |
| A-C | OCR multi-imagen, HITL confianza, preprocesado, importación Excel, cuentas corrientes, anulación | ✅ Completadas |
| D | Dashboard Recharts + Cuentas detalladas + Admin usuarios + Export fix + Contado/crédito | ✅ Completada |
| E | Admin superpoderes + Auditoría universal + Adiós Ollama + Acceso directo con ícono | ✅ Completada |
| F | Empresa con logo + Contado/crédito diferenciados + Datos personales usuarios | ✅ Completada |
| G | Bug recibos + Crédito con plazo + Adjuntos imágenes + Ubicación física | ✅ Completada |
| 4b | Build Electron (.exe installer NSIS) — PyInstaller + Next standalone + electron-builder | ✅ Completada |
| H | **Contabilidad Real**: Plan de Cuentas CRUD + Libro Diario (asientos partida doble) + Libro Mayor + Estados Financieros | ✅ Completada |
| I | **Gestión Bancaria y Fiscal**: CRUD cuentas banco + Reportes IVA RG90 + Aging de saldos + Notas de Crédito vinculadas | ✅ Completada |
| J | **Mejoras Avanzadas**: Retenciones + Presupuestos comparativo + Cierre Contable + Sidebar desplegable | ✅ Completada |
| 5 | Dashboard remoto web (solo lectura, rol viewer) | Pendiente |
| 6 | Timbrado DNIT + Emisión propia de facturas | Pendiente |

---

## Reglas Técnicas Permanentes

1. **Montos siempre en `DECIMAL(15,2)` en DB y `string` en frontend** — nunca `float`.
2. **UUIDs** en todas las PKs — nunca enteros auto-increment.
3. **`empresa_id`** en todas las tablas relevantes — arquitectura multi-tenant desde el origen.
4. **IVA paraguayo**: solo 0%, 5% y 10% — enum estricto, nunca valor libre.
5. **El sistema NO emite facturas propias** (aún) — solo registra documentos externos recibidos. El campo `timbrado_id` es nullable para expansión futura.
6. **Gemini API como motor único de IA** — OCR (Vision) y Chatbot (function calling). Ollama fue eliminado del stack en Fase E.
7. **Sin comandos de voz** — solo interfaz visual + chat/texto.
8. **Roles**: `admin`/`operador` tienen escritura; `viewer` es solo lectura (RLS en Supabase).

---

## Archivos Clave de Referencia

- `BITACORA_COLABORATIVA.md` — historial completo de cambios (leer antes de empezar)
- `docs/AUDITORIA_SISTEMA_CONTABLE.md` — **AUDITORÍA CONTABLE** con hallazgos y propuestas (leer antes de Fase H)
- `docs/especificaciones/REFERENCIAS_CONTABLES_PARAGUAY.md` — **REFERENCIAS Y FORMATOS** (SET/RG90 y legado Milano)
- `docs/arquitectura/Proyecto_Final_Arquitectura_Universal.md` — arquitectura v4.1
- `docs/roadmap/Plan_Implementacion_y_Diagrama.md` — fases y timeline
- `docs/api/API_REFERENCE.md` — endpoints documentados
- `db/esquema_bd.sql` — esquema PostgreSQL completo
- `db/migrations/` — 9 migraciones SQL incrementales (incluye Fase H, I y J)
