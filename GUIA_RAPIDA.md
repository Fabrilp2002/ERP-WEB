# Guía Rápida — ERP Universal

## 🚀 Primeros 5 Minutos

### Método 1: Un solo clic
```
Doble clic en INICIAR_ERP.vbs
```
O usa el acceso directo "ERP Universal" del Escritorio (creado con `INSTALAR_ACCESO_DIRECTO.bat`).

### Método 2: Manualmente
```bash
# 1. Navegar al proyecto
cd "C:\Users\gfcar\Desktop\IA\Empresa 1"

# 2. Iniciar todo (backend + frontend)
start_all.bat

# 3. Abrir navegador
http://localhost:3000
```

### Método 3: Paso a paso
```bash
# Terminal 1 — Backend
cd "C:\Users\gfcar\Desktop\IA\Empresa 1"
python -m uvicorn backend.main:app --reload --port 8000

# Terminal 2 — Frontend
cd "C:\Users\gfcar\Desktop\IA\Empresa 1\frontend"
npm run dev

# Abrir navegador
http://localhost:3000
```

---

## 📍 Dónde Está Todo

| Necesito... | Archivo |
|---|---|
| **Entender arquitectura** | `docs/arquitectura/README.md` |
| **Ver endpoints API** | `docs/api/API_REFERENCE.md` o `http://localhost:8000/docs` |
| **Plan de desarrollo** | `docs/roadmap/README.md` |
| **Convenciones de código** | `docs/especificaciones/README.md` |
| **Registro de trabajo** | `BITACORA_COLABORATIVA.md` |
| **Mapa del proyecto** | `ESTRUCTURA_PROYECTO.md` |
| **Variables de entorno** | `.env.example` |
| **Estado de fases** | `CLAUDE.md` → Estado de Fases |
| **Migraciones SQL** | `db/migrations/` |

---

## 🔧 Tareas Comunes

### Crear nuevo endpoint en Backend
1. Ir a `backend/routers/` → crear `nuevo_router.py`
2. Importar en `backend/main.py`: `app.include_router(nuevo_router.router)`
3. Documentar en `docs/api/API_REFERENCE.md`
4. Registrar en `BITACORA_COLABORATIVA.md`

### Crear nueva página en Frontend
1. Ir a `frontend/src/app/(app)/`
2. Crear carpeta: `mi_pagina/page.tsx`
3. Agregar en `Sidebar.tsx`: navegar a `/mi_pagina`
4. Agregar API client en `frontend/src/lib/api.ts` si requiere datos

### Cambiar esquema de Base de Datos
1. Crear migración en `db/migrations/` con formato `YYYY-MM-DD_descripcion.sql`
2. Hacer la migración idempotente (usar `IF NOT EXISTS`, `DO $$ ... $$`)
3. Actualizar modelos en `backend/models/schemas.py`
4. Registrar en `BITACORA_COLABORATIVA.md`

### Instalar nuevas dependencias
```bash
# Backend
cd backend && pip install paquete && pip freeze > requirements.txt

# Frontend
cd frontend && npm install paquete
```

### Configurar clave Gemini API
1. Obtener key en https://aistudio.google.com/app/apikey
2. Opción A: Guardar en `backend/.env` como `GEMINI_API_KEY=tu_clave`
3. Opción B: Usar el panel Ajustes en la página OCR del frontend

---

## 🐛 Debugging

### Backend no inicia
```bash
# 1. Verificar PostgreSQL está corriendo
#    Servicio: postgresql-x64-17 (debe estar en "Iniciado")
# 2. Verificar DATABASE_URL en backend/.env
# 3. Ejecutar desde la RAÍZ del proyecto (no desde backend/):
python -m uvicorn backend.main:app --reload --log-level debug --port 8000
# 4. Si falla un import, instalar dependencias:
pip install -r backend/requirements.txt
```

### Frontend no carga
```bash
# 1. Verificar NEXT_PUBLIC_API_URL en frontend/.env.local
# 2. Backend debe estar corriendo en puerto 8000
# 3. Limpiar cache: 
cd frontend && rm -rf .next && npm run dev
# 4. Si node_modules está corrupto (Google Drive), reinstalar en disco local
```

### OCR no funciona
```bash
# 1. Verificar que GEMINI_API_KEY está configurada (backend/.env o panel OCR)
# 2. Verificar conectividad a internet (Gemini API requiere conexión)
# 3. Si devuelve 502: revisar backend/logs — posible JSON truncado (ya hay parser robusto)
```

### Chatbot no responde
```bash
# 1. Verificar GEMINI_API_KEY en backend/.env
# 2. El chatbot usa Gemini function calling — requiere internet
# 3. Si Gemini no está configurado, el chat funciona en modo informativo limitado
```

---

## 📚 Documentación Completa

Navega a la carpeta `docs/` para:
- Arquitectura completa (Hub & Spoke)
- Todas las APIs documentadas
- Especificaciones técnicas
- Roadmap de desarrollo
- Diagramas (Mermaid + PNG)

---

## 👥 Contacto

- **Project Manager:** gfcar (validación de negocio)
- **Arquitecto:** Gemini (decisiones de arquitectura)
- **Developer:** Claude (implementación)
- **Registro:** Ver `BITACORA_COLABORATIVA.md`

---

## ⚡ Quick Reference

```
Backend:    http://localhost:8000
            Swagger: http://localhost:8000/docs
Frontend:   http://localhost:3000
Database:   postgresql+asyncpg://postgres@localhost:5432/erp_db
IA:         Gemini API (configurar en backend/.env)
```

¡Listo para empezar! 🚀
