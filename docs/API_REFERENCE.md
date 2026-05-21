# API Reference — ERP Universal

**Base URL:** `http://localhost:8000` (desarrollo)

**Autenticación:** Bearer JWT en header `Authorization: Bearer <token>`

**Documentación interactiva:** http://localhost:8000/docs (Swagger UI)

---

## Auth

### POST /auth/token
Obtener JWT para login

```http
POST /auth/token HTTP/1.1
Content-Type: application/x-www-form-urlencoded

username=user@example.com&password=securepass123
```

**Response 200:**
```json
{
  "access_token": "eyJ0eXAi...",
  "token_type": "bearer",
  "rol": "operador",
  "empresa_id": "uuid",
  "usuario_nombre": "Juan Pérez"
}
```

---

## Comprobantes

### GET /comprobantes
Listar comprobantes con filtros

```http
GET /comprobantes?page=1&page_size=50&estado=confirmado
Authorization: Bearer <token>
```

**Query params:**
- `page` (int, default: 1)
- `page_size` (int, default: 50, max: 200)
- `estado` (string: pendiente_revision|confirmado|rechazado)

**Response 200:** Array de comprobantes

---

### POST /comprobantes
Crear nuevo comprobante

```json
{
  "tipo_id": "uuid",
  "numero_comprobante": "001-001-0001234",
  "fecha_emision": "2026-04-13",
  "cliente_id": "uuid",
  "proveedor_id": null,
  "monto_subtotal": "1000000.00",
  "monto_iva": "100000.00",
  "monto_total": "1100000.00",
  "metodo_carga": "manual",
  "detalle": [
    {
      "descripcion": "Producto X",
      "cantidad": "10.0000",
      "precio_unitario": "100000.00",
      "porcentaje_iva": "10"
    }
  ]
}
```

**Response 201:** Comprobante creado

**Errores:**
- `422` si cliente_id y proveedor_id (ambos)
- `422` si ninguno de cliente_id/proveedor_id
- `403` si rol es viewer

---

### PATCH /comprobantes/{id}/validar
Aprobar o rechazar comprobante OCR

```http
PATCH /comprobantes/uuid-aqui/validar?estado=confirmado
Authorization: Bearer <token>
```

**Query params:**
- `estado` (string): `confirmado` o `rechazado` (requerido)

**Response 200:**
```json
{ "mensaje": "Comprobante marcado como 'confirmado'" }
```

---

### PATCH /comprobantes/{id}
Editar campos seguros de un comprobante sin modificar montos ni detalle.

```json
{
  "numero_comprobante": "001-001-0001234",
  "fecha_emision": "2026-05-13",
  "fecha_vencimiento": "2026-06-13",
  "notas": "Observacion interna",
  "condicion": "credito",
  "medio_pago_contado": null
}
```

**Reglas:**
- `viewer` no puede editar.
- `operador` no puede editar comprobantes confirmados.
- `admin` puede editar comprobantes confirmados.
- Comprobantes anulados no se editan.
- No permite editar montos ni items.

---

## Chatbot

### POST /chat/mensaje
Enviar mensaje al asistente IA.

### POST /chat/confirmar-accion
Confirmar una accion previamente generada por el chatbot con preview.

```json
{
  "action_token": "token-generado-en-preview",
  "historial": []
}
```

**Response 200:**
```json
{
  "ok": true,
  "accion": "registrar_cobro",
  "resultado": {},
  "mensaje": "Accion ejecutada"
}
```

**Errores:**
- `404` token inexistente o de otro usuario/empresa
- `409` token ya usado
- `410` token expirado

---

## Clientes

### GET /clientes
Listar clientes

```http
GET /clientes?buscar=nombre
```

**Query params:**
- `buscar` (string, opcional): filtro por nombre o RUC

**Response 200:** Array de clientes

---

### POST /clientes
Crear cliente

```json
{
  "nombre": "Empresa ABC S.A.",
  "ruc": "80012345-6",
  "telefono": "0981234567",
  "email": "contacto@abc.com",
  "direccion": "Av. Principal 123",
  "notas": "Cliente VIP"
}
```

---

### GET /clientes/{id}/saldo
Obtener estado de cuenta

```json
{
  "cliente_id": "uuid",
  "cliente": "Empresa ABC",
  "total_facturado": "5000000.00",
  "total_cobrado": "3000000.00",
  "saldo_pendiente": "2000000.00"
}
```

---

## OCR

### GET /ocr/status
Estado del motor OCR

**Response 200:**
```json
{
  "ollama_disponible": true,
  "modelo_ocr": "gemma4:4b",
  "gemini_configurado": true,
  "gemini_fallback_activo": false
}
```

---

### POST /ocr/extraer
Extraer datos sin crear comprobante

```
POST /ocr/extraer?forzar_gemini=false
Content-Type: multipart/form-data
Authorization: Bearer <token>

[archivo binario]
```

**Query params:**
- `forzar_gemini` (bool, default: false)

**Response 200:**
```json
{
  "numero_comprobante": "001-001-0001234",
  "fecha_emision": "2026-04-13",
  "ruc_emisor": "80012345-6",
  "items": [
    {
      "descripcion": "Producto X",
      "cantidad": 10,
      "precio_unitario": 100000,
      "porcentaje_iva": 10
    }
  ],
  "monto_subtotal": 1000000,
  "monto_iva_10": 100000,
  "monto_total": 1100000,
  "confianza": 0.92,
  "motor_usado": "ollama_local"
}
```

---

### POST /ocr/procesar
Extraer datos + crear comprobante

```
POST /ocr/procesar?tipo_id=uuid&cliente_id=uuid&forzar_gemini=false
Content-Type: multipart/form-data
Authorization: Bearer <token>

[archivo binario]
```

**Query params:**
- `tipo_id` (uuid): tipo de comprobante
- `cliente_id` (uuid): cliente O proveedor_id (mutually exclusive)
- `proveedor_id` (uuid)
- `forzar_gemini` (bool)

**Response 201:**
```json
{
  "comprobante": { ... },
  "datos_extraidos": { ... },
  "mensaje": "Comprobante creado como pendiente_revision..."
}
```

---

## Exportación

### GET /export/comprobantes
Descargar comprobantes como Excel

```http
GET /export/comprobantes?estado=confirmado
```

**Query params:**
- `estado` (string, opcional)

**Response 200:** application/vnd.openxmlformats-officedocument.spreadsheetml.sheet (*.xlsx)

---

### GET /export/cuentas-corrientes
Descargar CC (clientes + proveedores, 2 hojas)

**Response 200:** *.xlsx (2 hojas)

---

### GET /export/inventario
Descargar inventario

```http
GET /export/inventario?solo_critico=false
```

**Query params:**
- `solo_critico` (bool): solo items bajo stock

**Response 200:** *.xlsx

---

## Dashboard

### GET /dashboard/resumen
KPIs principales

**Response 200:**
```json
{
  "total_facturas_pendientes": 12,
  "monto_por_cobrar": "2500000.00",
  "monto_por_pagar": "1800000.00",
  "items_bajo_stock": 3,
  "ultima_actualizacion": "2026-04-13T10:30:00Z"
}
```

---

### GET /dashboard/cuentas-corrientes
Saldos clientes y proveedores

**Response 200:**
```json
{
  "clientes": [
    {
      "cliente_id": "uuid",
      "cliente": "Empresa ABC",
      "total_facturado": "5000000.00",
      "total_cobrado": "3000000.00",
      "saldo_pendiente": "2000000.00"
    }
  ],
  "proveedores": [
    {
      "proveedor_id": "uuid",
      "proveedor": "Distribuidor XYZ",
      "total_facturado": "1000000.00",
      "total_pagado": "800000.00",
      "saldo_pendiente": "200000.00"
    }
  ]
}
```

---

## Errores Comunes

| HTTP | Descripción | Causa |
|------|---|---|
| 401 | Unauthorized | JWT ausente o inválido |
| 403 | Forbidden | Rol viewer en endpoint de escritura |
| 404 | Not Found | Recurso no existe en esta empresa |
| 422 | Unprocessable | Validación Pydantic fallida |
| 502 | Bad Gateway | OCR falló (Ollama y Gemini no disponibles) |

---

## Rate Limiting (Futuro)

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1681382400
```

---

## Webhook Events (Futuro)

```
POST https://tu-dominio.com/webhook
Content-Type: application/json

{
  "event": "comprobante.creado",
  "timestamp": "2026-04-13T10:30:00Z",
  "data": { "comprobante": {...} }
}
```
