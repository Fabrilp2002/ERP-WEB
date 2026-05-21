<style>
    body {
        padding: 50px 70px !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        text-align: justify;
        line-height: 1.6;
        color: #333;
    }
    h1 {
        text-align: center;
        color: #1e3a8a;
        font-size: 2.2em;
        margin-bottom: 20px;
        border-bottom: 2px solid #1e3a8a;
        padding-bottom: 10px;
    }
    h2 {
        color: #2563eb;
        margin-top: 30px;
        text-align: center;
    }
    h3 {
        color: #1e40af;
        margin-top: 25px;
    }
    img {
        display: block;
        margin: 30px auto;
        max-width: 85% !important;
        border: 1px solid #ccc;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.1);
    }
    table {
        margin: 30px auto;
        width: 100%;
        border-collapse: collapse;
        font-size: 0.95em;
    }
    th, td {
        border: 1px solid #cbd5e1;
        padding: 12px 15px;
    }
    th {
        background-color: #f1f5f9;
        text-align: center !important;
        color: #1e3a8a;
    }
    td {
        text-align: center;
    }
    td:nth-child(2) {
        text-align: left;
    }
    .destacado {
        background-color: #fdfce8;
        border-left: 5px solid #facc15;
        padding: 15px;
        margin: 20px 0;
        border-radius: 4px;
    }
    .page-break {
        page-break-after: always;
    }
</style>

# Propuesta Ejecutiva: Sistema Integral de Gestión Financiera y de Inventario

## 1. Resumen Ejecutivo
El presente documento delinea el plan estratégico y la arquitectura tecnológica para el desarrollo de un nuevo **Sistema Híbrido de Gestión Empresarial**. El objetivo principal es modernizar la operativa de la compañía transicionando de la actual dependencia de planillas de cálculo (Excel) y la arquitectura antigua (Milano Software), hacia una plataforma ágil, multiplataforma y blindada tecnológicamente, que garantice la disponibilidad ininterrumpida de los balances e inventarios de materias primas.

## 2. Arquitectura del Sistema Propuesto
### 2.1. Ecosistema Multiplataforma y Soporte Offline
- **Frontend (Interfaz Gráfica):** Se desarrollará bajo el estándar PWA (Progressive Web Application). Esto garantiza velocidad, uso en iOS/Android y computadoras web, sin descargas largas ni complejas.
- **Base de Datos "Offline-First":** La infraestructura funcionará con una sincronización inteligente. La aplicación guardará registros localmente para disponibilidad "sin conexión" en sectores con mala señal (plantas/fábricas), garantizando la operatividad.

### 2.2. Eje Metodológico: Base SQL Central y Exportación Excel
- **Motor Central Inmutable (SQL):** Toda la información transaccional residirá en un motor relacional SQL robusto y blindado (SQLite/Supabase).
- **Módulo de Descargas Estructuradas (Excel):** La visualización rápida y manipulación final para los usuarios se hará generando automáticamente reportes en .xlsx. Los usuarios no corren riesgo de "romper fórmulas" matriz porque el origen es SQL, solo se dedican a descargar el resultado digerido si desean auditar fuera de la aplicación.

<div class="page-break"></div>

### 2.3. Motor Analítico y Gestor Documental Integrado
- **Módulo de Ingreso Omnicanal:**
  1. *Carga Automatizada vía IA (Facturas en PDF)*: Lectura con Google Gemini API.
  2. *Carga Automatizada vía Visión (Fotografía)*: Extraer y archivar foto de los comprobantes.
  3. *Formulario de Validación / Carga Manual*: Opción de tipeo directo clásico.
- **Gestión Multi-Documental:** Capacidad de alojar los comprobantes originales físicamente vinculados a cada asiento contable.

## 3. Sugerencias y Estrategias por Inteligencia Artificial
<div class="destacado">
**1. Encriptación y Roles de Seguridad Multicapa:** Control para que un 'Operador' sólo cargue facturas de insumos, pero solo el rol 'Gerencial' acceda a los gráficos de rentabilidad. Las bases locales celulares estarán cifradas.
</div>

<div class="destacado">
**2. Sistema de Notificaciones Push Proactivas:** Alertas instantáneas en celular/PC cuando un Insumo o Materia Prima entra en rango crítico (Quiebre de Stock), o cuando hay un pago a proveedores por vencer.
</div>

<div class="destacado">
**3. Validación Doble (Human-in-the-Loop):** Ante una factura leída por IA mediante una foto borrosa, el sistema resaltará en color amarillo los números donde "dudó la IA", obligando al humano a confirmar manualmente antes de alterar las cuentas contables.
</div>

## 4. Diagrama Lógico de Infraestructura

![Diagrama Formal del Sistema](diagrama_formal.png)

<div class="page-break"></div>

## 5. Estrategia de Migración y Cronograma

| Fase de Trabajo | Actividad Principal | Meta Entregable |
|:---:|---|:---:|
| **Fase 1: Datos** | Escaneo estructural de los Excels actuales y modelado del Esquema de Base de Datos SQL. | Creación de Motor SQL. |
| **Fase 2: Motor Base** | Módulos de carga. Programar el guardado local del dispositivo a la Nube. Testing y Reportes Excel. | Aplicación web/app cargando en offline. |
| **Fase 3: IA Gemini OCR** | Desarrollar módulos de Python para conectarse a Gemini, leyendo mediante fotografías o PDFs de compra/venta. | Módulo Híbrido Multicarga funcionando. |
| **Fase 4: BI Analytics** | Programación visual del Framework de Estadísticas y Dashboards Interactivos sobre React.js. | Exportación total de Reportes Dinámicos Mensuales. |
