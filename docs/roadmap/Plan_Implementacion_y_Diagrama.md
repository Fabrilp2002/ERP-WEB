# Plan de Implementación: Sistema Integral de Gestión Financiera y de Inventario

## Objetivo del Proyecto

Desarrollar un sistema multiplataforma enfocado en la contabilidad y finanzas (Web/App Móvil/Desktop) inspirado en la robusta estructura base del sistema heredado "MILANO SOFTWARE". El sistema moderno utilizará inteligencia artificial con la **Gemini API** para lectura automática de facturas (OCR) e ingresos de recibos, y permitirá gestionar ingresos, egresos, stock de materias primas y estados de cuentas totalmente en tiempo real. 

## 1. Arquitectura Tecnológica e Inteligencia Artificial

*   **Modalidad Híbrida de Carga (IA o Manual):** El sistema contará con tres vías a elección del usuario para ingresar los datos:
    1.  **Carga Inteligente por PDF:** Sube la factura digital y Gemini extrae la información.
    2.  **Carga Inteligente por Imagen:** Saca una foto al recibo y Gemini hace el OCR.
    3.  **Carga Manual:** Un formulario clásico y rápido para tipear la información si no se dispone del archivo o si el usuario prefiere hacerlo directamente.
*   **Gestor Documental (Subida y Extracción):** El sistema contará con un módulo específico para **subir y almacenar documentos originales** (comprobantes, remitos) y otra función clave para **extraer/exportar reportes y documentos** (descargar resúmenes en PDF o Excel de operaciones, balances o inventarios, así como la recuperación de las facturas previamente subidas).
*   **Estructura Base (Inspirada en MILANO SOFTWARE):** Para mantener una transición amigable, se replicará el árbol de operaciones de este ERP clásico:
    *   *Plan de Cuentas:* Categorización estructurada de centros de costos y centros de ganancias.
    *   *Módulo de Inventarios:* Actualización basada en remitos y facturas para cálculos de costos en (MP / Insumos / Terminados).
*   **Frontend (PWA / App Móvil):** La interfaz se desarrollará en React.js / React Native, con funcionamiento **offline-first** enfocado en accesibilidad veloz (ingresos rápidos en el piso de fábrica o desde cualquier lugar). Las estadísticas gerenciales se visualizarán en un Dashboard con componentes modernos.
*   **Backend & Base de Datos:** Se creará con Node.js combinado con una base de datos en tiempo real (como Supabase o Firebase). Esto permite el ansiado "respaldo doble": los datos viven en el dispositivo local y, apenas hay WiFi/Datos Móviles en segundo plano y automáticamente, se replican y guardan como respaldo en la web.

## 2. Flujo de Funcionamiento del Sistema (Diagrama)

El siguiente gráfico ilustra cómo interactuarán las partes, desde el usuario en su móvil hasta el sistema contable replicando a MILANO y terminando en el panel de gráficos.

![Diagrama del Flujo](diagrama.png)

## 3. RoadMap y Fases de Trabajo

### Fase 1: Arquitectura, IA e Ingeniería Inversa (Semanas 1-2)
- Replicación arquitectónica de tablas esenciales (Clientes, Proveedores, Stock MP) basándose en las plantillas extraídas de la empresa y en el flujo del software Milano.
- Conexión de prueba con la **API de Gemini** para establecer el módulo de captura de datos: experimentar con la lectura de comprobantes reales.
- Creación de base de datos nube-local combinada.

### Fase 2: Core del Sistema (Semanas 3-5)
- Desarrollo del motor local para carga de datos (App).
- Construcción de pantallas para Clientes (Estado de Cuentas), Inventario de Materia Prima y carga manual o asistida de Gastos/Ventas.

### Fase 3: Gráficos Funcionales Interactivos (Semanas 6-7)
- Diseño del Dashboard Gerencial en la web.
- Programación de visualizaciones para comparar la variación de costos de Insumos vs utilidades de ventas y métricas históricas mensuales.

### Fase 4: Beta y Despliegue Multiplataforma (Semanas 8-9)
- Optimización de accesibilidad y estabilización en dispositivos móviles o PC simultáneas en pruebas de conectividad intermitente (Offline Mode testing).
- Despliegue completo con acceso por usuario y rol.
