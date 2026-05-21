<style>
    body {
        padding: 40px 60px !important;
        font-family: 'Segoe UI', Roboto, Helvetica, sans-serif;
        text-align: justify;
        line-height: 1.6;
        color: #2d3748;
    }
    h1 {
        text-align: center;
        color: #1a365d;
        font-size: 2.2em;
        margin-bottom: 20px;
        border-bottom: 3px solid #2b6cb0;
        padding-bottom: 15px;
    }
    h2 {
        color: #2b6cb0;
        margin-top: 35px;
        border-bottom: 1px solid #e2e8f0;
        padding-bottom: 5px;
    }
    h3 {
        color: #2c5282;
        margin-top: 25px;
    }
    .phase-box {
        background-color: #ebf8ff;
        border-left: 5px solid #3182ce;
        padding: 15px;
        margin: 15px 0;
        border-radius: 4px;
    }
    .specs-box {
        background-color: #f0fff4;
        border-left: 5px solid #48bb78;
        padding: 15px;
        margin: 15px 0;
        border-radius: 4px;
    }
    .tier-box {
        background-color: #faf5ff;
        border-left: 5px solid #805ad5;
        padding: 15px;
        margin: 15px 0;
        border-radius: 4px;
    }
    .page-break {
        page-break-after: always;
    }
</style>

# Documento Maestro: ERP Universal Híbrido (v4.1 Consolidado)

## 1. Misión del Proyecto
Desarrollar un sistema de gestión profesional, escalable y multi-empresa que combine la robustez de las aplicaciones de escritorio con la accesibilidad de la nube. El sistema se divide en **Dos Capas de Operación** para garantizar estabilidad y rendimiento.

---

## 2. Arquitectura de Dos Capas (Escritura/Lectura)

<div class="tier-box">
<h3>Capa 1: App de Escritorio (Estación de Carga)</h3>
<ul>
    <li><b>Perfil:</b> Operadores, Contadores, Encargados de Stock.</li>
    <li><b>Tecnología:</b> Electron/FastAPI Bundle (Windows).</li>
    <li><b>Motor IA:</b> **Ollama + Gemma 4** instalado localmente para OCR de alta velocidad y Chatbot offline sin costos de API.</li>
    <li><b>Función:</b> CRUD completo (Crear, Editar, Borrar). Es el único punto de entrada de datos pesados.</li>
</ul>
</div>

<div class="tier-box">
<h3>Capa 2: App Web/PWA (Visor Universal)</h3>
<ul>
    <li><b>Perfil:</b> Gerentes, Vendedores, Dueños.</li>
    <li><b>Tecnología:</b> Next.js 14 optimizado para móviles.</li>
    <li><b>Función:</b> **Solo Lectura / Dashboards**. Consulta de estados de cuenta, reportes de stock y analítica en tiempo real sincronizada desde Supabase.</li>
</ul>
</div>

---

## 3. Especificaciones Técnicas Irrenunciables (Cimientos)
Aprobado por el equipo de arquitectura y desarrollo:
*   **Identidad:** UUIDs para todos los registros (Previene colisiones).
*   **Finanzas:** Uso estricto de `DECIMAL(15,2)` (Precisión contable real).
*   **Soberanía de Datos:** Local-first para operadores con sincronización en segundo plano hacia Supabase.
*   **Seguridad:** Hashing bcrypt y autenticación JWT.

---

## 4. Roadmap de Desarrollo v4.1

<div class="phase-box">
<b>Fase 1: Motor SQL y Backend (FastAPI)</b><br>
Modelado de bases de datos, lógica multi-tenant y configuración inicial de Supabase.
</div>

<div class="phase-box">
<b>Fase 2: Estación de Carga Desktop e integración Ollama</b><br>
Desarrollo de la App de escritorio capaz de procesar facturas localmente mediante Gemma 4.
</div>

<div class="phase-box">
<b>Fase 3: Visor Web y Dashboards</b><br>
Desarrollo de la interfaz de consulta móvil y reportes gerenciales en la nube.
</div>

<div class="phase-box">
<b>Fase 4: El Bot Omnipotente</b><br>
Integración final del agente de IA para manejo total del sistema vía lenguaje natural.
</div>

## 5. Aprobación Final
Este documento v4.1 representa el consenso final entre la visión estratégica y la viabilidad técnica.
**Aprobado por: gfcar (PM) | 2026-04-11**
