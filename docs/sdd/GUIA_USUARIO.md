# 📖 Guía de uso — ERP Esplendida PY

> Manual completo para administradores y operadores del Laboratorio Esplendida

---

## 📑 Contenido

1. [Bienvenida](#1-bienvenida)
2. [Primer ingreso](#2-primer-ingreso)
3. [Cómo navegar](#3-cómo-navegar)
4. [Tareas frecuentes](#tareas-frecuentes)
   - [Cargar una factura](#41-cargar-una-factura)
   - [Registrar un cobro](#42-registrar-un-cobro)
   - [Registrar un pago](#43-registrar-un-pago)
   - [Crear cliente o proveedor](#44-crear-un-cliente-o-proveedor)
   - [Inventario](#45-inventario)
   - [Recetas (BOM)](#46-recetas-bom)
5. [Pantallas principales](#5-pantallas-principales)
6. [Conceptos clave](#6-conceptos-clave)
7. [Roles y permisos](#7-roles-y-permisos)
8. [Atajos y tips](#8-atajos-y-tips)
9. [Preguntas frecuentes](#9-preguntas-frecuentes)
10. [Si algo falla](#10-si-algo-falla)

---

## 1. Bienvenida

El ERP de **Esplendida** es el sistema interno para gestionar las operaciones del laboratorio: registrar facturas, controlar stock de insumos y productos terminados, llevar cuentas corrientes de clientes y proveedores, y revisar el flujo financiero.

> 💡 Reemplaza planillas Excel y el viejo programa desktop. Todo lo que antes anotabas a mano ahora vive acá, accesible desde cualquier dispositivo con internet.

### ¿Qué vas a poder hacer?

| Módulo | Para qué sirve |
|---|---|
| 🧾 **Facturas** | Cargar facturas de venta y compra, manualmente o sacando una foto |
| 💰 **Cobros y pagos** | Registrar pagos parciales o totales, ver quién debe qué |
| 📦 **Inventario** | Stock de bronceadores, cremas, frascos, tapas y materias primas |
| 🧪 **Recetas (BOM)** | Definir qué insumos lleva cada producto y cuánto cuesta producirlo |
| 👥 **Clientes** | Datos, cuenta corriente y mapa de ubicación |
| 📊 **Reportes** | IVA mensual, P&L, forecast de caja, aging |
| 🤖 **Asistente IA** | Preguntar al chatbot en lenguaje natural |

---

## 2. Primer ingreso

1. **Abrí la URL del sistema**
   En la nube: la URL que te pasó administración. En local: `http://localhost:3000`

2. **Ingresá tu usuario y contraseña**
   El email que te dieron al darte de alta. Si no la recordás, hacé click en "¿Olvidaste tu contraseña?"

3. **Vas a entrar al *Inicio***
   Ahí ves un resumen del día: lo que te deben, lo que debés, las facturas vencidas, y un gráfico de los últimos meses.

> ⚠️ **Importante:** Si no usás el sistema durante **30 minutos**, te va a cerrar la sesión por seguridad. Te avisa 60 segundos antes. Cualquier movimiento del mouse reinicia el temporizador.

---

## 3. Cómo navegar

El sistema usa un **menú lateral oscuro** a la izquierda con todas las opciones agrupadas por área. En celular, el menú se mueve a la parte de abajo de la pantalla.

### Las 5 áreas del menú

| Área | Qué incluye |
|---|---|
| **Vista general** | Inicio (dashboard), Timeline (historia mes a mes), Asistente IA |
| **Ventas** | Facturas de venta, Cobros, Clientes |
| **Compras** | Facturas de compra, Foto OCR, Pagos, Proveedores |
| **Producción** | Inventario, Recetas, Capacidad |
| **Finanzas** | Cuentas corrientes, Cobros vencidos (Aging), Resumen IVA, Resultados (P&L), Forecast de caja |

> 💡 **Tip:** Si necesitás más espacio en pantalla, hacé click en la flechita ⟨ a la derecha del menú lateral.

### Migas de pan

Arriba de cada pantalla vas a ver `Inicio › Clientes › Detalle`. Eso te dice dónde estás y te permite volver a cualquier paso anterior con un click.

---

## Tareas frecuentes

### 4.1 Cargar una factura

Hay **3 maneras** de cargar una factura:

#### 📸 Opción A — Por foto (recomendada para facturas de compra)

1. Andá a **Compras → Foto OCR**
2. Sacá una foto o subí el PDF de la factura
3. El sistema usa Gemini (IA de Google) para leer los datos automáticamente
4. Revisá los datos extraídos — vienen pre-llenados, corregí si algo está mal
5. Click en **Guardar**

> ✅ **Cuándo conviene:** Factura de proveedor en papel o PDF. Te ahorra ~3 minutos por factura.

#### ✍️ Opción B — Carga manual

1. Andá a **Ventas → Facturas de venta** o **Compras → Facturas de compra**
2. Click en **+ Nueva factura**
3. Completá: tipo, número, fecha, cliente o proveedor
4. Agregá los items uno por uno (descripción, cantidad, precio unitario **sin IVA**, % de IVA)
5. Verificá el total — se calcula automáticamente
6. Click en **Guardar**

> ⚠️ **Sobre el precio:** Siempre se carga el precio **NETO (sin IVA)**. El sistema le suma el IVA automáticamente.

#### 📊 Opción C — Importación masiva

Si tenés muchas facturas históricas, podemos preparar una plantilla Excel y subirlas todas juntas.

---

### 4.2 Registrar un cobro

Cuando un cliente te paga (total o parcialmente) una factura:

1. Andá a **Ventas → Cobros**
2. Click en **+ Nuevo cobro**
3. Buscá la factura
4. Ingresá el monto cobrado (puede ser parcial o total)
5. Elegí el medio de pago (efectivo, transferencia, cheque, etc.)
6. Si fue transferencia o cheque, vinculá la cuenta bancaria
7. **Confirmá**

> ✅ El saldo del cliente se actualiza al instante. Tenés 5 segundos para deshacer si te equivocaste.

---

### 4.3 Registrar un pago

Cuando vos le pagás a un proveedor por una factura de compra:

1. Andá a **Compras → Pagos**
2. Click en **+ Nuevo pago**
3. Buscá la factura de compra
4. Ingresá el monto pagado
5. Elegí cómo pagaste
6. **Confirmá**

---

### 4.4 Crear un cliente o proveedor

1. Andá a **Ventas → Clientes** o **Compras → Proveedores**
2. Click en **+ Nuevo cliente / proveedor**
3. Completá:
   - Nombre o razón social (obligatorio)
   - RUC
   - Teléfono
   - **Dirección/ciudad** ← importante para el mapa

> 💡 **Pro tip:** Incluí la **ciudad** en la dirección (ej: "Av. Mcal López, Asunción"). Así el cliente aparece en el mapa de Paraguay.

### El mapa de Paraguay

En la pantalla de Clientes hay un mapa real (OpenStreetMap) a la derecha donde aparecen marcadores. El sistema detecta la ciudad automáticamente desde la dirección o el nombre.

- 🟢 **Verde** — cliente al día (saldo bajo o cero)
- 🟡 **Amarillo** — cliente con saldo medio
- 🔴 **Rojo** — cliente con saldo alto

Click en un marcador → filtra la lista a clientes de esa ciudad.

---

### 4.5 Inventario

Acá vive el stock de Esplendida: bronceadores y cremas (productos terminados) e insumos (frascos, tapas, etiquetas, materias primas).

#### Categorías visuales

| Categoría | Color | Ejemplos |
|---|---|---|
| 🧴 **Bronceadores** | Amarillo | Producto estrella |
| 🫧 **Cremas** | Rosa | Línea facial/corporal |
| 🍶 **Frascos** | Azul | Envases |
| 🔒 **Tapas** | Violeta | Atomizadores y disc-top |
| 🏷️ **Etiquetas** | Verde | Frente y dorso |
| 🌿 **Materia prima** | Naranja | Extractos, aceites |

#### Semáforo de stock

| Color | Significa |
|---|---|
| 🟢 **Verde** | Stock saludable (más de 2× el punto de reorden) |
| 🟡 **Amarillo** | Atención (entre 1× y 2× el punto de reorden) |
| 🔴 **Rojo** | ¡Crítico! Pedir ya |
| ⚪ **Gris** | Sin punto de reorden configurado (no avisa) |

#### Agregar un nuevo item

1. Click en **+ Nuevo item**
2. Empezá a escribir el nombre → aparecen **sugerencias** (plantillas genéricas + items existentes)
3. Click en una plantilla para autocompletar (ahorra tiempo)
4. Completá código, unidad de medida
5. Cargá stock actual y costo unitario
6. **Definí el "punto de reorden"** — cantidad mínima a partir de la cual querés alerta

> ⚠️ Si todos tus productos figuran como "OK" pero sabés que faltan algunos, es porque **el punto de reorden está en 0**. Pasá por cada producto y completá ese campo.

---

### 4.6 Recetas (BOM)

> 🧪 Define qué ingredientes lleva cada producto terminado y cuánto cuesta producirlo.

#### Crear una receta

1. Andá a **Producción → Recetas**
2. Click en **+ Nueva receta**
3. Elegí el **producto terminado** (bronceador, crema)
4. Definí: nombre, versión, **rendimiento** (cuántas unidades por batch)
5. Agregá ingredientes uno por uno:
   - Insumo (frasco, tapa, materia prima…)
   - Cantidad y unidad
   - Marcá si es crítico
6. La UI calcula **EN VIVO**:
   - Costo total batch
   - Costo unitario
   - Margen (si hay precio de venta cargado)
7. **Guardar**

#### Ejemplo Esplendida

```
Bronceador FPS 15 — 200mL (rendimiento: 100 unidades)
  - 500g Extracto de Uruku
  - 5L Aceite de coco
  - 100u Frasco Oval 200mL
  - 100u Tapa Atomizador
  - 100u Etiqueta frente
  - 100u Etiqueta dorso

Costo total: Gs. 546.000 / 100 = Gs. 5.460 por unidad
Precio venta: Gs. 12.000
Margen: 54.5%
```

#### Ver capacidad de producción

**Producción → Capacidad** te muestra, para cada receta activa:

- Cuántas unidades podés producir con el stock actual
- Cuántos batches
- **El insumo cuello de botella** (el que limita)

---

## 5. Pantallas principales

### Inicio (Dashboard)

Lo primero que ves al entrar. 5 secciones:

1. **3 Hero Cards** — Por cobrar / Por pagar / Ingresos cobrados
2. **Gráfico Ingresos y egresos** — Barras con filtro de período + opción "comparar año anterior"
3. **Balanza de caja** — Lo que va a entrar vs lo que va a salir
4. **Concentración de clientes** — Tu Top 1/3/5 + análisis de riesgo
5. **Listas y acciones rápidas** — Top deudores, últimas facturas, botones de acción

### Timeline

Vista cronológica agrupada por mes. Útil para ver "qué pasó en mayo" en una sola pantalla.

### Cobros vencidos (Aging)

Clasifica los saldos pendientes por días de atraso:

- Al día (no vencido)
- 1-30 días → seguimiento
- 31-60 días → llamar
- 61-90 días → insistir
- +90 días → 🚨 acciones legales

### Estado de Resultados (P&L)

```
Ventas brutas
− CMV
= Utilidad bruta            (margen %)
− Gastos operativos
= Resultado operativo       (margen %)
− IVA neto
= Resultado del período     (margen neto %)
```

### Forecast de caja

Proyección día por día a 30/60/90 días. Te dice si vas a tener plata para pagar la planilla el día 28.

### Resumen IVA

3 cuadros: IVA ventas (débito), IVA compras (crédito), Diferencia.

---

## 6. Conceptos clave

### 📊 Facturado vs Cobrado

| Facturado | Cobrado |
|---|---|
| Lo que emitiste como factura | La plata que realmente entró |
| Sin importar si te pagaron o no | A caja o cuenta bancaria |
| Aparece en "Por cobrar" y en el gráfico | Aparece en "Ingresos cobrados" |

> 💡 **Ejemplo:** En mayo facturaste Gs. 50M, pero te pagaron Gs. 30M → facturado mayo = Gs. 50M, cobrado mayo = Gs. 30M. La diferencia (Gs. 20M) sigue en "Por cobrar".

### 💰 Neto vs Bruto

- **NETO:** precio sin IVA (lo que cargás)
- **BRUTO o TOTAL:** precio + IVA (lo que el cliente paga)

Ejemplo: producto a Gs. 100.000 neto + 10% IVA = Gs. 110.000 total.

### 🇵🇾 IVA paraguayo

Solo hay 3 tasas válidas:

- **10%** — la mayoría de productos (aplica a cosméticos)
- **5%** — canasta familiar, medicamentos
- **0% (exento)** — exportaciones

---

## 7. Roles y permisos

| Rol | Quién | Permisos |
|---|---|---|
| 🔴 **Admin** | Dueño / gerencia | Todo: configurar empresa, alta de usuarios, anular, plan de cuentas |
| 🟡 **Operador** | Administración | Cargar facturas, pagos/cobros, inventario, ver reportes. NO gestionar usuarios |
| 🟢 **Viewer** | Contador / gerente externo | Solo lectura: dashboards, reportes, P&L. Sin modificar nada |

> Los botones de "Nueva factura", "Nuevo cobro", etc. solo aparecen para roles con permiso de escritura. Si sos Viewer, no los vas a ver — es por diseño.

---

## 8. Atajos y tips

### Teclas útiles

| Tecla | Para qué |
|---|---|
| `Ctrl` + `K` | Búsqueda global (próximamente) |
| `Esc` | Cerrar modal abierto |
| `Tab` | Pasar al siguiente campo |
| `Enter` | Submit en formularios |

### Tips

1. **Cargá facturas el mismo día** que las recibís
2. **Revisá el dashboard cada mañana** para ver qué necesita atención hoy
3. **Configurá el punto de reorden** en cada producto, sino el sistema no avisa
4. **Completá la ciudad de cada cliente** para que aparezca en el mapa
5. **Usá el deshacer** — tenés 5 segundos para cancelar
6. **Exportá a Excel** antes de reuniones con el contador
7. **Preguntale al chatbot** cuando tengas dudas — entiende lenguaje natural

---

## 9. Preguntas frecuentes

### ¿Por qué la columna RUC y Teléfono aparece vacía con "—"?

Probablemente cargaste el cliente sin esos datos. Hacé click sobre el cliente y completalo.

### ¿Por qué todos mis productos figuran como "OK" si sé que faltan?

Porque el **punto de reorden** está en 0 en esos productos. Editá cada producto y poné un mínimo razonable (ej: 500 frascos).

### El IVA muestra Gs. 0 en compras pero sé que cargué compras

Verificá:

1. Las facturas de compra están en estado "Confirmado" (no "Pendiente revisión")
2. Tienen **proveedor** asignado, no cliente
3. Los items tienen porcentaje de IVA (10% o 5%)

### ¿Puedo borrar una factura?

No. Por trazabilidad fiscal, las facturas **no se borran**, solo se anulan.

### Subí una factura con OCR pero los datos están mal

Editá la factura directamente, o anulala y cargala de nuevo manualmente.

### ¿Funciona en celular?

Sí. La interfaz se adapta automáticamente. En el celular el menú aparece abajo.

### ¿Y si me quedo sin internet?

El sistema funciona offline para lecturas. Las operaciones de escritura se guardan en una cola local y se sincronizan cuando vuelve la conexión.

> ⚠️ El OCR y el chatbot necesitan internet siempre.

### ¿Cuándo se cierra mi sesión?

A los 30 minutos sin actividad. Avisa 60 segundos antes.

### ¿Puedo exportar los datos?

Sí, a Excel. Cualquier listado tiene un botón "Exportar" arriba.

---

## 10. Si algo falla

### 🐌 La página tarda en cargar

Si es la primera carga del día, el servidor puede estar "dormido" y tardar 30-60 segundos. Es normal.

### 🔌 "No pude conectarme con el servidor"

- Verificá tu conexión a internet
- Refrescá la página (`Ctrl` + `R`)
- Esperá 1 minuto y volvé a intentar

### 🔒 "Tu sesión expiró"

Ingresá de nuevo con tu usuario y contraseña.

### 🤖 El chatbot no responde

Verificá que tengas internet. Si Gemini está caído, esperá unos minutos.

### 📞 Reportar un bug

Anotá:

- Qué intentaste hacer (paso a paso)
- Qué esperabas que pase
- Qué pasó en realidad
- Captura de pantalla del error
- Tu nombre de usuario y hora aproximada

---

> 📖 Más documentación: [SDD técnico](SDD.md) · [Análisis de mejoras](ANALISIS_MEJORAS.md) · [Guía deploy Supabase](GUIA_SUPABASE_DEPLOY.md)
