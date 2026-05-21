# Plan — Navegación consolidada (menos items, todo agrupado)

> **Versión:** v1.0 · 2026-05-13
> **Autor:** Claude · Aprobación pendiente: PM
> **Estado:** 📋 Planificado — sin implementar todavía
> **Tiempo estimado:** 4–6 h · 0 cambios destructivos · 0 funcionalidades removidas

---

## 1. ¿Qué problema resuelve?

Hoy la barra superior tiene **10 items** + 5 en el menú de usuario = 15 destinos. El usuario tiene que pensar dónde encontrar cada cosa, y cosas que se usan juntas están separadas:

- "Facturas" y "Foto" (OCR para cargar facturas) son items distintos en la barra, pero hacen lo mismo: cargar facturas.
- "IVA" está separado de "Facturas", aunque el IVA se calcula a partir de las facturas.
- "Clientes", "Proveedores" y "Cuentas" están dispersos, aunque los tres son "personas con las que hago negocio".

Esto produce dos efectos:
1. **Fricción mental** — el operador tiene que recordar en qué ítem entrar.
2. **Items que se ocultan** en mobile cuando no caben todos en la barra.

---

## 2. Inventario actual (lo que tenemos hoy)

### Barra superior (10 items, mismo nivel)

| Item | URL | ¿Qué hace? |
|---|---|---|
| Inicio | `/dashboard` | KPIs y resumen |
| Facturas | `/comprobantes` | Listado y CRUD de comprobantes |
| Foto | `/ocr` | Cargar factura desde imagen/PDF |
| Cuentas | `/cuentas` | Estado de cuenta por contraparte |
| Cobros y pagos | `/movimientos` | Registrar y ver pagos |
| IVA | `/reportes/iva` | Resumen del IVA del mes |
| Clientes | `/clientes` | CRUD clientes |
| Proveedores | `/proveedores` | CRUD proveedores |
| Inventario | `/inventario` | Stock |
| Asistente | `/asistente` | Chatbot IA |

### Globo de usuario (5 items)

| Item | URL | ¿Qué hace? |
|---|---|---|
| Mi seguridad | `/perfil/seguridad` | Cambiar pass, ver eventos |
| Actividad | `/actividad` | Auditoría |
| Mi empresa (admin) | `/admin/empresa` | Datos de la empresa |
| Usuarios (admin) | `/admin/usuarios` | CRUD usuarios |
| Cerrar sesión | — | Logout |

---

## 3. Propuesta: 6 grupos lógicos en la barra

| # | Grupo | Comportamiento | Contiene |
|---|---|---|---|
| 1 | **🏠 Inicio** | Click directo → `/dashboard` | Sin cambio |
| 2 | **📄 Facturas** ↓ | Dropdown al hover/click | **Ver facturas** · **Cargar con foto** · **IVA del mes** |
| 3 | **💸 Cobros y pagos** | Click directo → `/movimientos` | Ya tiene botones "Cargar cobro" y "Cargar pago" adentro — no necesita submenú |
| 4 | **👥 Contactos** ↓ | Dropdown | **Clientes** · **Proveedores** · **Cuentas corrientes** |
| 5 | **📦 Inventario** | Click directo → `/inventario` | (Futuro: submenú con Recetas y Producción cuando se activen) |
| 6 | **🤖 Asistente** | Click directo → `/asistente` | Atajo Ctrl+/ ya disponible |

**Globo de usuario:** sin cambios. Sigue conteniendo: Mi seguridad, Actividad, Mi empresa, Usuarios, Cerrar sesión.

**Resultado:** 10 items → 6 grupos. **Cero funcionalidades eliminadas** — solo se reagrupan los caminos para llegar a ellas.

---

## 4. Detalle de cada dropdown

### Dropdown "Facturas"

```
┌─────────────────────────────────────┐
│ 📄 Facturas                       ↓ │
└─────────────────────────────────────┘
        │  click o hover
        ▼
┌─────────────────────────────────────────┐
│ 📋 Ver facturas                         │
│    Listado de ventas y compras          │
│                                         │
│ 📸 Cargar con foto                      │
│    Sacá una foto o subí PDF             │
│                                         │
│ 🧮 IVA del mes                          │
│    Cuánto vas a pagar/recibir este mes  │
└─────────────────────────────────────────┘
```

Cada opción tiene su nombre simple + una línea explicativa abajo (igual al patrón que ya usamos en el dashboard "¿Qué querés hacer?").

### Dropdown "Contactos"

```
┌─────────────────────────────────────┐
│ 👥 Contactos                      ↓ │
└─────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────┐
│ 🛒 Clientes                             │
│    A quiénes les vendés                 │
│                                         │
│ 🏭 Proveedores                          │
│    A quiénes les comprás                │
│                                         │
│ 📋 Cuentas corrientes                   │
│    Quién te debe y a quién le debés     │
└─────────────────────────────────────────┘
```

---

## 5. Comportamiento en mobile

### Hoy

En pantallas < 768px, la barra superior se oculta y aparece BottomNav. Algunos items quedan accesibles solo desde el menú de usuario.

### Propuesta

**BottomNav (mobile)** queda con los 4 más usados:
- 🏠 Inicio
- 📄 Facturas
- 💸 Cobros y pagos
- ➕ **Más**

**"Más" abre una sheet** que ocupa la parte inferior de la pantalla con todos los grupos:

```
┌─────────────────────────────────────────┐
│ Más                                  ✕  │
├─────────────────────────────────────────┤
│ 📄 FACTURAS                             │
│   📋 Ver facturas                       │
│   📸 Cargar con foto                    │
│   🧮 IVA del mes                        │
│                                         │
│ 👥 CONTACTOS                            │
│   🛒 Clientes                           │
│   🏭 Proveedores                        │
│   📋 Cuentas corrientes                 │
│                                         │
│ 📦 Inventario                           │
│ 🤖 Asistente                            │
└─────────────────────────────────────────┘
```

Misma agrupación que en desktop — el usuario aprende una sola vez dónde está cada cosa.

---

## 6. Tabla de equivalencias (sin pérdida)

Para que el PM pueda verificar que **ninguna funcionalidad desaparece**:

| Antes (10 items + 5 menú) | Después (6 grupos + 5 menú) |
|---|---|
| Inicio | Inicio |
| Facturas | Facturas → Ver facturas |
| Foto | Facturas → Cargar con foto |
| IVA | Facturas → IVA del mes |
| Cuentas | Contactos → Cuentas corrientes |
| Cobros y pagos | Cobros y pagos |
| Clientes | Contactos → Clientes |
| Proveedores | Contactos → Proveedores |
| Inventario | Inventario |
| Asistente | Asistente |
| Mi seguridad | Globo de usuario → Mi seguridad |
| Actividad | Globo de usuario → Actividad |
| Mi empresa | Globo de usuario → Mi empresa |
| Usuarios | Globo de usuario → Usuarios |
| Cerrar sesión | Globo de usuario → Cerrar sesión |

**15 destinos antes → 15 destinos después.** Ninguno se borra; se reorganizan.

---

## 7. Beneficios concretos

| Beneficio | Cómo se nota |
|---|---|
| **Menos elementos visibles a la vez** | La barra superior pasa de 10 a 6 ítems — menos ruido visual |
| **Las acciones relacionadas están juntas** | Para cargar una factura nueva: abrís "Facturas" y elegís foto, manual o ver IVA — todo en el mismo menú |
| **Mobile más limpio** | BottomNav con solo 4 botones grandes + "Más" para el resto |
| **Aprendizaje más rápido** | Un usuario nuevo entiende la lógica: dinero (cobros/pagos), papel (facturas), gente (contactos), cosas (inventario) |
| **Espacio para crecer** | Si mañana se agrega "Notas de crédito" o "Presupuestos", caben dentro de Facturas sin volver a saturar la barra |

---

## 8. Reglas de UX para el dropdown

Para que no se sienta como "una pestaña más":

1. **Abre con hover en desktop** (tras 150ms para evitar disparos accidentales) **o tap en mobile/touch**.
2. **Click directo en el label del grupo** (ej "Facturas") va a la opción principal del grupo (`/comprobantes`). El dropdown sigue abriéndose si se hace hover.
3. **Cierra al click fuera, Escape o seleccionar opción.**
4. **No se anida.** Solo un nivel. Si algún día necesitamos sub-sub-categorías, se rediseña — pero hoy no.
5. **Cada opción tiene icono + nombre + descripción de 4-6 palabras.** Igual al patrón del dashboard.
6. **Se resalta el grupo activo** (no solo el item exacto). Si estás en `/ocr`, el grupo "Facturas" queda resaltado en la barra para que el usuario vea dónde está parado.

---

## 9. Frontend — archivos a tocar

| Archivo | Acción |
|---|---|
| `frontend/src/components/TopBar.tsx` | Refactor: cambiar el array `NAV` plano por estructura `NAV_GRUPOS` con grupos y subitems; renderizar dropdowns |
| `frontend/src/components/NavDropdown.tsx` (NUEVO) | Componente reutilizable del dropdown (hover + click + accesible con teclado) |
| `frontend/src/components/BottomNav.tsx` | Reducir a 4 botones + "Más"; "Más" abre `<MasSheet />` |
| `frontend/src/components/MasSheet.tsx` (NUEVO) | Bottom sheet de mobile con todos los grupos |

**Sin dependencias nuevas.** Todo es CSS + React state.

---

## 10. Accesibilidad

- Dropdowns navegables por teclado (Tab para entrar, ↑↓ para mover, Enter para seleccionar, Escape para cerrar)
- `aria-expanded` y `aria-haspopup` correctamente seteados
- Focus visible en cada opción
- En mobile, la sheet usa `role="dialog"` con focus trap
- Texto de cada opción ≥ 14px

---

## 11. Sub-fases de implementación

| Sub-fase | Contenido | Tiempo |
|---|---|---|
| **A.1** | Componente `NavDropdown.tsx` reutilizable con hover, click, teclado y `aria-*` | 1.5 h |
| **A.2** | Refactor de `TopBar.tsx` para usar grupos en vez de array plano | 1.5 h |
| **A.3** | Componente `MasSheet.tsx` para mobile | 1 h |
| **A.4** | Refactor `BottomNav.tsx` a 4 botones + "Más" | 0.5 h |
| **A.5** | Smoke test en Chrome, Firefox y mobile real; ajustes visuales | 1 h |

Total: **~5.5 h**. Una sola entrega — no tiene sentido fraccionar.

---

## 12. Verificación

- `npm run lint` y `npm run build` deben pasar.
- Probar manualmente: hover desktop, click desktop, tap mobile, sheet mobile, atajos de teclado.
- Confirmar que **cada uno de los 15 destinos sigue accesible** (tabla §6).
- Validar que el active state funciona: estar en `/ocr` resalta el grupo "Facturas" en la barra.
- Probar en pantallas: 320px (iPhone SE), 768px (tablet), 1280px (laptop) y 1920px (desktop grande).

---

## 13. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Usuarios acostumbrados se confunden buscando "Foto" | Mostrar tooltip "💡 Ahora está dentro de Facturas → Cargar con foto" durante 1 semana después del deploy (banner discreto, con botón "Entendido") |
| Hover delay molesto en touch screens | En touch, deshabilitar hover y usar solo tap |
| Click en label del grupo confunde si el usuario quería ver el dropdown | Hover ya abre el dropdown en desktop; el click es atajo a la opción principal |
| Búsqueda por URL directa (ej tipear `/ocr`) sigue funcionando | Las URLs no cambian — solo se reorganiza el menú |

---

## 14. Estado actual y siguiente paso

- ✅ Plan documentado
- ⏳ Pendiente aprobación del PM
- 🚀 Si aprueba: arrancar por A.1 (componente `NavDropdown` aislado) — testeable en isolation antes de integrar al TopBar real
