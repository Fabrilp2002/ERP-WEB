# Fase K - Chatbot ERP v2 "Atajo Inteligente"

> **Estado: APROBADO por PM (gfcar) - 2026-05-12.**
> **Correccion Codex - 2026-05-13:** plan alineado con el codigo real.
> **K.1 backend base - 2026-05-13:** implementado por Codex; frontend de confirmacion pendiente.
> Autor del plan original: Claude (Opus 4.7). Correccion tecnica: Codex.

## Contexto

El chatbot actual (`backend/services/chatbot.py` + `backend/routers/chatbot.py` + `/asistente`) ya usa Gemini 2.5 Flash con function calling y tiene herramientas de lectura. Ademas, **ya existen `registrar_cobro` y `registrar_pago` por chat**, pero hoy ejecutan directo cuando la factura y el monto son inequivocos.

Fase K convierte el asistente en un **operador conversacional completo del ERP**, con escritura segura por confirmacion, alcance estrictamente ERP y rediseño visual con widget flotante global + pagina dedicada.

## Decisiones cerradas

- La escritura siempre usa patron **Two-Phase Action**: preview primero, confirmacion despues.
- Los `action_token` se guardan en **base de datos**, no en memoria ni Redis.
- Toda escritura se audita en `auditoria_log` con `origen='chatbot'`.
- `viewer` queda solo lectura.
- `operador` puede crear comprobantes y registrar cobros/pagos.
- `admin` puede ademas anular comprobantes, eliminar pagos y editar comprobantes validados.
- `DELETE /pagos/{id}` debe endurecerse a `admin` antes de exponer `eliminar_pago` al chatbot.
- `PATCH /comprobantes/{id}` fue creado en K.1 con edicion limitada a campos seguros.
- K.1 refactoriza `registrar_cobro` y `registrar_pago` existentes para que dejen de ejecutar directo y pasen por preview + confirmacion.

## Estado de implementacion

| Sub-fase | Estado | Evidencia |
|---|---|---|
| K.1 - Migracion `chatbot_action_tokens` | Implementado | `db/migrations/2026-05-13_chatbot_action_tokens.sql` |
| K.1 - Servicio de tokens DB | Implementado | `backend/core/action_tokens.py` |
| K.1 - Endpoint `POST /chat/confirmar-accion` | Implementado | `backend/routers/chatbot.py` |
| K.1 - Cobros/pagos preview + confirmacion | Implementado | `backend/services/chatbot.py` |
| K.1 - `PATCH /comprobantes/{id}` seguro | Implementado | `backend/routers/comprobantes.py` |
| K.1 - `DELETE /pagos/{id}` solo admin | Implementado | `backend/routers/pagos.py` |
| K.2 - Widget Aurora + store | Pendiente | Frontend no implementado |
| K.3 - Pagina `/asistente` rediseñada | Pendiente | Frontend no implementado |
| K.4 - Pulido | Pendiente | Streaming/accesibilidad/E2E pendientes |

## Backend - contrato de escritura

### Tools objetivo

| Tool | Endpoint / implementacion | Estado actual | Decision K.1 |
|------|---------------------------|---------------|--------------|
| `crear_comprobante` | `POST /comprobantes` | Existe | Envolver con preview + confirmacion |
| `anular_comprobante` | `PATCH /comprobantes/{id}/anular` | Existe | Solo admin desde chatbot; preview rojo |
| `editar_comprobante` | `PATCH /comprobantes/{id}` | Existe desde K.1 | Solo campos seguros; sin montos ni detalle |
| `registrar_pago` | `POST /pagos` / helper actual | Existe y ejecuta directo | Refactor a Two-Phase |
| `registrar_cobro` | `POST /pagos` / helper actual | Existe y ejecuta directo | Refactor a Two-Phase |
| `eliminar_pago` | `DELETE /pagos/{id}` | Existe con `require_escritura` | Endurecer a admin |
| `crear_cliente` | `POST /clientes` | Existe | Envolver con preview + confirmacion |
| `crear_proveedor` | `POST /proveedores` | Existe | Envolver con preview + confirmacion |

### Two-Phase Action

Cada tool de escritura acepta `confirmar: bool`.

- `confirmar=false`: valida rol, tenant, payload y ambiguedades; devuelve `ActionPreview`.
- `ActionPreview`: resumen humano, impacto, payload exacto, tipo de riesgo y `action_token`.
- `confirmar=true` + `action_token`: valida token, revalida permisos/tenant y ejecuta.
- Los tokens son de un solo uso, expiran en 60 segundos y no deben contener secretos.

### Tabla nueva para action_token

Migracion creada: `db/migrations/2026-05-13_chatbot_action_tokens.sql`.

Tabla propuesta: `chatbot_action_tokens`

| Campo | Tipo | Uso |
|---|---|---|
| `id` | UUID PK | Identificador interno |
| `empresa_id` | UUID NOT NULL | Tenant obligatorio |
| `usuario_id` | UUID NOT NULL | Usuario que genero el preview |
| `token_hash` | TEXT UNIQUE NOT NULL | Hash del token enviado al frontend |
| `accion` | VARCHAR(50) NOT NULL | Tool a ejecutar |
| `payload` | JSONB NOT NULL | Payload validado del preview |
| `expires_at` | TIMESTAMPTZ NOT NULL | TTL 60s |
| `used_at` | TIMESTAMPTZ NULL | Marca de uso unico |
| `fecha_creacion` | TIMESTAMPTZ NOT NULL DEFAULT NOW() | Auditoria tecnica |

Indices minimos:

- `token_hash` unique.
- `(empresa_id, usuario_id, expires_at)`.
- Limpieza futura de tokens expirados con job o DELETE oportunista.

### Endpoint de confirmacion

`POST /chat/confirmar-accion`

Entrada:

```json
{
  "action_token": "...",
  "historial": []
}
```

Salida:

```json
{
  "ok": true,
  "accion": "registrar_cobro",
  "resultado": {},
  "mensaje": "Accion ejecutada"
}
```

El endpoint debe:

1. Buscar `token_hash`.
2. Rechazar si expiro, no existe, ya fue usado, no coincide `empresa_id` o no coincide `usuario_id`.
3. Revalidar rol actual.
4. Ejecutar la accion server-side, nunca confiar en payload nuevo del cliente.
5. Marcar `used_at`.
6. Registrar en `auditoria_log` con `origen='chatbot'`.

## Reglas de permisos y edicion

### Edicion de comprobantes

K.1 creo `PATCH /comprobantes/{id}` con reglas cerradas:

- `operador`: solo puede editar comprobantes no validados o no anulados, y solo campos seguros.
- `admin`: puede editar comprobantes validados, salvo si estan anulados.
- Campos seguros iniciales: `numero_comprobante`, `fecha_emision`, `fecha_vencimiento`, `notas`, `condicion`, `medio_pago_contado`.
- No editar montos ni detalle en K.1 para evitar inconsistencias contables; si se necesita, sera Fase K.5.
- Toda edicion registra `auditoria_log`.

### Eliminar pagos

- Cambiar `DELETE /pagos/{id}` a `require_admin`.
- El chatbot solo expone `eliminar_pago` para `admin`.
- Mantener reversion de saldo y registro en `auditoria_log` existentes.

## Frontend - widget y pagina

Componentes nuevos:

- `frontend/src/components/chat/ChatWidget.tsx`: FAB flotante global, atajo `Ctrl+J`.
- `frontend/src/components/chat/ChatPanel.tsx`: panel deslizable, 420px desktop, fullscreen mobile.
- `frontend/src/components/chat/ActionPreviewCard.tsx`: tarjeta de confirmacion.
- `frontend/src/components/chat/QuickActions.tsx`: chips contextuales por ruta.
- `frontend/src/components/chat/MessageBubble.tsx`: burbujas reutilizables.
- `frontend/src/store/chatStore.ts`: Zustand, historial persistido en localStorage.

Pagina `/asistente`:

- Reusar `ChatPanel` en modo full-page.
- Sidebar de historial: ultimas 20 conversaciones agrupadas por dia.
- Busqueda simple de conversaciones.

Diseño "Aurora":

- FAB 56px con gradiente animado.
- Panel claro, profesional y legible; glassmorphism solo si no afecta contraste.
- Tarjetas preview con color por riesgo: info, dinero, destructiva.
- Sin comandos de voz.
- Accesibilidad AA y soporte teclado completo.

Dependencias nuevas:

- `framer-motion`
- `zustand`
- `react-markdown`
- `remark-gfm`

## Sub-fases

1. **K.1 - Backend escritura segura**: migracion `chatbot_action_tokens`, endpoint `POST /chat/confirmar-accion`, `PATCH /comprobantes/{id}`, hardening `DELETE /pagos/{id}` a admin, refactor de cobros/pagos existentes a preview + confirmacion.
2. **K.2 - Widget Aurora + store**: componentes globales, Zustand, persistencia local, atajo `Ctrl+J`.
3. **K.3 - Pagina `/asistente` rediseñada + historial**: full-page chat, sidebar, busqueda.
4. **K.4 - Pulido**: streaming si Gemini lo permite, accesibilidad, mobile, dark mode y pruebas E2E.

Cada sub-fase termina con entrada en `BITACORA_COLABORATIVA.md`, SDD actualizado si cambia contrato, pruebas registradas y commit con coautor correspondiente.

## Verificacion end-to-end

Funcionales:

1. Lectura: "Cuanto facture este mes?" mantiene regresion.
2. Crear: "Carga una factura de Distribuidora SA por 1.500.000 Gs IVA 10%" -> preview -> confirmar.
3. Pago: "Registra un pago de 500.000 Gs a la factura 001-001-1234" -> preview con saldo -> confirmar.
4. Anular: "Anula el comprobante 001-001-1234" -> preview rojo -> confirmar -> `auditoria_log` registra.
5. Eliminar pago: operador recibe rechazo; admin puede preview -> confirmar.
6. Off-topic: "Como esta el clima?" -> rechazo amable.
7. Permisos: `viewer` intenta crear factura -> rechazo.
8. Ambiguedad: "Pagale a Juan" con 3 matches -> pide desambiguar.
9. Token expirado: confirmar despues de 60s -> rechazo y opcion de regenerar preview.
10. Token reutilizado: segunda confirmacion del mismo token -> rechazo.

Seguridad:

- `action_token` no reutilizable.
- `empresa_id` y `usuario_id` verificados contra sesion actual.
- Payload ejecutado sale de DB, no del cliente.
- Prompt injection no puede saltar permisos server-side.

## Riesgos

| Riesgo | Mitigacion |
|--------|------------|
| Prompt injection dispara acciones | Two-Phase + validacion de rol y tenant server-side |
| LLM inventa UUIDs | Resolver todo contra DB antes del preview; no aceptar UUID inventado sin verificar |
| Token robado/reusado | Hash en DB, TTL 60s, `used_at`, empresa/usuario obligatorios |
| Reinicio backend pierde previews | Tokens en DB, no memoria |
| Endpoint de edicion rompe saldos | K.1 no edita montos/detalle |
| Operador elimina pagos | `DELETE /pagos/{id}` pasa a admin antes de exponer tool |

## Fuera de alcance de esta fase

- Voz o comandos hablados.
- Edicion de montos/detalles de comprobantes.
- Emision propia de facturas DNIT.
- Redis.
- Automatizaciones sin confirmacion humana.
