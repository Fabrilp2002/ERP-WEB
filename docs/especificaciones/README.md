# Especificaciones Técnicas — ERP Universal v4.0

## Convenciones y Estándares

### Base de Datos
- **PKs:** UUID v4 (no secuencial)
- **Montos:** `DECIMAL(15,2)` (guaraníes, nunca float)
- **Fechas:** `TIMESTAMP WITH TIME ZONE`
- **Enums:** CHECK constraints (no tablas lookup para enums pequeños)
- **Soft delete:** columna `activo BOOLEAN DEFAULT TRUE`

### API REST
- **Base URL:** `http://localhost:8000` (app), `https://api.erp.com` (producción)
- **Autenticación:** Bearer JWT en header `Authorization`
- **Response:** `{ "data": {...} }` o error HTTP
- **Paginación:** `page`, `page_size` query params
- **Filtros:** Query params nombrados (ej: `?estado=confirmado&cliente_id=uuid`)

### Frontend
- **Montos:** string en tipos (mantener precisión decimal)
- **Formatos:** Usar `decimal.js` SIEMPRE para aritmética
- **Guaraní:** `₲ 1.234.567` (sin decimales)
- **Fechas:** ISO 8601 strings (`2026-04-13`)

### IVA Paraguayo
- **Valores válidos:** 0%, 5%, 10% SOLAMENTE
- **Validación:** SQL CHECK + Pydantic @field_validator
- **Cálculo:** subtotal × porcentaje_iva ÷ 100

---

## Endpoints Clave (Swagger: /docs)

### Auth
- `POST /auth/token` — Login
- JWT claims: `sub`, `empresa_id`, `rol`, `exp`

### Comprobantes
- `GET /comprobantes` — Listar (con filtros)
- `POST /comprobantes` — Crear (validación cliente XOR proveedor)
- `PATCH /comprobantes/{id}/validar` — Aprobar/rechazar OCR

### OCR
- `GET /ocr/status` — Estado Ollama/Gemini
- `POST /ocr/extraer` — Extraer datos sin crear
- `POST /ocr/procesar` — Extraer + crear en pendiente_revision

### Exportación
- `GET /export/comprobantes` — Excel descargar
- `GET /export/cuentas-corrientes` — Excel descargar
- `GET /export/inventario` — Excel descargar

---

## Modelos de Datos

### Comprobante
```python
{
  "id": "uuid",
  "empresa_id": "uuid",
  "numero_comprobante": "001-001-0001234",  # Único por empresa
  "fecha_emision": "2026-04-13",
  "cliente_id": "uuid | null",  # XOR proveedor_id
  "proveedor_id": "uuid | null",
  "monto_subtotal": "Decimal",
  "monto_iva": "Decimal",
  "monto_total": "Decimal",
  "saldo_pendiente": "Decimal",
  "metodo_carga": "manual | ocr_imagen | ocr_pdf",
  "estado_validacion": "pendiente_revision | confirmado | rechazado",
  "detalle": [
    {
      "id": "uuid",
      "descripcion": "str",
      "cantidad": "Decimal",
      "precio_unitario": "Decimal",
      "porcentaje_iva": "0 | 5 | 10",
      "subtotal": "Decimal",
      "iva_monto": "Decimal"
    }
  ]
}
```

### Usuario
```python
{
  "id": "uuid",
  "empresa_id": "uuid",
  "nombre": "str",
  "email": "email",
  "password_hash": "bcrypt",  # 12 rounds
  "id_rol": "uuid",
  "activo": true,
  "fecha_creacion": "timestamp"
}
```

---

## Flujos Críticos

### Crear Comprobante Manual
```
1. usuario → POST /comprobantes {numero, fecha, cliente_id, items}
2. validar: cliente_id XOR proveedor_id, IVA ∈ [0,5,10]
3. calc subtotal/iva (DECIMAL)
4. INSERT comprobante + detalle_comprobantes
5. estado = 'confirmado' (manual es confiable)
6. response 201
```

### Cargar Factura por OCR
```
1. usuario → POST /ocr/procesar {archivo, cliente_id/proveedor_id}
2. OCR → Ollama (local) o Gemini (fallback)
3. parse JSON → estructura ComprobanteCreate
4. INSERT con estado = 'pendiente_revision'
5. respuesta: comprobante + datos_extraidos
6. usuario revisa en tabla → PATCH /validar {confirmado|rechazado}
```

### Sincronizar Offline
```
1. operador pierde conexión
2. POST /comprobantes → ERR_NETWORK
3. interceptor: Dexie.encolar(request)
4. response 202 optimista
5. UI: badge "1 pendiente de sync"
6. reconexión → window 'online'
7. auto-sincronizar() → POST cola items
8. response 200 → limpiar Dexie
```

---

## Seguridad

### Validación entrada
- SQL injection: SQLAlchemy ORM + parameterized queries
- XSS: React/Next.js sanitiza por defecto
- CSRF: CORS configurado (solo localhost dev)
- Rate limiting: (futuro) Redis + slowapi

### Encriptación
- Passwords: bcrypt 12 rounds (hash one-way)
- JWT: HMAC-SHA256
- TLS: HTTPS en producción (HTTPS only cookies)

### Control de acceso
- Autenticación: JWT obligatorio en protected routes
- Autorización: RLS en Supabase + `require_escritura()` en API
- Auditoría: auditoria_log + BITACORA.md

---

## Performance

### Índices (PostgreSQL)
- PK: idx_id (uuid)
- FK: idx_empresa_id, idx_cliente_id, idx_proveedor_id
- Búsqueda: idx_numero_comprobante_por_empresa
- Ordenamiento: idx_fecha_emision DESC

### Caching
- Frontend: TanStack Query (30s staleTime)
- Backend: (futuro) Redis para vistas complejas

### Timeouts
- API request: 30s
- OCR: 120s (Ollama puede ser lento)
- Export: 60s

---

## Versionado API

**Actual:** v1 (implícito en paths `/api/...`)

Cuando breaking changes → `/api/v2/...`

---

## Testing

### Unit Tests
- Models: validación Pydantic
- Security: JWT decode, bcrypt verify
- Offline: Dexie mock

### Integration Tests
- Create comprobante end-to-end
- OCR extract + create
- Export genera bytes válidos

### Manual Tests
- Nuevo usuario login
- Crear comprobante offline → sync online
- OCR con Ollama caído (fallback Gemini)
