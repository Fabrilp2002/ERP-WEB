"""
ERP Universal — Backend FastAPI v5.0 (cloud)
Punto de entrada principal de la API.
Swagger UI disponible en: /docs
"""
import json
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import settings
from .middleware.security_headers import SecurityHeadersMiddleware
from .routers import (
    auth, clientes, proveedores, comprobantes, inventario, dashboard,
    ocr, export, chatbot, configuracion, pagos, usuarios,
    empresa, adjuntos, actividad, reportes, recetas, lotes,
)

# Configurar logging temprano
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("erp_web")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="""
## ERP Universal — API REST (cloud)

Sistema contable multi-tenant para gestión de:
- **Comprobantes**: registro de facturas externas de compra y venta
- **Cuentas Corrientes**: saldos de clientes y proveedores
- **Inventario**: stock de productos y materia prima
- **Bancos**: movimientos de cuentas bancarias
- **Dashboard**: KPIs en tiempo real

### Roles
| Rol | Permisos |
|---|---|
| `admin` | CRUD completo + configuración |
| `operador` | CRUD de comprobantes, inventario y cuentas |
| `viewer` | Solo GET — dashboards y reportes remotos |

### Montos
Todos los montos usan `DECIMAL(15,2)`. Nunca `float`.
    """,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ─── Security middleware ─────────────────────────────────────────────────────
app.add_middleware(SecurityHeadersMiddleware)

# ─── CORS ────────────────────────────────────────────────────────────────────
# Las origins se leen de settings.CORS_ORIGINS (string JSON).
# En Railway/Vercel se setea por env var:
#   CORS_ORIGINS=["https://erp-web.vercel.app","http://localhost:3000"]
# Tambien se permiten aliases/deployments Vercel del ERP que empiecen por
# erp-web, para evitar cortes cuando Vercel rota el dominio de produccion.
try:
    cors_origins = json.loads(settings.CORS_ORIGINS)
    if not isinstance(cors_origins, list):
        cors_origins = [str(cors_origins)]
except Exception:
    logger.warning("CORS_ORIGINS no es JSON válido, fallback a localhost")
    cors_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]

vercel_origin_regex = r"^https://erp-web[a-z0-9-]*\.vercel\.app$"

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=vercel_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
logger.info("CORS allow_origins=%s", cors_origins)
logger.info("CORS allow_origin_regex=%s", vercel_origin_regex)


# ─── Routers ─────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(clientes.router)
app.include_router(proveedores.router)
app.include_router(comprobantes.router)
app.include_router(inventario.router)
app.include_router(dashboard.router)
app.include_router(ocr.router)
app.include_router(export.router)
app.include_router(chatbot.router)
app.include_router(configuracion.router)
app.include_router(pagos.router)
app.include_router(usuarios.router)
app.include_router(empresa.router)
app.include_router(adjuntos.router)
app.include_router(actividad.router)
app.include_router(reportes.router)
app.include_router(recetas.router)
app.include_router(lotes.router)


# ─── Health check & root ─────────────────────────────────────────────────────

@app.get("/", tags=["Sistema"], summary="Health check raíz")
async def root():
    return {
        "sistema": settings.APP_NAME,
        "version": settings.VERSION,
        "estado": "operativo",
        "docs": "/docs",
    }


@app.get("/health", tags=["Sistema"], summary="Health check para load balancers")
async def health():
    """Endpoint dedicado para health checks de Render / load balancer.
    Respuesta inmediata para evitar timeouts en cold start del free tier.
    """
    return {"status": "ok", "version": "5.1-chatbot-transaccional"}
