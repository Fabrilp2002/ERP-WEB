# Documento Base: Arquitectura y Estructura del Sistema ERP Híbrido

## 1. Resumen y Viabilidad del Proyecto
El desarrollo de este **Sistema Híbrido de Gestión Empresarial (Finanzas e Inventario)** es **altamente viable y escalable**. La combinación de una arquitectura "offline-first" con inteligencia artificial para la carga de comprobantes resuelve uno de los mayores cuellos de botella en la gestión empresarial: la carga manual de datos y la dependencia de conexión permanente.

La tecnología elegida (PWA, Bases de datos SQL descentralizadas/sincronizadas, y Gemini para OCR) conforman un stack moderno y robusto. Al abstraer la lógica de negocio basada en el modelo heredado, este sistema se convierte en una **solución universal (SaaS/On-Premise)**, capaz de ser implementada en *cualquier empresa*, independientemente de su rubro (manufactura, comercialización, servicios).

---

## 2. Estructura Organizativa y Roles

Para garantizar el éxito y la correcta implementación, el equipo de desarrollo se estructura de la siguiente manera:

*   **Director de Proyecto (Project Manager):** **Usuario (Propietario del Proyecto)**. Encargado de definir los requerimientos de negocio, flujos de trabajo de la empresa, validaciones de interfaz y el rumbo comercial del producto.
*   **Arquitecto Tecnológico y Estratega (Gemini / Antigravity):** Encargado de formular la arquitectura, supervisar la integración de componentes complejos (como IA y BD), y guiar la visión técnica a alto nivel.
*   **Desarrollador Principal (Claude):** Encargado de la escritura de código, implementación de la lógica en el Frontend y Backend, creación de componentes y resolución de problemas de programación a bajo nivel guiado por la arquitectura.

---

## 3. Arquitectura General y Tecnologías (Universal)

Esta estructura está diseñada para ser agnóstica a la industria, basándose en principios contables y de stock universales.

### 3.1. Frontend (Interfaz de Usuario)
*   **Tecnología:** React.js o Next.js (Web) / React Native (Móvil). Empaquetado como PWA (Progressive Web App).
*   **Concepto:** "Offline-First". El cliente web guarda datos en IndexedDB/SQLite local (por ejemplo usando RxDB o WatermelonDB) garantizando que la aplicación jamás se bloquee por falta de internet.
*   **Módulos Nativos:**
    *   **Dashboard:** Analítica, métricas gerenciales y gráficos dinámicos.
    *   **Operador:** Carga de facturas (Vía IA OCR, Foto o Manual).
    *   **Inventario:** Centro de costos, remitos y seguimiento de stock.

### 3.2. Backend y Almacenamiento Central
*   **Tecnología:** Node.js + Base de datos SQL (PostgreSQL vía Supabase u otra capa de Backend-as-a-Service escalable).
*   **Concepto:** Actúa como la "Verdad Absoluta" y motor de sincronización. Recibe datos de las terminales cuando tienen internet, resuelve conflictos, y orquesta los respaldos.

### 3.3. Motor de Inteligencia Artificial (IA Local Nativa)
*   **Tecnología:** Ollama + Gemma 4 (E2B para Chatbot, E4B para OCR) ejecutándose localmente en la App Desktop.
*   **Funcionalidad:** Recepción de documentos no estructurados (Fotos, PDFs) y extracción estructurada de datos. La IA corre localmente para garantizar privacidad y cero costos por transacción. Incorpora validación "Human-in-the-Loop" para que un humano apruebe datos de baja confianza.

---

## 4. Instrucciones para Claude (Flujo de Trabajo)

> **Nota para Claude:** El Project Manager te asignará tareas específicas basadas en esta arquitectura. Tu objetivo será traducir las necesidades descritas aquí en código limpio, modular y documentado.

1.  **Modularidad:** Todo el código que desarrolles debe pensarse para un entorno multi-empresa (Multi-tenant). Las tablas SQL deben contemplar un `empresa_id` u operar bajo esquemas separados si es necesario.
2.  **Seguridad y Roles:** El sistema maneja información financiera confidencial. Implementa siempre restricciones basadas en roles (ej. Operador vs. Gerencial).
3.  **Prioridad al Modo Fuera de Línea:** Al crear lógicas de guardado, asume siempre que la conexión a internet puede fallar. Utiliza colas de sincronización en segundo plano.
4.  **Colaboración Activa:** Consulta cualquier incongruencia arquitectónica con el Project Manager o conmigo (Gemini) antes de avanzar en desarrollos que impliquen reescribir mucha lógica estructural.
