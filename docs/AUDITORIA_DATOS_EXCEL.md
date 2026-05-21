# Auditoria de Datos Excel - ERP_Web

Fecha: 2026-05-05  
Autor: Codex

## Archivos revisados

Los scripts de migracion leen los Excel fuente desde la carpeta externa:

`C:\Users\gfcar\Desktop\IA\Empresa 1\Datos Generales de la empresa`

Archivos:

- `CLIENTES - ESTADO DE CUENTAS 2023-2024 (1).xlsx`
- `CLIENTES - ESTADO DE CUENTAS 2025 (Autoguardado) (1).xlsx`
- `COSTOS MP - INSUMOS - PROD TERMINADOS (1).xlsx`

## Conteos extraidos

| Area | Resultado |
|---|---:|
| Clientes detectados | 57 |
| Facturas/lineas de venta detectadas | 279 |
| Facturas con fecha valida importable | 244 |
| Facturas sin fecha o con fecha invalida | 35 |
| Proveedores detectados | 20 |
| Items inventario consolidados | 114 |
| Materias primas | 68 |
| Insumos | 34 |
| Productos terminados | 12 |
| Clientes con matriz producto-cliente | 7 |

## Hallazgos importantes

### 1. Matriz productos x cliente inflaba cantidades

En `scripts/migrar_excels.py`, la hoja `VENTAS 2025-2026` heredaba el ultimo cliente hacia columnas de totales/costos. Eso asignaba columnas como `VENTAS`, `COSTO UN` y `COSTO PRODUCCION` al ultimo cliente visible.

Impacto antes del arreglo:

| Cliente | Cantidad anterior | Cantidad corregida |
|---|---:|---:|
| CADENA REAL | 31.209.405 | 102 |
| COSCOM | 438 | 188 |

Estado: corregido. Ahora `migrar_excels.py` usa el mismo criterio robusto que `enriquecer_items_facturas.py`.

### 2. Inventario tenia codigo duplicado

El codigo `100012` aparecia dos veces como `DMDM HIDANTOINA`:

- Fila con cantidad `3.4`
- Fila con cantidad `0.8`

Antes, la migracion cargaba la primera y saltaba la segunda por lookup de codigo.

Estado: corregido. Ahora el extractor consolida ambas filas en una sola con cantidad `4.2`.

### 3. Hay facturas sin fecha o con fecha no importable

Se detectaron 35 lineas de venta sin fecha valida. Ejemplos:

- `FARMA S.A.` con montos agregados altos sin fecha en `VENTAS 2025-2026`
- `MODENA COMERCIAL S.A.` con varias lineas sin fecha en `VENTAS 2024-2025`
- Una linea con fecha textual `PRODUCTOS`
- Duplicados pequenos para `AUGUSTINA ACOSTA` y `RITA ALGARIN - TITA` sin fecha

Estado: no se importan como comprobantes porque `upsert_facturas()` exige fecha ISO valida. Se recomienda que el PM revise si esas lineas son totales/resumen o ventas reales pendientes de fecha.

### 4. Hay numeros de factura duplicados en origen

Duplicados detectados:

- `001-001-0000128`: dos veces, ambas sin fecha, `BEAUTY CARE S.A. - VITA COSMETICOS`, monto `22.000`
- `001-002-0000130`: aparece en `Hoja1` y `Hoja2`, mismo cliente `FARMA S.A. PUNTOFARMA (distribuidora nemby)`, misma fecha `2023-10-03`, mismo monto `51.030.000`

Estado: la migracion es idempotente y deduplica por numero de comprobante, por lo que no deberia duplicar en BD. Igual queda anotado para limpieza del Excel fuente.

### 5. Clientes con variantes de nombre

Hay variantes que pueden ser intencionales por sucursal, pero fragmentan la vista por cliente:

- `A.B.L. S.A.` / `ABL S.A.`
- `ALIMENTOS ESPECIALES S.A`, `ALIMENTOS ESPECIALES S.A.`, variantes por sucursal
- `CADENA REAL S.A`, `CADENA REAL S.A.`, variantes por sucursal
- `CAFSA S.A`, `CAFSA S.A.`, variantes por sucursal
- `FARMA S.A.` / `FARMA S.A.- PUNTOFARMA`

Estado: no se fusionaron automaticamente para evitar perder informacion de sucursales. El script de enriquecimiento ya tiene un mapeo de grupos para repartir productos, pero la base mantiene los clientes separados.

## Cambios aplicados en scripts

- `scripts/migrar_excels.py`
  - Agrega `--excel-dir` y variable `ERP_EXCEL_DIR`.
  - Valida que existan los 3 Excel fuente antes de migrar.
  - Consolida items de inventario repetidos por codigo.
  - Actualiza inventario existente al re-ejecutar, en vez de saltarlo.
  - Corrige matriz producto-cliente para excluir columnas de totales/costos.

- `scripts/enriquecer_items_facturas.py`
  - Agrega `--excel-dir` y variable `ERP_EXCEL_DIR`.
  - Valida que exista el Excel de costos antes de enriquecer.

## Verificacion ejecutada

- `python -m compileall scripts backend`
- Extractor de Excel directo:
  - Matriz corregida coincide entre scripts.
  - `CADENA REAL` queda en `102`.
  - `COSCOM` queda en `188`.
  - Inventario queda sin codigos duplicados.
  - Codigo `100012` queda consolidado en cantidad `4.2`.

## Recomendacion PM

Antes de una migracion definitiva, revisar manualmente las 35 lineas sin fecha valida. Si son totales/resumen, dejarlas fuera es correcto. Si son ventas reales, completar fecha y numero en el Excel o preparar una tabla manual de correccion.
