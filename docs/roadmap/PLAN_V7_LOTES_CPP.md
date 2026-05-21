# Plan v7 — Trazabilidad de lotes + Costo Promedio Ponderado

> **Estado:** v7.1 (foundation) en ejecución · v7.2 (integración con ventas) pendiente
> **Decisiones cerradas por PM (2026-05-17):**
> - Stock existente → lote único `INICIAL`, sin vencimiento.
> - Estrategia de salida → **FEFO** (First Expired First Out).
> - CPP → desde la fecha de migración hacia adelante (no se reprocesan facturas históricas).
> - Alerta de vencimientos → 30 días antes (configurable por empresa).

---

## 1. Problema que resuelve

Hoy el inventario tiene un solo `costo_unitario` por item y ninguna noción de lote. Eso impide:

1. **Trazabilidad**: si un lote de bronceador resulta defectuoso, no se puede recuperar a qué clientes se vendió ni qué stock contiene aún ese lote.
2. **Vencimientos**: cosméticos vencen. Sin lotes con fecha, no hay forma de avisar antes de que se pierda mercadería.
3. **Costos reales**: cada compra de la misma materia prima entra a precio distinto. Mantener un único `costo_unitario` falsea el margen y el COGS contable.

V7 resuelve los tres con cambios incrementales — no invasivos al flujo actual.

---

## 2. Decisiones de producto (cerradas)

### 2.1 Stock existente — opción A
Los 115 items actuales mantienen su `cantidad_actual` y su `costo_unitario`. Al aplicar la migración:
- Se crea **un** lote por item con `numero_lote = 'INICIAL'`, `fecha_vencimiento = NULL`, `cantidad = inventario.cantidad_actual`, `costo_unitario = inventario.costo_unitario`.
- Items con `cantidad_actual = 0` no reciben lote (no hace falta).

Ningún dato existente se modifica. La migración es reversible borrando los lotes con `numero_lote = 'INICIAL'`.

### 2.2 Estrategia de salida — FEFO
Al vender un item, el sistema consume primero del lote con `fecha_vencimiento` más cercana (NULLs van al final). Empate de vencimiento → se ordena por `fecha_ingreso` ASC (FIFO secundario).

### 2.3 CPP — incremental
El campo `inventario.costo_unitario` se reinterpreta como "costo promedio ponderado actual". Se recalcula sólo en **ingresos** de mercadería (creación de lote nuevo):

```
nuevo_cpp = (stock_anterior * costo_anterior + cantidad_nueva * costo_nuevo)
            / (stock_anterior + cantidad_nueva)
```

Las salidas (ventas, mermas) NO modifican el CPP — solo descuentan stock al CPP vigente.

No se reprocesan facturas históricas. El CPP arranca con el costo actual al momento de la migración.

### 2.4 Alerta de vencimientos
Default = 30 días, configurable por empresa via `empresas.dias_alerta_vencimiento` (nueva columna, default 30). Se mostrará en el dashboard cuando haya lotes que vencen en ese rango.

---

## 3. Modelo de datos

### 3.1 Tabla nueva — `inventario_lotes`

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | UUID PK | Identificador interno |
| `empresa_id` | UUID NOT NULL | Tenant |
| `inventario_id` | UUID NOT NULL FK → inventario(id) | A qué item pertenece |
| `numero_lote` | VARCHAR(50) NOT NULL | Identificador del lote (ej: `L-2025-04-12-A`, `INICIAL`) |
| `cantidad` | DECIMAL(15,4) NOT NULL | Stock vigente del lote (se decrementa con ventas) |
| `cantidad_inicial` | DECIMAL(15,4) NOT NULL | Stock con el que entró el lote (no cambia) |
| `costo_unitario` | DECIMAL(15,2) NOT NULL | Costo unitario al ingresar el lote |
| `fecha_ingreso` | DATE NOT NULL | Cuándo entró |
| `fecha_vencimiento` | DATE NULL | Cuándo vence (NULL = no vence) |
| `proveedor_id` | UUID NULL FK → proveedores(id) | De quién vino |
| `comprobante_id` | UUID NULL FK → comprobantes(id) | Factura de compra origen |
| `notas` | TEXT NULL | Observaciones del operador |
| `fecha_creacion` | TIMESTAMPTZ NOT NULL DEFAULT NOW() | Auditoría |

Índices:
- `(empresa_id, inventario_id, fecha_vencimiento NULLS LAST, fecha_ingreso)` — para queries FEFO.
- `(empresa_id, fecha_vencimiento) WHERE cantidad > 0 AND fecha_vencimiento IS NOT NULL` — para alertas.

### 3.2 Tabla nueva — `inventario_movimientos` (kardex)

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | UUID PK | |
| `empresa_id` | UUID NOT NULL | |
| `inventario_id` | UUID NOT NULL FK | Item afectado |
| `lote_id` | UUID NULL FK → inventario_lotes | Lote consumido o creado |
| `tipo` | VARCHAR(20) NOT NULL CHECK IN (`ingreso`, `salida`, `ajuste`, `merma`) | |
| `cantidad` | DECIMAL(15,4) NOT NULL | Positivo siempre; el signo lo lleva `tipo` |
| `costo_unitario` | DECIMAL(15,2) NOT NULL | Costo en el momento del movimiento |
| `cpp_resultante` | DECIMAL(15,2) NOT NULL | Costo promedio del item tras el movimiento |
| `fecha` | DATE NOT NULL | |
| `comprobante_id` | UUID NULL FK | Factura origen si aplica |
| `usuario_id` | UUID NULL FK | Quién registró |
| `notas` | TEXT | |
| `fecha_creacion` | TIMESTAMPTZ NOT NULL DEFAULT NOW() | |

Es **append-only**. Sirve como auditoría completa del stock + base para reportes de valuación.

### 3.3 Columna nueva — `empresas.dias_alerta_vencimiento`

`INTEGER NOT NULL DEFAULT 30`. Cada empresa la puede ajustar desde Configuración.

### 3.4 Política RLS

Ambas tablas nuevas reciben policy `tenant_isolation` igual que el resto. Se aplica en el mismo bloque que el resto del SQL del usuario.

---

## 4. Sub-fases

### v7.1 — Foundation (HOY)
- Migración SQL: tablas + columnas + seed `INICIAL`.
- Backend service `lotes.py`: `crear_lote`, `consumir_fefo`, `proximos_vencimientos`, `recalcular_cpp`.
- Backend router `/inventario/lotes`: GET listar, POST crear, GET vencimientos.
- Tests pytest del cálculo de CPP y la selección FEFO.
- Frontend: página `/inventario/lotes` con tabla + filtro por item + alerta de vencimientos.
- Card en dashboard "Lotes por vencer en 30 días".

### v7.2 — Integración con ventas (PENDIENTE — necesita validación con datos reales)
- Al registrar una factura de venta, el backend invoca `consumir_fefo` en cada línea de detalle.
- Se persiste `lote_id` en `detalle_comprobantes` (columna nueva).
- Al anular factura, se reponen los movimientos del kardex.
- Reportes: valuación de inventario al cierre, COGS por período.

### v7.3 — Polish (FUTURO)
- Etiquetado QR/código de barras por lote.
- Trazabilidad inversa: dado un lote, ver clientes que recibieron stock de ese lote.
- Reporte de mermas por lote vencido.

---

## 5. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| El lote `INICIAL` se mezcla con lotes reales y aparece en alertas raras | `fecha_vencimiento = NULL` lo excluye automáticamente de queries de vencimiento |
| Items sin stock que igual tienen lotes huérfanos | Migración solo crea lote si `cantidad_actual > 0`. Para items con stock 0, el primer ingreso futuro crea el primer lote |
| CPP de partida puede no ser el "real" si los costos actuales no estaban bien cargados | Aceptado por PM: arrancamos desde la foto actual, no reprocesamos historia |
| FEFO con mucho stock y muchos lotes puede ser lento | Índice compuesto sobre `(empresa_id, inventario_id, fecha_vencimiento NULLS LAST)` |
| Anulación de factura con lotes mezclados → cuál stock devolver | Resuelto en v7.2 vía kardex: la salida original sabe a qué lote tocó, se reversa con precisión |
| Ingreso manual y luego corrección con monto distinto | El usuario puede registrar un movimiento de "ajuste" que recalcula CPP. v7.2. Por ahora, el flujo es crear el lote correcto o eliminar el incorrecto |

---

## 6. Definition of Done v7.1

- [x] Migración SQL idempotente
- [x] Backend service compila + tests verdes
- [x] Endpoint funcional en /openapi.json
- [x] Frontend lista lotes y muestra alertas
- [x] Dashboard tiene card de vencimientos próximos
- [x] Bitácora + SDD actualizados

v7.2 requiere validación con PM tras testing con datos reales.
