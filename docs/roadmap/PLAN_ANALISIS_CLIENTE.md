# Plan — Análisis histórico por cliente

> **Versión:** v1.1 · 2026-05-13
> **Autor:** Claude (revisión técnica) · Aprobación pendiente: PM
> **Estado:** 📋 Planificado — sin implementar todavía
> **Tiempo estimado:** 10–14 h de desarrollo · 0 cambios destructivos en DB

## Cambios v1.1 (2026-05-13)

A pedido del PM se eliminó la idea de pestañas. La pantalla queda como **una sola página scrolleable**, sin navegación adicional, manteniendo la simplicidad de la pantalla actual. Toda la información se apila de arriba a abajo: lo más importante arriba (score + saldo), los detalles abajo. El usuario hace scroll, no clicks.

---

## 1. ¿Qué problema resuelve?

Hoy en `/cuentas/cliente/{id}` se muestra el estado de cuenta básico: facturas y pagos. Falta una vista que responda preguntas reales del negocio:

- **¿Este cliente me devuelve mucha mercadería?** → ¿cuánto y qué productos?
- **¿Es buen pagador?** → ¿cuántos días tarda en promedio?
- **¿Cuánto me compra realmente?** → neto de devoluciones, no bruto
- **¿Qué productos prefiere?** → top de items que más le vendí
- **¿Vale la pena seguir vendiéndole?** → score simple (verde/amarillo/rojo)
- **¿Cuándo me compró por última vez?** → señal de alerta si está dormido

Toda la información ya existe en la base de datos. Solo falta presentarla bien.

---

## 2. Pantalla nueva: una sola página, sin pestañas

Se mantiene la URL actual `/cuentas/cliente/{id}` y `/cuentas/proveedor/{id}`. La pantalla **agrega información arriba** y **conserva las listas actuales abajo**. Sin pestañas, sin tabs, sin sub-navegación. El usuario hace scroll.

### Orden visual de arriba a abajo

```
┌─────────────────────────────────────────────────────────┐
│ ① Encabezado: nombre + RUC + score + botón volver       │
├─────────────────────────────────────────────────────────┤
│ ② Resumen del negocio (6 números clave)                 │
├─────────────────────────────────────────────────────────┤
│ ③ Hábitos de pago (1 línea de texto + 3 números)        │
├─────────────────────────────────────────────────────────┤
│ ④ Devoluciones (solo si tiene — sino se oculta)         │
├─────────────────────────────────────────────────────────┤
│ ⑤ Productos que más te compra (top 5, no top 10)        │
├─────────────────────────────────────────────────────────┤
│ ⑥ Lista de facturas (idéntica a la actual)              │
├─────────────────────────────────────────────────────────┤
│ ⑦ Lista de pagos (idéntica a la actual)                 │
└─────────────────────────────────────────────────────────┘
```

**Principio:** todo lo nuevo está en la mitad superior (compacto, fácil de leer en una pasada de ojos). La mitad inferior es lo que ya conocen los usuarios — no se les cambia el lugar de las cosas.

### ① Encabezado

```
┌────────────────────────────────────────────────────────────────┐
│ 👤 CADENA REAL S.A.                          [editar] [volver]│
│ RUC 80012345-6  ·  Cliente desde marzo 2023                   │
│                                                                │
│  🟢 Cliente saludable          → ver por qué                  │
└────────────────────────────────────────────────────────────────┘
```

Score 🟢🟡🔴 con popover explicativo (al hacer click, panel de 3 líneas con las razones).

### ② Resumen del negocio

6 números en grilla 3×2 (en mobile, 2×3). Cada uno con su explicación al pasar el mouse.

| Total facturado | Devoluciones | Compra neta |
|---|---|---|
| ₲ 45.200.000 | ₲ 3.150.000 (7%) | ₲ 42.170.000 |
| **Ya cobrado** | **Saldo pendiente** | **Cargos extra** |
| ₲ 38.000.000 | ₲ 4.170.000 | ₲ 120.000 |

> Si no hay devoluciones ni cargos extra, esos dos números se ocultan y queda 4 números (grilla 2×2 ó 4×1). No se muestran ceros para no agregar ruido visual.

### ③ Hábitos de pago

Una sola línea con los datos importantes, sin tabla:

> Paga en promedio en **23 días** · Última compra hace **12 días** · Suele pagar por **transferencia** (78%)

Si tiene saldo +60 días, se agrega una segunda línea en ámbar/rojo:
> ⚠ Tiene facturas vencidas hace más de 60 días

### ④ Devoluciones (solo si tiene)

Si el cliente nunca tuvo NC/ND, **toda la sección se oculta** — cero ruido.

Si tiene, se muestra una sola sub-sección compacta:

> 📦 Te devolvió mercadería **5 veces** por un total de **₲ 3.150.000** (7% de sus compras).

Debajo, una tabla pequeña de **máximo 5 filas** con los productos más devueltos:

| Producto | Veces | Cantidad | Valor |
|---|---|---|---|
| Crema Hidratante 250ml | 4 | 23 u | ₲ 1.150.000 |
| Bronceador FPS 30 | 2 | 8 u | ₲ 600.000 |
| … | … | … | … |

Botón discreto al final: **"Ver las 5 devoluciones"** — abre un **modal** (no una pestaña nueva) con la lista completa de NC. Mismo patrón si tiene ND: aparecen en el modal abajo de las NC.

> No hay timeline ni gráfico de barras de 12 meses — se eliminó por simplicidad. Si el PM lo pide después, se agrega.

### ⑤ Productos que más te compra

Top **5** (no 10) en una mini-tabla:

| Producto | Cantidad | Total |
|---|---|---|
| Bronceador FPS 15 200ml | 320 u | ₲ 12.800.000 |
| Crema Aloe 200ml | 240 u | ₲ 9.600.000 |
| … | … | … |

Sin gráfico de torta. Solo la tabla.

### ⑥ y ⑦ Listas de facturas y pagos

**Sin cambios respecto a la pantalla actual.** Se conservan exactamente como están. El usuario que ya conoce el sistema sigue encontrando las cosas en el mismo lugar.

---

## 3. Backend — qué endpoints hay que tocar

Casi todo se puede armar con un solo endpoint nuevo que extiende el existente.

### Endpoint nuevo

```
GET /pagos/analisis-cliente/{cliente_id}
GET /pagos/analisis-proveedor/{proveedor_id}
```

Devuelve un JSON con todas las secciones de la pantalla precalculadas:

```json
{
  "cliente": { "id": "...", "nombre": "...", "ruc": "...", "fecha_alta": "..." },
  "resumen": {
    "total_facturado": "45200000",
    "total_devoluciones": "3150000",
    "total_cargos_extra": "120000",
    "compra_neta": "42170000",
    "ya_cobrado": "38000000",
    "saldo_pendiente": "4170000",
    "porcentaje_devolucion": 7.0
  },
  "score": { "color": "verde", "razones": ["paga puntual", "devoluciones bajo 10%"] },
  "devoluciones": {
    "por_mes": [{ "mes": "2025-04", "monto": "1200000" }, ...],
    "top_productos": [{ "producto": "...", "veces": 4, "cantidad": "23", "monto": "1150000" }, ...],
    "notas_credito": [{ "id": "...", "numero": "NC-...", "fecha": "...", "monto": "...", "factura_origen": "..." }, ...]
  },
  "cargos_extra": {
    "notas_debito": [{ "id": "...", "numero": "ND-...", "fecha": "...", "monto": "...", "factura_origen": "..." }, ...]
  },
  "top_productos": [{ "producto": "...", "cantidad": "...", "ventas": 18, "total": "..." }, ...],
  "habitos_pago": {
    "promedio_dias": 23,
    "mejor_dias": 5,
    "peor_dias": 67,
    "medio_favorito": "transferencia",
    "porcentaje_medio_favorito": 78,
    "ultima_compra": "2026-05-01",
    "dias_desde_ultima_compra": 12
  }
}
```

### Queries SQL clave

Todas reutilizan tablas existentes (`comprobantes`, `detalle_comprobantes`, `pagos`):

```sql
-- Devoluciones por mes (Notas de Crédito)
SELECT DATE_TRUNC('month', fecha_emision) AS mes, SUM(monto_total) AS monto
FROM comprobantes
WHERE cliente_id = $1
  AND tipo = 'venta'
  AND comprobante_origen_id IS NOT NULL  -- es una NC vinculada a una factura
  AND estado_validacion = 'confirmado'
GROUP BY 1 ORDER BY 1 DESC LIMIT 12;

-- Top productos devueltos
SELECT i.nombre,
       COUNT(DISTINCT c.id) AS veces,
       SUM(d.cantidad) AS cantidad,
       SUM(d.subtotal) AS monto
FROM comprobantes c
JOIN detalle_comprobantes d ON d.comprobante_id = c.id
JOIN inventario i ON i.id = d.inventario_id
WHERE c.cliente_id = $1
  AND c.tipo = 'venta'
  AND c.comprobante_origen_id IS NOT NULL
  AND c.estado_validacion = 'confirmado'
GROUP BY i.id, i.nombre
ORDER BY monto DESC LIMIT 10;

-- Promedio de días entre fecha_emision y fecha_pago
SELECT AVG(p.fecha_pago - c.fecha_emision)::int AS promedio_dias
FROM comprobantes c
JOIN pagos p ON p.comprobante_id = c.id
WHERE c.cliente_id = $1 AND c.tipo = 'venta';
```

### Performance

- Caché de React Query: 60s por cliente (los datos no cambian segundo a segundo)
- En backend: si una empresa tiene > 10.000 facturas por cliente, considerar una vista materializada `mv_analisis_cliente` refrescada cada hora. **No urgente** — primero medir.

---

## 4. Frontend — archivos a tocar

Mínima superficie de cambio: la página actual gana 4 secciones nuevas arriba; el resto queda igual.

| Archivo | Acción |
|---|---|
| `frontend/src/app/(app)/cuentas/[tipo]/[id]/page.tsx` | Agregar las secciones ①–⑤ arriba; conservar ⑥ ⑦ tal cual |
| `frontend/src/components/AnalisisCliente/ScoreBadge.tsx` (NUEVO) | Score 🟢🟡🔴 con popover de razones |
| `frontend/src/components/AnalisisCliente/Devoluciones.tsx` (NUEVO) | Resumen ④ + tabla top 5 + modal con lista completa |
| `frontend/src/lib/api.ts` | Agregar `pagosApi.analisisCliente(id)` / `analisisProveedor(id)` |
| `frontend/src/lib/types.ts` | Tipo `AnalisisCliente` |

**No se crean** componentes separados para Resumen, Hábitos ni Top productos — son tan compactos que viven inline en la página principal (3-15 líneas JSX cada uno). Solo se aíslan en componentes los dos elementos con lógica propia: el score (popover) y las devoluciones (modal).

Dependencias: ya están todas (decimal.js, React Query). Sin Recharts, sin librerías nuevas.

---

## 5. Definición del score (Verde / Amarillo / Rojo)

Regla simple y transparente — el usuario ve por qué está en cada color.

```
puntos = 100
si % devoluciones > 10%:   puntos -= 20
si % devoluciones > 20%:   puntos -= 30 más
si promedio_dias_pago > vencimiento promedio + 7:  puntos -= 15
si tiene saldo +60 días:   puntos -= 25
si no compra hace +90 días: puntos -= 15

100–75 = 🟢 Saludable
74–50  = 🟡 A revisar
49–0   = 🔴 Riesgo
```

Mostrar siempre las razones. Si el cliente está en amarillo "porque tardó 45 días en pagar dos veces", el usuario lo ve y decide.

---

## 6. Mismo análisis para proveedores

La pantalla y el endpoint son **simétricos** — solo cambia el sentido de las operaciones:

- "Total facturado" → "Total comprado a este proveedor"
- "Devoluciones" → "Mercadería que le devolvimos" (NC recibidas)
- "Cargos extra" → "Recargos que nos facturó" (ND recibidas)
- "Hábitos de pago" → "Cuándo solemos pagarle"
- Score → indica si **vos** sos buen cliente para él (útil para negociar plazos)

---

## 7. Sub-fases de implementación

Menos sub-fases que la v1.0 porque al no haber pestañas hay menos componentes que armar.

| Sub-fase | Contenido | Tiempo |
|---|---|---|
| **A.1** | Endpoint backend `/pagos/analisis-cliente/{id}` con queries + tests | 4 h |
| **A.2** | Tipo `AnalisisCliente` en frontend + cliente API + caché | 1 h |
| **A.3** | Secciones ① ② ③ inline en la página actual (encabezado, resumen, hábitos) | 2 h |
| **A.4** | Componente `Devoluciones` con tabla + modal (sección ④) | 2 h |
| **A.5** | Sección ⑤ inline (top 5 productos) + Score con popover | 1.5 h |
| **A.6** | Versión simétrica para proveedores | 1 h |

Total: **~11.5 h** (antes 14 h). Se puede dividir en 2 entregas:
- **Entrega 1:** A.1 + A.2 + A.3 (~7 h) — el cliente ya ve score, resumen y hábitos
- **Entrega 2:** A.4 + A.5 + A.6 (~4.5 h) — devoluciones, top productos, proveedores

---

## 8. Verificación

- `python -m pytest -q` debe pasar (agregar 3 tests al endpoint nuevo: cliente con NC, cliente sin compras, cliente con pagos parciales)
- `npm run lint && npm run build` 0 errores
- Probar en producción con un cliente real que tenga ≥ 1 NC, ≥ 5 pagos y ≥ 10 facturas
- Verificar que el cálculo de score sea idéntico al manual (devoluciones / facturado)

---

## 9. Reglas de lenguaje (importante)

Para mantener el sistema simple, evitamos jerga técnica en la UI:

| ❌ No usar | ✅ Usar |
|---|---|
| "Nota de Crédito" como título | "Devolución" |
| "Nota de Débito" como título | "Cargo extra" |
| "DSO" / "Days Sales Outstanding" | "Días que tarda en pagar" |
| "Concentración HHI" | "Cuánto depende de este cliente" |
| "Comprobante de venta" | "Factura" |

Si el usuario quiere ver el nombre técnico (ej: el número exacto de la NC), aparece **en pequeño debajo** del nombre simple, no como título principal.

---

## 10. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Cliente con 5.000 facturas — la pantalla puede ser lenta | El backend devuelve todo precalculado en 1 JSON; la lista de facturas ya pagina hoy |
| Empresa con poco historial — score sin sentido | Mostrar "Datos insuficientes" si hay < 3 facturas |
| Devoluciones no vinculadas a factura origen (NC libres) | Detectar `comprobante_origen_id IS NULL` y mostrar aparte en el modal como "Notas de crédito sueltas" |
| Cliente con saldo a favor | Aceptar saldo negativo; mostrar "Te debe" en verde y "Le debés" en rojo |
| **Pantalla larga en mobile** | Las secciones ②–⑤ son compactas (≤ 4 líneas cada una); en total agregan ~25 vh sobre la pantalla actual |

---

## 11. Estado actual y siguiente paso

- ✅ Plan documentado
- ⏳ Pendiente aprobación del PM
- 🚀 Si aprueba: arrancar por A.1 (backend) — es la base y se puede testear con curl antes de tocar UI
