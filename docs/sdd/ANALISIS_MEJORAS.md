# 🎯 Análisis de mejoras — ERP Esplendida PY

> **Auditoría profunda desde dos perspectivas:** diseño de producto y gestión financiera.
> 24 oportunidades de mejora · 8 de diseño · 11 de finanzas · 5 quick wins · Roadmap de 10 semanas

---

## Resumen ejecutivo

El sistema tiene una base sólida y las mejoras de v6.0/v6.1 (sidebar, mapa real, BOM, aging, P&L, forecast) lo pusieron varios escalones por encima del nivel típico de un ERP local. Pero todavía hay **3 brechas grandes**.

> *"Un ERP que solo registra facturas es un cuaderno digital. Un ERP útil te dice qué hacer mañana."*

### Las 3 brechas más importantes

#### 1. BRECHA FINANCIERA
**Falta el "Estado de Resultados real" basado en CMV verdadero.**
Hay P&L básico pero usa CMV estimado (70% de las compras). Para ser preciso necesita BOM completo + vinculación venta↔producto.

#### 2. BRECHA DE PRODUCCIÓN
**El BOM está implementado pero no usado todavía.**
Las tablas y endpoints están listos en producción, pero hace falta cargar las recetas reales de cada bronceador y crema.

#### 3. BRECHA DE ANTICIPACIÓN
**Forecast asume escenario optimista.**
Toma fechas de vencimiento como verdad absoluta. Falta modelar el patrón real de pago de cada cliente (algunos pagan a 45 días aunque la factura diga 30).

### Mi recomendación de orden

| Semana | Foco |
|---|---|
| **1-2** | Quick wins de adopción (cargar primeras recetas, completar RUCs/teléfonos faltantes) |
| **3-4** | Lotes de producción real (no solo planificación) + CMV preciso en P&L |
| **5-7** | Trazabilidad de lotes con vencimientos |
| **8-10** | Forecast con patrones de pago + alertas predictivas |

---

## 🎨 Mejoras de diseño y experiencia

### D1 — Sobrecarga del dashboard

**Impacto:** 🔴 Alto

El usuario que abre el sistema ve: 3 hero cards, 4 KPIs, gráfico de barras, balanza, concentración, lista de top, últimas facturas, acciones rápidas. Demasiado scroll.

**Propuesta:** Refactorizar en 3 zonas:
- ① Cabecera (lo urgente): card con la decisión del día
- ② Zona principal (lo importante): gráfico con filtro, sin distracciones
- ③ Pie (lo de referencia): tops y últimas, colapsable

**Esfuerzo:** 1 día · Riesgo: bajo

---

### D2 — Inconsistencia visual entre páginas

**Impacto:** 🟡 Medio

Algunas páginas usan `p-8`, otras `p-6`; algunos botones azules, otros índigo; cards con `rounded-2xl` y otros con `rounded-xl`.

**Propuesta:** Crear archivo de **design tokens** en `frontend/src/lib/design-tokens.ts`. Refactorizar páginas para tomar de ahí. Cambios futuros 5× más rápidos.

**Esfuerzo:** 2-3 días

---

### D3 — Empty states genéricos

**Impacto:** 🟡 Medio

Cuando no hay datos: "🤷 Sin items". Oportunidad perdida.

**Propuesta:**
```
ANTES: "🤷 Sin proveedores que coincidan"

DESPUÉS: "📦 No tenés proveedores cargados todavía.
Los proveedores son las empresas que te venden insumos como Uruku, frascos, tapas.

[+ Cargar mi primer proveedor]"
```

**Esfuerzo:** 1 día (todas las páginas)

---

### D4 — Skeleton loaders

**Impacto:** 🟡 Medio

"Cargando clientes..." genera percepción de lentitud.

**Propuesta:** Componente `<Skeleton>` con animación shimmer. Reemplazar todos los "Cargando..." por skeletons. **Bonus:** usuario percibe la app 30% más rápida sin cambios reales de performance.

**Esfuerzo:** 1 día

> ✅ Ya implementado en v6.0. Falta usarlo en todas las páginas.

---

### D5 — Mobile sin búsqueda global

**Impacto:** 🟡 Medio

En celular no hay búsqueda persistente, no hay acceso rápido al asistente IA, los breadcrumbs no aparecen.

**Propuesta:** Agregar al header móvil: barra de búsqueda persistente (ícono lupa que expande), menú radial con 5 acciones más usadas.

**Esfuerzo:** 2 días

---

### D6 — Dark mode

**Impacto:** 🟢 Bajo

El sidebar es oscuro pero el resto siempre claro. La gente que trabaja muchas horas con ERP suele preferir dark mode.

**Propuesta:** Toggle en perfil de usuario. Si hay design tokens (D2), es 1 día.

**Esfuerzo:** 1-4 días

---

### D7 — Microinteracciones

**Impacto:** 🟢 Bajo

Al guardar una factura simplemente cierra el modal. Falta feedback emocional positivo.

**Propuestas:**
- Toast con animación slide-in al guardar
- Animación de check verde al confirmar acciones críticas
- Mini confetti al cargar la 100ª factura del mes
- Animación de la card cuando una factura se marca como "pagada"

**Esfuerzo:** 2-3 días

---

### D8 — Búsqueda global con Ctrl+K

**Impacto:** 🟡 Medio

El sidebar tiene un botón "Ctrl K" pero no funciona aún.

**Propuesta:** Implementar modal de búsqueda que indexe clientes, proveedores, productos, facturas. Tipo Linear/Notion.

**Esfuerzo:** 3-4 días

---

## 💰 Mejoras de gestión financiera

### F1 — CMV preciso en P&L (no estimado)

**Impacto:** 🔴 CRÍTICO

El P&L actual estima CMV en 70% de las compras. Para precisión necesita:
- BOM cargado por producto ✅ (ya está)
- Vincular cada línea de venta con el producto vendido
- Calcular CMV = sum(receta.costo_unitario × cantidad_vendida)

**Esfuerzo:** 5-7 días · Necesita BOM cargado primero

---

### F2 — Lotes de producción ejecutables

**Impacto:** 🔴 Alto

La tabla `lotes_produccion` existe pero solo permite planificar. Falta:
- Marcar lote como "en proceso" → descuenta insumos del stock
- Marcar como "completado" → suma producto terminado al stock
- Trazabilidad: qué lote se vendió a qué cliente

**Esfuerzo:** 4-5 días

---

### F3 — Trazabilidad de lotes con vencimientos

**Impacto:** 🟡 Medio

La industria cosmética en Paraguay tiene regulaciones de DINAVISA/MSPyBS sobre trazabilidad.

**Propuesta:** Agregar tablas:
- `lotes_movimientos`: lote, entrada/salida, factura asociada
- Alerta cuando un lote está por vencer

Útil para retiros de mercado o reclamos de calidad. **Diferenciador competitivo.**

**Esfuerzo:** 6-8 días

---

### F4 — Valuación de inventario con CPP

**Impacto:** 🟡 Alto

Existe "Total en stock" pero falta método de valuación claro (LIFO, FIFO, promedio ponderado).

**Propuesta:** Implementar **costo promedio ponderado (CPP)**. Cada compra recalcula el costo unitario promedio. Agregar pantalla "Movimientos de inventario".

**Esfuerzo:** 4-5 días

---

### F5 — Forecast con patrones reales

**Impacto:** 🟡 Alto

El forecast actual asume que todos pagan en fecha de vencimiento. La realidad: cada cliente paga con su propio ritmo.

**Propuesta:**
- Calcular el "días promedio de pago" por cliente histórico
- Ajustar el forecast usando ese ritmo
- Mostrar 3 escenarios: optimista, realista, pesimista

**Esfuerzo:** 4-5 días

---

### F6 — Presupuesto anual

**Impacto:** 🟡 Medio

Endpoint `/presupuestos` existe pero sin UI.

**Propuesta:** Pantalla "Presupuesto" para cargar montos esperados por mes y categoría. En el dashboard: "Llevás 78% del objetivo del mes".

**Esfuerzo:** 3-4 días

---

### F7 — Términos de pago por cliente/proveedor

**Impacto:** 🟡 Medio

Algunos clientes pagan a 30 días, otros a 60, otros contado.

**Propuesta:** Campo `plazo_pago_dias` en clientes y proveedores. Al crear factura, calcular vencimiento automático. Alertar si la fecha manual difiere mucho.

**Esfuerzo:** 2 días

---

### F8 — Análisis de concentración de proveedores

**Impacto:** 🟢 Medio

Ya hay concentración de clientes. Falta para proveedores.

**Propuesta:** Card similar a `ClientConcentration` en página de proveedores. Si el 80% de las compras viene de 1 proveedor, hay riesgo.

**Esfuerzo:** 1-2 días

---

### F9 — Estacionalidad

**Impacto:** 🟢 Bajo

Los bronceadores tienen pico en verano (Nov-Mar). Comparar "vs mes anterior" es engañoso en negocio estacional.

**Propuesta:** Comparativa "Ventas de este mes vs el mismo mes del año pasado y dos años atrás".

**Esfuerzo:** 1 día

> ✅ Ya implementado en v6.0 (toggle "Comparar año anterior" en el gráfico de flujo).

---

### F10 — Alertas predictivas

**Impacto:** 🟢 Bajo pero alto WOW

Falta sistema que avise ANTES de que pase algo malo.

**Propuestas:**
- "Al ritmo actual de ventas, vas a quedarte sin Frascos Oval Dorado en 12 días"
- "CASA RICA tiene un patrón de pago a 45-50 días. Esta factura está vencida hace 55 — considera llamar"
- "El IVA de este mes va a ser ~Gs. 65M según tu ritmo de facturación"
- "El costo del Uruku subió 22% en las últimas 3 compras — revisar precios de venta"

**Esfuerzo:** 5-6 días

---

### F11 — Estado de Flujo de Efectivo (Cash Flow Statement)

**Impacto:** 🟢 Medio

Falta el clásico estado contable: actividades operativas, de inversión, de financiamiento.

**Esfuerzo:** 4-5 días · Requiere clasificación de gastos por plan de cuentas

---

## ⚡ Quick wins (1 semana)

| # | Tarea | Esfuerzo | Impacto |
|---|---|---|---|
| 1 | **Cargar las primeras 5 recetas reales** de Esplendida | 1 día | 🔴 Alto |
| 2 | Completar RUC + teléfono + ciudad de los clientes principales | 1 día | 🟡 Medio |
| 3 | Configurar `punto_reorden` en todos los insumos críticos | 0.5 día | 🟡 Medio |
| 4 | Cargar precio de venta sugerido en productos terminados | 0.5 día | 🔴 Alto (habilita margen automático) |
| 5 | Mejorar empty states en clientes/proveedores/inventario | 1 día | 🟡 Medio |

**Total: ~4 días** — sin necesidad de tocar código en algunas tareas.

---

## 📅 Roadmap completo de 10 semanas

### Fase A — Adopción del BOM (1 semana)
- S1: Cargar recetas reales · Completar datos maestros · Configurar punto_reorden

### Fase B — Producción funcional (2 semanas)
- S2-3: Lotes ejecutables (descuentan insumos al completarse, suman terminados)

### Fase C — Finanzas precisas (2 semanas)
- S4-5: CMV preciso en P&L · Presupuesto · Términos de pago

### Fase D — Diseño y consistencia (1 semana)
- S6: Design tokens + Skeleton loaders + Empty states accionables

### Fase E — Anticipación (3 semanas)
- S7-9: Forecast con patrones reales · Alertas predictivas · Trazabilidad de lotes

### Fase F — Polish (1 semana)
- S10: Dark mode · Búsqueda global · Microinteracciones

---

## 📊 Esfuerzo total estimado

| Fase | Días |
|---|---|
| A — Adopción BOM | 4 |
| B — Producción | 10 |
| C — Finanzas precisas | 10 |
| D — Diseño | 5 |
| E — Anticipación | 15 |
| F — Polish | 5 |
| **Total** | **49 días** (~10 semanas) |

---

> Mi recomendación honesta: empezá por la **Fase A** (4 días). Cuando lo veas funcionando, el negocio te va a pedir B sola. Si paralelizamos diseño (D) con finanzas (C), llegás al mes 2 con un sistema de otra categoría.

---

📖 **Más documentación:** [SDD técnico](SDD.md) · [Guía de usuario](GUIA_USUARIO.md) · [Guía deploy Supabase](GUIA_SUPABASE_DEPLOY.md)
