# 🚀 Guía de deploy en Supabase — BOM + verificaciones

> Paso a paso para aplicar la migración del Bill of Materials y verificar que todo quedó funcionando. **Tiempo estimado: 5-10 minutos.**

---

## 📋 Contenido

1. [Requisitos previos](#1-requisitos-previos)
2. [Acceso al SQL Editor](#2-acceso-al-sql-editor)
3. [Aplicar la migración SQL](#3-aplicar-la-migración-sql)
4. [Verificar que las tablas se crearon](#4-verificar-que-las-tablas-se-crearon)
5. [Configurar Row Level Security](#5-configurar-row-level-security)
6. [Cargar datos iniciales](#6-cargar-datos-iniciales)
7. [Troubleshooting](#7-troubleshooting)

---

## 1. Requisitos previos

### Lo que necesitás

- ✅ Acceso al proyecto ERP WEB en Supabase con rol `owner` o `developer`
- ✅ URL del proyecto: `https://supabase.com/dashboard/project/skwxkmmnvdojagdruthi`
- ✅ Un navegador

> ⚠️ Si sos colaborador con permisos limitados, es posible que no puedas ejecutar DDL (CREATE TABLE). Pedile al dueño que ejecute la migración o que te promueva al rol `developer`.

---

## 2. Acceso al SQL Editor

1. Andá a https://supabase.com y entrá con la cuenta que tiene acceso al proyecto
2. Click en el proyecto **ERP WEB** (us-east-2)
3. En el menú lateral izquierdo → **SQL Editor**
4. Click en **+ New query** arriba a la derecha

> 💡 Te queda una pestaña en blanco lista para pegar SQL. Acá vas a hacer todos los pasos siguientes.

---

## 3. Aplicar la migración SQL

> ⚠️ **OBLIGATORIO** — Esto crea las tablas, columnas y vistas nuevas.

### 3.1 Copiá el SQL completo

El SQL está en el repo: [`db/migrations/2026-05-11_bom_recetas.sql`](../../db/migrations/2026-05-11_bom_recetas.sql)

Copialo todo y pegalo en la query en blanco.

### 3.2 Ejecutar

1. Pegá todo el SQL
2. Click en **Run** verde (o `Ctrl+Enter`)
3. Esperá unos segundos

### ✅ Resultado esperado

```
Success. No rows returned.
```

> ⚠️ Si ves error tipo *"relation 'empresas' does not exist"*, estás en el proyecto Supabase equivocado. Verificá que sea ERP WEB.

---

## 4. Verificar que las tablas se crearon

### 4.1 Verificar tablas nuevas

```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN ('recetas', 'receta_items', 'lotes_produccion')
ORDER BY table_name;
```

**✅ Esperado: 3 filas** — `lotes_produccion`, `receta_items`, `recetas`

### 4.2 Verificar columnas nuevas en inventario

```sql
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'inventario'
  AND column_name IN ('es_producto_terminado', 'precio_venta', 'notas_produccion')
ORDER BY column_name;
```

**✅ Esperado: 3 filas** — `es_producto_terminado` (boolean), `notas_produccion` (text), `precio_venta` (numeric)

### 4.3 Verificar las 2 vistas

```sql
SELECT viewname
FROM pg_views
WHERE schemaname = 'public'
  AND viewname IN ('v_recetas_detalle', 'v_capacidad_produccion')
ORDER BY viewname;
```

**✅ Esperado: 2 filas** — `v_capacidad_produccion`, `v_recetas_detalle`

---

## 5. Configurar Row Level Security

> ⚠️ **OPCIONAL** — Solo si el resto del sistema usa RLS.

### 5.1 Verificar si el resto del sistema usa RLS

```sql
SELECT tablename, rowsecurity
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename IN ('comprobantes', 'clientes', 'proveedores', 'inventario')
ORDER BY tablename;
```

Si todas dicen `false`, saltá al paso 6.

### 5.2 Aplicar RLS a las tablas nuevas

```sql
-- Activar RLS
ALTER TABLE recetas          ENABLE ROW LEVEL SECURITY;
ALTER TABLE receta_items     ENABLE ROW LEVEL SECURITY;
ALTER TABLE lotes_produccion ENABLE ROW LEVEL SECURITY;

-- Política: usuarios autenticados pueden hacer todo sobre las recetas de SU empresa
CREATE POLICY recetas_tenant_isolation ON recetas
  USING (empresa_id::text = auth.jwt() ->> 'empresa_id');

CREATE POLICY receta_items_via_receta ON receta_items
  USING (
    EXISTS (
      SELECT 1 FROM recetas r
      WHERE r.id = receta_items.receta_id
        AND r.empresa_id::text = auth.jwt() ->> 'empresa_id'
    )
  );

CREATE POLICY lotes_tenant_isolation ON lotes_produccion
  USING (empresa_id::text = auth.jwt() ->> 'empresa_id');
```

> ⚠️ Si tu backend usa el `service_role key`, las políticas RLS son bypass por el service role — no afectan el funcionamiento. Las RLS solo aplican si te conectás con la `anon key`.

---

## 6. Cargar datos iniciales

> 💡 **OPCIONAL** — Marcar algunos productos existentes como "terminados" para empezar a usar el BOM.

### 6.1 Marcar productos terminados

```sql
-- Marcar como producto terminado todo lo que se llama "Bronceador" o "Crema"
UPDATE inventario
SET es_producto_terminado = TRUE
WHERE (
    descripcion ILIKE '%bronceador%'
    OR descripcion ILIKE '%crema%'
    OR descripcion ILIKE '%locion%'
    OR descripcion ILIKE '%loción%'
)
AND activo = TRUE;

-- Ver qué quedó
SELECT id, codigo, descripcion, precio_venta
FROM inventario
WHERE es_producto_terminado = TRUE
  AND activo = TRUE
ORDER BY descripcion;
```

### 6.2 Cargar precio de venta sugerido

```sql
-- Ejemplo: bronceador 150ml a 18.000 Gs
UPDATE inventario
SET precio_venta = 18000
WHERE descripcion ILIKE '%bronceador%150%';

-- Ver precios y margen
SELECT codigo, descripcion, costo_unitario, precio_venta,
       ROUND(precio_venta - costo_unitario, 0) AS margen_bruto
FROM inventario
WHERE es_producto_terminado = TRUE
  AND precio_venta IS NOT NULL;
```

---

## 7. Troubleshooting

### ❌ "relation 'empresas' does not exist"

Estás en el proyecto Supabase equivocado. Verificá que sea **ERP WEB**.

### ❌ "extension uuid-ossp does not exist"

```sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
```

Y volvé a aplicar la migración del BOM.

### ❌ "permission denied for table inventario"

Tu cuenta no tiene rol `owner` ni `developer`. Pedile al dueño del proyecto.

### ❌ Empezar de cero

```sql
-- ⚠ Esto borra TODO el BOM. Solo si querés empezar de cero.
DROP VIEW  IF EXISTS v_capacidad_produccion CASCADE;
DROP VIEW  IF EXISTS v_recetas_detalle      CASCADE;
DROP TABLE IF EXISTS lotes_produccion       CASCADE;
DROP TABLE IF EXISTS receta_items           CASCADE;
DROP TABLE IF EXISTS recetas                CASCADE;
ALTER TABLE inventario DROP COLUMN IF EXISTS es_producto_terminado;
ALTER TABLE inventario DROP COLUMN IF EXISTS precio_venta;
ALTER TABLE inventario DROP COLUMN IF EXISTS notas_produccion;
```

---

## ✅ Cuando termines

Si todos los pasos pasaron OK, vas a poder:

- Entrar al ERP en producción
- Ir a **Producción → Recetas** sin error
- Crear una receta nueva (ej: Bronceador FPS 15 con sus ingredientes)
- Ver el costo unitario y margen calculado automáticamente
- Ir a **Producción → Capacidad** para ver cuántas unidades podés producir

---

## 🤖 Prompts listos para Claude

Si vas a darle esta tarea a un asistente IA con acceso a Supabase:

```
Hola Claude. Necesito que ejecutes una migración SQL en el proyecto Supabase
"ERP WEB" (project_id: skwxkmmnvdojagdruthi).

Por favor:
1. Aplicá el SQL del archivo db/migrations/2026-05-11_bom_recetas.sql
2. Verificá con estas queries:
   - SELECT table_name FROM information_schema.tables WHERE table_schema='public'
     AND table_name IN ('recetas','receta_items','lotes_produccion');
   - SELECT column_name FROM information_schema.columns WHERE table_schema='public'
     AND table_name='inventario' AND column_name IN ('es_producto_terminado','precio_venta','notas_produccion');
   - SELECT viewname FROM pg_views WHERE schemaname='public'
     AND viewname IN ('v_recetas_detalle','v_capacidad_produccion');
3. Reportame cuántas filas devolvió cada verificación
```

---

📖 **Más documentación:** [SDD técnico](SDD.md) · [Guía de usuario](GUIA_USUARIO.md) · [Análisis de mejoras](ANALISIS_MEJORAS.md)
