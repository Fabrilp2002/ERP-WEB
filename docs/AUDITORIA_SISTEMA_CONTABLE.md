# 🔍 AUDITORÍA COMPLETA — Sistema Contable ERP Universal v4.0

> **Fecha:** 2026-04-24  
> **Alcance:** Revisión exhaustiva de funcionalidades contables existentes vs. requeridas  
> **Destino:** Claude (Desarrollador) — leer ANTES de implementar cualquier fase nueva

---

## Resumen Ejecutivo

El ERP Universal tiene una **base operativa sólida** para registro de comprobantes, pagos, cuentas corrientes y exportación. Sin embargo, **carece de funcionalidades contables fundamentales** que lo separan de un sistema contable real. El hallazgo más crítico es que la tabla `plan_cuentas` existe en el esquema SQL pero **no tiene absolutamente ningún uso en el código backend ni frontend**.

> **HALLAZGO PRINCIPAL:** El sistema NO tiene contabilidad por partida doble. Sin libro diario, sin asientos contables, sin balance general ni estado de resultados. El plan de cuentas es una tabla muerta.

---

## 1. HALLAZGOS CRÍTICOS (Severidad: 🔴 BLOQUEANTE) — **[RESUELTO ✅ Fase H+I]**

### 1.1 Plan de Cuentas — Tabla muerta **[RESUELTO ✅ Fase H]**

| Aspecto | Estado |
|---------|--------|
| Tabla `plan_cuentas` en SQL | ✅ Existe con estructura jerárquica correcta |
| Seed con 17 cuentas base | ✅ Insertadas en esquema_bd.sql |
| Router backend `/plan-cuentas` | ✅ **Implementado en Fase H** |
| CRUD de cuentas contables | ✅ **Implementado en Fase H** |
| Página frontend de plan de cuentas | ✅ **Implementado en Fase H** |
| Uso en routers/servicios | ✅ **Asientos automáticos en comprobantes y pagos** |

### 1.2 Libro Diario — Inexistente **[RESUELTO ✅ Fase H]**

Implementado en Fase H:
- **Asientos contables** con partida doble (débito + crédito balanceado)
- Registro automático al crear comprobantes y pagos
- Consulta de movimientos por cuenta contable
- Mayorización en libro mayor

### 1.3 Estados Financieros — Inexistentes **[RESUELTO ✅ Fase H]**

Implementado en Fase H:
- **Balance General** (Activo = Pasivo + Patrimonio)
- **Estado de Resultados** (Ingresos - Egresos = Utilidad)
- **Balance de Comprobación** (sumas y saldos)

### 1.4 Cuentas Bancarias — Schema sin código **[RESUELTO ✅ Fase I]**

| Aspecto | Estado |
|---------|--------|
| Tabla `cuentas_banco` en SQL | ✅ Existe |
| Tabla `movimientos_banco` en SQL | ✅ Existe |
| FK `pagos.cuenta_banco_id` | ✅ Existe |
| Router CRUD `/cuentas-banco` | ✅ **Implementado en Fase I** |
| Router `/movimientos-banco` | ✅ **Implementado en Fase I** |
| UI de gestión bancaria | ✅ **Implementado en Fase I** |

---

## 2. HALLAZGOS ALTOS (Severidad: 🟠 IMPORTANTE) — **[RESUELTO ✅ Fase I+J]**

### 2.1 Reportes Fiscales Paraguayos — Inexistentes **[RESUELTO ✅ Fase I]**

Implementado en Fase I:
- **Libro Compras IVA** (detalle de IVA 5% y 10% de compras)
- **Libro Ventas IVA** (detalle de IVA de ventas)
- **Resumen IVA mensual** (IVA Crédito vs IVA Débito = IVA a pagar/recuperar) — formato RG90

### 2.2 Antigüedad de Saldos (Aging) **[RESUELTO ✅ Fase I]**

Implementado en Fase I — reporte de antigüedad de cuentas por cobrar/pagar:
- Corriente (0-30 días), 31-60 días, 61-90 días, Más de 90 días

### 2.3 Notas de Crédito/Débito — Sin flujo contable **[RESUELTO ✅ Fase I]**

Implementado en Fase I:
- NC vinculada a factura origen vía `comprobante_origen_id`
- Al confirmar NC se reduce el saldo del comprobante origen

### 2.4 Retenciones — Inexistentes **[RESUELTO ✅ Fase J]**

Implementado en Fase J:
- Retenciones de IVA y Renta
- CRUD completo + vinculación a comprobantes
- UI de registro de retenciones

---

## 3. HALLAZGOS MEDIOS (Severidad: 🟡 DESEABLE)

### 3.1 Presupuestos **[RESUELTO ✅ Fase J]**
- Módulo de presupuesto por periodo implementado en Fase J
- Comparativo presupuesto vs ejecución real con semáforo visual

### 3.2 Centros de Costo
- No hay segmentación de gastos por departamento/proyecto (pendiente, baja prioridad)

### 3.3 Multi-moneda real
- El campo `moneda_principal` en empresas es solo label ("PYG")
- No hay tabla de tipos de cambio (pendiente — Fase futura)

### 3.4 Cierre Contable **[RESUELTO ✅ Fase J]**
- Proceso de cierre mensual/anual implementado en Fase J
- Bloqueo de periodos cerrados activo
- Panel de cierre contable en el sidebar

---

## 4. HALLAZGOS DE ARQUITECTURA (Severidad: 🔵 TÉCNICO)

### 4.1 Inventario: `ajustar_cantidad` usa `float` **[RESUELTO ✅ 2026-04-24]**

```python
# Línea 68 en inventario.py — ANTES:
cantidad_nueva: float = Query(...)  # ❌ Viola regla "nunca float"
# DESPUÉS:
cantidad_nueva: Decimal = Query(...)  # ✅ Correcto
```

Corregido en `backend/routers/inventario.py` — también se agregó `from decimal import Decimal`.

### 4.2 Vista `v_saldo_clientes` con posible doble-conteo **[RESUELTO ✅ 2026-04-24]**

Corregido en `db/esquema_bd.sql` y migración `db/migrations/2026-04-24_fix_vistas_saldo.sql`.
Ambas vistas usan ahora subquery pre-agregada para `pagos`, eliminando la multiplicación 1:N.

---

## 5. LO QUE FUNCIONA BIEN ✅

| Funcionalidad | Evaluación |
|---------------|------------|
| CRUD Comprobantes con detalle | ✅ Completo y robusto |
| Pagos con actualización de saldo | ✅ Con validaciones correctas |
| Anulación soft con motivo | ✅ Bien diseñado |
| Cuentas corrientes (vistas SQL) | ✅ Funcional |
| Dashboard con KPIs | ✅ 7 endpoints completos |
| OCR con Gemini Vision | ✅ Sofisticado |
| Chatbot con 19 herramientas | ✅ Muy completo |
| Exportación Excel profesional | ✅ 4 reportes con estilos |
| Auditoría JSONB no-bloqueante | ✅ Bien implementada |
| Condición contado/crédito | ✅ Con medio de pago diferenciado |
| Adjuntos de comprobantes/pagos | ✅ Upload + delete + visor |
| Multi-tenant con empresa_id | ✅ Consistente en todos los endpoints |

---

## 6. PROPUESTAS DE IMPLEMENTACIÓN

Organizadas en 3 fases prioritarias:

### FASE H — Contabilidad Real (CRÍTICA)

> **IMPORTANTE:** Esta es la fase más importante. Sin esto, el sistema NO es contable, es solo un registrador de facturas.

#### H.1 — CRUD Plan de Cuentas
- **Backend:** Crear `backend/routers/plan_cuentas.py`
  - `GET /plan-cuentas` — listar cuentas jerárquicas (árbol)
  - `POST /plan-cuentas` — crear cuenta (validar código único, padre válido)
  - `PATCH /plan-cuentas/{id}` — editar nombre/estado
  - `DELETE /plan-cuentas/{id}` — desactivar (solo si es hoja sin movimientos)
- **Frontend:** Crear `frontend/src/app/(app)/contabilidad/plan-cuentas/page.tsx`
  - Vista de árbol expandible/colapsable
  - Crear/editar/desactivar cuentas
- **Chatbot:** Agregar tool `consultar_plan_cuentas`

#### H.2 — Libro Diario (Asientos Contables)
- **Migración SQL:** Crear tabla `asientos_contables` + `detalle_asientos`

```sql
CREATE TABLE asientos_contables (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    empresa_id      UUID NOT NULL REFERENCES empresas(id),
    numero          SERIAL,  -- numeración secuencial por empresa
    fecha           DATE NOT NULL,
    concepto        VARCHAR(500) NOT NULL,
    comprobante_id  UUID REFERENCES comprobantes(id),  -- nullable: asientos manuales
    pago_id         UUID REFERENCES pagos(id),          -- nullable
    tipo            VARCHAR(20) NOT NULL DEFAULT 'automatico'
                    CHECK (tipo IN ('automatico','manual','ajuste','cierre')),
    usuario_id      UUID REFERENCES usuarios(id),
    fecha_creacion  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE detalle_asientos (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    empresa_id      UUID NOT NULL REFERENCES empresas(id),
    asiento_id      UUID NOT NULL REFERENCES asientos_contables(id) ON DELETE CASCADE,
    cuenta_id       UUID NOT NULL REFERENCES plan_cuentas(id),
    debe            DECIMAL(15,2) NOT NULL DEFAULT 0,
    haber           DECIMAL(15,2) NOT NULL DEFAULT 0,
    CHECK (debe >= 0 AND haber >= 0),
    CHECK (debe > 0 OR haber > 0)  -- al menos uno debe tener valor
);
```

- **Backend:** Crear `backend/routers/asientos.py` + `backend/services/contabilidad.py`
  - Generación automática de asientos al crear comprobantes
  - Generación automática al registrar pagos
  - CRUD de asientos manuales (solo admin)
  - Validación partida doble: `SUM(debe) = SUM(haber)` por asiento
- **Frontend:** `frontend/src/app/(app)/contabilidad/libro-diario/page.tsx`

#### H.3 — Libro Mayor
- **Backend:** Endpoint `GET /contabilidad/mayor/{cuenta_id}`
  - Todos los movimientos de una cuenta con saldo acumulado
- **Frontend:** `frontend/src/app/(app)/contabilidad/libro-mayor/page.tsx`

#### H.4 — Estados Financieros
- **Backend:** 
  - `GET /contabilidad/balance-general?fecha=YYYY-MM-DD`
  - `GET /contabilidad/estado-resultados?desde=YYYY-MM-DD&hasta=YYYY-MM-DD`
  - `GET /contabilidad/balance-comprobacion?mes=YYYY-MM`
- **Frontend:** `frontend/src/app/(app)/contabilidad/reportes/page.tsx`
  - Selector de periodo
  - Tablas con formato profesional
  - Exportación a Excel y PDF

---

### FASE I — Gestión Bancaria y Fiscal

#### I.1 — CRUD Cuentas Bancarias
- **Backend:** Crear `backend/routers/cuentas_banco.py`
  - `GET /cuentas-banco` — listar cuentas
  - `POST /cuentas-banco` — crear cuenta
  - `PATCH /cuentas-banco/{id}` — editar
  - Registrar movimientos automáticos al registrar pagos con `cuenta_banco_id`
- **Frontend:** `frontend/src/app/(app)/bancos/page.tsx`
  - Lista de cuentas con saldos
  - Detalle de movimientos por cuenta
  - Registro de movimientos manuales (depósitos, retiros, comisiones)

#### I.2 — Reportes IVA
- **Backend:**
  - `GET /reportes/libro-compras-iva?mes=YYYY-MM` — IVA crédito desglosado 5%/10%
  - `GET /reportes/libro-ventas-iva?mes=YYYY-MM` — IVA débito desglosado
  - `GET /reportes/liquidacion-iva?mes=YYYY-MM` — Crédito - Débito = saldo
- **Frontend:** `frontend/src/app/(app)/reportes/iva/page.tsx`
- **Excel:** Agregar `generar_excel_libro_iva()` en `services/export.py`

#### I.3 — Antigüedad de Saldos (Aging Report)
- **Backend:** `GET /reportes/antiguedad-saldos?tipo=clientes|proveedores`
  - Agrupación: Corriente | 31-60 | 61-90 | 90+
- **Frontend:** Tabla color-coded con alertas
- **Dashboard:** Agregar widget de aging al dashboard

#### I.4 — Notas de Crédito vinculadas
- **Migración:** Agregar `comprobante_origen_id UUID REFERENCES comprobantes(id)` a tabla `comprobantes`
- **Backend:** Lógica para que al confirmar una NC se reduzca el saldo del comprobante origen
- **Frontend:** Selector de factura origen al crear NC

---

### FASE J — Mejoras Avanzadas

#### J.1 — Retenciones
- **Migración SQL:** Tabla `retenciones`
- **Backend:** CRUD + vinculación a comprobantes
- **Frontend:** Registro de retenciones al registrar pagos

#### J.2 — Multi-moneda
- **Migración:** Campo `moneda` en comprobantes + tabla `tipos_cambio`
- **Backend:** Conversión automática al tipo de cambio del día
- **Frontend:** Selector de moneda en comprobantes

#### J.3 — Presupuestos
- **Tablas:** `presupuestos` + `detalle_presupuesto`
- **Backend:** CRUD + comparación vs real
- **Frontend:** Vista presupuesto vs ejecución

#### J.4 — Cierre Contable
- **Backend:** Proceso de cierre que bloquea modificaciones en periodo cerrado
- **Frontend:** Panel de cierre mensual/anual

---

## 7. BUGS MENORES A CORREGIR — **[TODOS RESUELTOS ✅ 2026-04-24]**

| # | Archivo | Línea | Descripción | Fix | Estado |
|---|---------|-------|-------------|-----|--------|
| 1 | `inventario.py` | 68 | `float` en `cantidad_nueva` | Cambiar a `Decimal` | **[RESUELTO ✅]** |
| 2 | `esquema_bd.sql` | 273-297 | Vista `v_saldo_clientes` posible doble-conteo | Subquery pre-agregada para pagos | **[RESUELTO ✅]** |
| 3 | `pagos.py` | 264 | `eliminar_pago` no revertía asiento contable | `revertir_asiento_pago()` antes del DELETE | **[RESUELTO ✅]** |

---

## 8. PRIORIZACIÓN

```
URGENCIA MÁXIMA (Fase H — sin esto no es sistema contable):
  H.1 Plan de Cuentas CRUD          ~2 horas
  H.2 Libro Diario + Asientos auto  ~4 horas  
  H.3 Libro Mayor                   ~2 horas
  H.4 Estados Financieros           ~3 horas

URGENCIA ALTA (Fase I — requerido para producción):
  I.1 Cuentas Bancarias CRUD        ~2 horas
  I.2 Reportes IVA                  ~3 horas
  I.3 Aging Report                  ~1 hora
  I.4 Notas de Crédito vinculadas   ~2 horas

URGENCIA MEDIA (Fase J — mejora competitiva):
  J.1 Retenciones                   ~2 horas
  J.2 Multi-moneda                  ~3 horas
  J.3 Presupuestos                  ~3 horas
  J.4 Cierre Contable               ~2 horas
```

---

## 9. CONVENCIONES A MANTENER EN TODA IMPLEMENTACIÓN

1. **DECIMAL(15,2)** en todos los montos — nunca float
2. **UUID** en todas las PKs
3. **empresa_id** en toda tabla nueva
4. **Auditoría** en toda operación de escritura (usar `services/audit.py`)
5. **IVA paraguayo**: solo 0%, 5%, 10%
6. Los asientos contables deben cumplir **partida doble estricta**: `SUM(debe) = SUM(haber)`
7. Todo nuevo router → registrar en `main.py`
8. Todo nuevo endpoint → documentar en `docs/api/API_REFERENCE.md`
9. Todo nuevo módulo frontend → agregar entrada en `Sidebar.tsx`
10. Las nuevas herramientas del chatbot deben agregarse a `services/chatbot.py`

---

> **Próximo paso:** Aprobación del PM (gfcar) → Ejecutar Fase H
