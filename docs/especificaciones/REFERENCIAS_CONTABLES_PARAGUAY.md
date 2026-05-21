# 📚 REFERENCIAS CONTABLES Y FORMATOS (PARAGUAY)

Este documento centraliza las fuentes de verdad y ejemplos prácticos para la implementación de los módulos contables (Fases H, I, J).

## 1. Fuentes de Referencia Internas (Legado)

El sistema anterior (**Milano Software**) está disponible en la carpeta `/SOFTWARE CONTABLE/MILANO SOFTWARE/`. Estos archivos muestran cómo se ha llevado la contabilidad de la empresa hasta ahora:

- **Libro Diario:** Ver `librodiarioespecial.TXT`. Muestra la estructura de asientos (Asiento, Fecha, Cuenta, Debe, Haber, Concepto).
- **Libro Mayor:** Ver `libromayor.TXT` y `libromayorubricado.TXT`.
- **Libro Ventas:** Ver `libroventas -SARA JOSEFINA-2025-1.txt`. Muestra RUC, Razón Social, Número de Comprobante, Fecha, y desgloses de impuestos.
- **Plan de Cuentas:** La tabla `tl_pc_red.dbf` contiene el plan de cuentas antiguo. Se puede usar como referencia para la jerarquía (ej: `1.01.01.XXX`).

## 2. Normativa Fiscal Vigente (Paraguay - SET/DNIT)

La implementación de reportes debe alinearse con la **Resolución General N° 90/21 (RG 90)** de la SET (ahora DNIT), que regula el registro electrónico de comprobantes.

### Requerimientos Clave de la RG 90:
- **Libro de Ventas:** Debe contener RUC comprador, Razón Social, Tipo de Com comprobante (Factura, NC, ND), Nro. Comprobante (formato XXX-XXX-XXXXXXX), Gravadas 10%, Gravadas 5%, Exentas y el IVA liquidado.
- **Libro de Compras:** Similar al de ventas, incluyendo la distinción de crédito fiscal (IVA gasto vs IVA inversión).
- **Tipos de Comprobantes:**
  - 1: Factura
  - 2: Nota de Débito
  - 3: Nota de Crédito
  - 4: Comprobante de Retención
  - 5: Nota de Remisión

## 3. Guía para Claude (Desarrollador)

Para saber "qué código usar" o "qué formato seguir":

1.  **Estructura de Asientos:** Seguir el modelo de `asientos_contables` definido en el `AUDITORIA_SISTEMA_CONTABLE.md`.
2.  **Lógica de IVA:**
    - Paraguay usa **IVA incluido** en los comprobantes físicos.
    - Base 10% = Total / 1.1
    - IVA 10% = Base 10% * 0.1 (o Total / 11)
    - Base 5% = Total / 1.05
    - IVA 5% = Base 5% * 0.05 (o Total / 21)
3.  **Plan de Cuentas:** Utilizar la estructura de 5 niveles (Activo.Corriente.Disponibilidades.Caja.Caja Moneda Nacional). Ver `db/esquema_bd.sql` para el seed inicial.

## 4. Sitios Web de Consulta Obligatoria

- **DNIT (ex SET) - RG 90:** [https://www.set.gov.py/](https://www.set.gov.py/) (Sección Registro de Comprobantes).
- **Formatos Excel Importación Marangatu:** Buscar "Planillas de importación RG 90" para ver las columnas exactas que requiere el fisco.

---

Este documento debe actualizarse si cambian las normativas o si se encuentran nuevos formatos de referencia.
