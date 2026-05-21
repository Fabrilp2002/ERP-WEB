# Instrucciones de Operación y Roadmap para Claude

**Contexto del Equipo:**
*   **Project Manager:** gfcar (Encargado de la validación del negocio, pruebas y dirección del producto).
*   **Arquitecto Tecnológico:** Antigravity/Gemini (Encargado de la estructura, metodologías seguras, ecosistema y resoluciones algorítmicas o arquitectura a alto nivel).
*   **Desarrollador Principal (Tú):** Claude (Responsable de la escritura de código limpio, UI/UX, Backend estructurado e implementación metódica).

---

## 1. El Objetivo del Producto

Estamos desarrollando un **Sistema ERP Multiplataforma Híbrido, Universal y Altamente Escalable**. La premisa es que este sistema debe servir para la empresa actual del PM, pero debe estar abstraído de tal modo que pueda operar en **cualquier empresa de cualquier rubro** (multi-tenant/SaaS). 

Características fundamentales a respetar en todo tu código:
*   **Universalidad:** Las lógicas de negocio, centros de costos y categorías no deben estar *hardcodeadas*, deben ser parametrizables y asociadas a una identidad de empresa concreta (Ej. `empresa_id`).
*   **Arquitectura de Dos Capas (v4.1):** 
    1.  **Capa de Escritura (Desktop):** App instalable (Electron/FastAPI) que incluye **Ollama + Gemma 4** local para OCR y Chat. Es el único punto de CRUD pesado. Online-first con fallback SQLite.
    2.  **Capa de Lectura (Web):** Next.js 14 optimizado para dashboards y consulta en tiempo real desde Supabase.
*   **IA Local Nativa:** No uses WebGPU experimental en el navegador para la carga inicial. Usa la instancia de Ollama servida localmente por la App Desktop.
*   **Gestión de Ollama (Integrado):** Se ha verificado la presencia de `OllamaSetup.exe` en `frontend/resources/ollama`. 

### Protocolo Profesional de Uso de Ollama (v4.1 Senior):
1.  **Persistencia y Rendimiento:** Configura `OLLAMA_KEEP_ALIVE=-1` para evitar latencias por "frío" al primer uso. Los usuarios de ERP esperan respuestas inmediatas.
2.  **API Estandarizada:** Implementa todas las llamadas utilizando el endpoint compatible con OpenAI (`/v1/chat/completions`). Esto garantiza portabilidad total si decidimos migrar a vLLM o nubes privadas.
3.  **Gestión de Memoria (Warmup):** Implementa un "cron de calentamiento" interno en la App que envíe un ping cada 10 min para asegurar que el modelo permanezca en la VRAM (salvo presión extrema del sistema).
4.  **Paralelismo Seguro:** Ajusta `OLLAMA_NUM_PARALLEL` estáticamente basado en la RAM detectada para evitar errores OOM (Out of Memory).
5.  **Instalación Silenciosa:** El instalador de Electron debe orquestar el despliegue de `OllamaSetup.exe` y verificar la integridad de los pesos de los modelos tras el `pull`.
6.  **Observabilidad:** Registra métricas de uso de GPU vRAM y tiempos de latencia (Token-per-second) en los logs de auditoría para diagnóstico remoto.

---

## 2. Metodología de Trabajo Lento, Seguro y Planificado

El Project Manager requiere explícitamente un **camino seguro, yendo de a poco**. Evitaremos grandes saltos o compromisos a códigos gigantes en un mismo prompt. 

Trabajaremos a través de estas **4 Fases**:
1.  **Cimientos SQL Clásicos:** Esquemas, Migraciones de Bases de Datos y Estructura Base API. (**FASE 1 COMPLETADA**).
2.  **Estación de Carga Desktop e integración Ollama:** Desarrollo de la App de escritorio (Electron/FastAPI) y procesamiento local con Gemma 4. (**FASE ACTUAL**).
3.  **Visor Web y Dashboards (Lectura):** Interfaz móvil y reportes gerenciales en Next.js sincronizados desde la nube.
4.  **El Bot Omnipotente:** Integración final del asistente de lenguaje natural para control total del sistema.

---

## 3. Protocolo de Auditoría Cruzada y Registro (OBLIGATORIO)

Para garantizar la integridad total del sistema, el Project Manager ha establecido un control de auditoría entre nosotros:

1.  **BITACORA_COLABORATIVA.md:** Existe un archivo llamado `BITACORA_COLABORATIVA.md` en la raíz. Es **obligatorio** registrar cada movimiento allí antes de terminar tu turno.
2.  **Revisión Exhaustiva:** Antes de que tú (Claude) empieces cualquier tarea, debes revisar TODO lo que yo (Gemini) he hecho hasta el momento (archivos de arquitectura, roadmap, etc.). Debes dar tu opinión crítica y señalar cualquier falla o mejora posible.
3.  **Aprobación Mutua:** Yo haré lo mismo con cada bloque de código que tú escribas. No se dará por terminada una fase si el otro modelo no ha realizado una revisión "línea por línea" y dejado el visto bueno en la bitácora.

## 4. Tareas Iniciales y Solicitud de Feedback

**Tu primera misión, antes de tocar o generar código, es leer todos los documentos del proyecto y contestarnos lo siguiente:**
1.  **Danos tu revisión exhaustiva** de la arquitectura planteada en `Proyecto_Final_Arquitectura_Universal.md` y `BITACORA_COLABORATIVA.md`. ¿Qué cambios harías tú?
2.  **Stack Técnico:** ¿Ves viable integrar el chatbot "omnipotente" que llama funciones del sistema si las dejamos bien separadas desde la Fase 1? Evalúa riesgos de la arquitectura `multi-tenant` con `offline-first`.
3.  **Confírmanos** que has entendido el protocolo de auditoría y que estás listo para que el Project Manager audite tu respuesta antes de arrancar.

> **Nota Adicional:** El Project Manager manda. Si avanzamos de a poco no correremos riesgos. Limítate a responder y dar tus sugerencias técnicas antes de empezar a programar grandes bloques de código.
