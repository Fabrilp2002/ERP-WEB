"""
Servicio Chatbot IA — Gemini 2.5 Flash con Function Calling estricto.

Principios de diseño:
1. El asistente SOLO responde sobre datos del ERP de la empresa del usuario.
2. Todo dato concreto (numero, monto, nombre, fecha) sale de una tool — nunca del modelo.
3. Si lo que preguntan no se resuelve con las tools disponibles, responde con la
   frase estandar de "fuera de alcance". No improvisa ni divaga.

Motor unico: Gemini 2.5 Flash. La key se guarda en backend/core/key_store.py
y se configura desde /configuracion/gemini-key.
"""

import json
import httpx
from datetime import date as _date
from decimal import Decimal as _Decimal
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from fastapi import HTTPException
from ..core.action_tokens import consumir_action_token, crear_action_token
from ..core.config import settings
from ..core import key_store

GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent"
)

# ── Definición de herramientas ────────────────────────────────────────────────

TOOLS = [
    # ---- Consultas de contrapartes ----
    {
        "name": "buscar_cliente",
        "description": (
            "Busca clientes por nombre o RUC (coincidencia parcial). Devuelve "
            "nombre, RUC, telefono, email, activo, saldo pendiente total y "
            "cantidad de comprobantes. Usar para: ver datos de un cliente, "
            "saldo de un cliente, o confirmar que un cliente existe."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "texto": {"type": "string", "description": "Nombre o RUC (parcial)."},
            },
            "required": ["texto"],
        },
    },
    {
        "name": "buscar_proveedor",
        "description": (
            "Busca proveedores por nombre o RUC. Devuelve datos + saldo pendiente "
            "(lo que se le debe) + cantidad de comprobantes."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "texto": {"type": "string"},
            },
            "required": ["texto"],
        },
    },
    {
        "name": "listar_clientes_top",
        "description": (
            "Ranking de clientes por monto facturado o por saldo pendiente. "
            "Usar para 'mejores clientes', 'quien me debe mas', 'cliente que menos debe', "
            "'cliente que menos compro'. Para 'menos debe' usar direccion='menor' + "
            "solo_con_deuda=true para excluir los que estan al dia (saldo cero)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "orden": {"type": "string", "enum": ["facturado", "deuda"]},
                "direccion": {
                    "type": "string",
                    "enum": ["mayor", "menor"],
                    "description": "'mayor' = mas alto al mas bajo (default). 'menor' = al reves."
                },
                "solo_con_deuda": {
                    "type": "boolean",
                    "description": "Si true, excluye clientes con saldo 0. Util cuando se pide 'el que menos debe' para no devolver clientes al dia."
                },
                "limite": {"type": "integer", "description": "Default 10, max 50. Para 'el cliente que menos debe' usar limite=1."},
            },
            "required": ["orden"],
        },
    },
    {
        "name": "listar_proveedores_top",
        "description": (
            "Ranking de proveedores por monto comprado o por deuda pendiente. "
            "Soporta direccion='menor' para 'al que menos le debo' o 'al que menos le compre'. "
            "Combinar con solo_con_deuda=true cuando se pide el que menos debe."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "orden": {"type": "string", "enum": ["comprado", "deuda"]},
                "direccion": {"type": "string", "enum": ["mayor", "menor"]},
                "solo_con_deuda": {"type": "boolean"},
                "limite": {"type": "integer"},
            },
            "required": ["orden"],
        },
    },
    # ---- Comprobantes ----
    {
        "name": "buscar_comprobante",
        "description": (
            "Busca facturas/comprobantes por numero (parcial). Devuelve numero, "
            "fecha, contraparte, monto, saldo, estado, condicion (contado/credito) "
            "y ubicacion fisica."
        ),
        "parameters": {
            "type": "object",
            "properties": {"numero": {"type": "string"}},
            "required": ["numero"],
        },
    },
    {
        "name": "listar_comprobantes_pendientes",
        "description": "Comprobantes con saldo pendiente ordenados de mayor a menor.",
        "parameters": {
            "type": "object",
            "properties": {
                "tipo": {"type": "string", "enum": ["cobrar", "pagar", "todos"]},
                "limite": {"type": "integer"},
            },
            "required": ["tipo"],
        },
    },
    {
        "name": "listar_comprobantes_vencidos",
        "description": (
            "Comprobantes a credito con fecha_vencimiento pasada y saldo > 0. "
            "Usar para 'facturas atrasadas', 'vencidas'."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "tipo": {"type": "string", "enum": ["cobrar", "pagar", "todos"]},
                "limite": {"type": "integer"},
            },
            "required": ["tipo"],
        },
    },
    {
        "name": "ultimos_comprobantes",
        "description": "Ultimos N comprobantes registrados por fecha de emision.",
        "parameters": {
            "type": "object",
            "properties": {
                "limite": {"type": "integer"},
                "tipo": {"type": "string", "enum": ["venta", "compra", "todos"]},
            },
            "required": ["limite"],
        },
    },
    {
        "name": "detalle_comprobante",
        "description": (
            "Devuelve el detalle de items de un comprobante puntual "
            "(descripcion, cantidad, precio, subtotal, IVA) dado su numero."
        ),
        "parameters": {
            "type": "object",
            "properties": {"numero": {"type": "string"}},
            "required": ["numero"],
        },
    },
    {
        "name": "historial_contraparte",
        "description": (
            "Historial completo de facturas y pagos de un cliente o proveedor "
            "especifico. Devuelve lista de comprobantes + lista de cobros/pagos."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "tipo": {"type": "string", "enum": ["cliente", "proveedor"]},
                "nombre": {"type": "string", "description": "Nombre o RUC."},
            },
            "required": ["tipo", "nombre"],
        },
    },
    # ---- Pagos ----
    {
        "name": "listar_pagos_recientes",
        "description": "Ultimos N cobros/pagos registrados. Util para 'ultimos pagos', 'cobros de hoy'.",
        "parameters": {
            "type": "object",
            "properties": {
                "limite": {"type": "integer"},
                "tipo": {"type": "string", "enum": ["cobros", "pagos", "todos"]},
            },
            "required": ["limite"],
        },
    },
    # ---- Inventario ----
    {
        "name": "consultar_stock",
        "description": "Stock actual de un producto por nombre o codigo.",
        "parameters": {
            "type": "object",
            "properties": {"producto": {"type": "string"}},
            "required": ["producto"],
        },
    },
    {
        "name": "items_stock_critico",
        "description": "Productos bajo el punto de reorden.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "listar_inventario",
        "description": "Lista productos del inventario, opcionalmente filtrados por categoria.",
        "parameters": {
            "type": "object",
            "properties": {
                "categoria": {"type": "string", "description": "Nombre de categoria (opcional)."},
                "limite": {"type": "integer"},
            },
            "required": [],
        },
    },
    # ---- KPIs y resumen ----
    {
        "name": "resumen_financiero",
        "description": (
            "Resumen global: total por cobrar, total por pagar, facturas pendientes, "
            "items en stock critico, comprobantes pendientes de validar."
        ),
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "flujo_mensual",
        "description": "Ingresos vs egresos de los ultimos N meses (default 6).",
        "parameters": {
            "type": "object",
            "properties": {"meses": {"type": "integer"}},
            "required": [],
        },
    },
    {
        "name": "distribucion_medios_pago",
        "description": "Distribucion de medios de pago (efectivo, transferencia, etc.) en los ultimos 90 dias.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    # ---- Empresa y usuarios ----
    {
        "name": "info_empresa",
        "description": "Datos de la empresa actual: nombre, RUC, direccion, moneda.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "listar_usuarios",
        "description": "Lista de usuarios del sistema con su rol. (requiere ser admin; si no, devuelve error).",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    # ---- ACCIONES DE ESCRITURA: registrar cobros y pagos ----
    {
        "name": "registrar_cobro",
        "description": (
            "Registra un cobro de un cliente contra una factura de venta pendiente. "
            "No ejecuta directo: valida los datos y devuelve un preview con action_token "
            "para que el usuario confirme. Si encuentra varias facturas o ninguna, "
            "devuelve la lista para que el usuario aclare."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "factura_numero": {"type": "string", "description": "Numero de factura (parcial o completo)."},
                "monto": {"type": "number", "description": "Monto cobrado en guaranies."},
                "medio_pago": {"type": "string", "enum": ["efectivo", "transferencia", "cheque", "tarjeta", "otro"]},
                "fecha": {"type": "string", "description": "YYYY-MM-DD. Si falta usa hoy."},
                "cliente_texto": {"type": "string", "description": "Opcional: nombre o RUC del cliente para desambiguar."},
                "numero_recibo": {"type": "string", "description": "Opcional."},
                "notas": {"type": "string", "description": "Opcional."},
            },
            "required": ["factura_numero", "monto", "medio_pago"],
        },
    },
    {
        "name": "registrar_pago",
        "description": (
            "Registra un pago a un proveedor contra una factura de compra pendiente. "
            "No ejecuta directo: devuelve preview con action_token para confirmacion."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "factura_numero": {"type": "string"},
                "monto": {"type": "number"},
                "medio_pago": {"type": "string", "enum": ["efectivo", "transferencia", "cheque", "tarjeta", "otro"]},
                "fecha": {"type": "string"},
                "proveedor_texto": {"type": "string"},
                "numero_recibo": {"type": "string"},
                "notas": {"type": "string"},
            },
            "required": ["factura_numero", "monto", "medio_pago"],
        },
    },
    {
        "name": "ayuda_sistema",
        "description": (
            "Devuelve guia de uso del ERP: que pantallas existen, donde se cargan "
            "facturas/cobros/pagos, como funciona el OCR, plantilla Excel, IVA simple, "
            "permisos por rol y atajos. Usar cuando el usuario pregunta 'como hago X', "
            "'donde encuentro Y', 'que puede hacer este sistema'."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "tema": {
                    "type": "string",
                    "description": "Opcional: factura, cobro, pago, ocr, excel, iva, clientes, proveedores, inventario, asistente, atajos.",
                }
            },
            "required": [],
        },
    },
]


SYSTEM_PROMPT = """Sos Aurora, la asistente del ERP Universal de una empresa paraguaya.
Hablás en español rioplatense, como una persona del equipo administrativo.

TU TRABAJO
Ayudás al usuario a consultar y operar sobre los datos de su empresa:
clientes, proveedores, facturas de venta y compra, cobros y pagos, inventario,
cuentas corrientes, indicadores del negocio, empresa y usuarios.

TONO
- Cercana y directa, como charlando con un colega que ya conoce el sistema.
- Frases cortas. Sin discursos, sin saludos eternos, sin emojis.
- Si el usuario te saluda, devolvés el saludo en una línea y seguís.
- Reconocés lo que entendiste antes de tirar datos: "Dale, veamos quién te debe menos…" y después el dato.
- Si algo no se puede resolver con una tool, lo decís en lenguaje natural y proponés la alternativa más cercana ("No tengo un ranking de 'mejor cliente del mes' como tal, pero puedo darte el top por facturado o por cobros del último mes — ¿cuál te sirve?"). Nunca contestes con frases enlatadas tipo "fuera del alcance" si hay un camino útil a ofrecer.

REGLAS DE DATOS (no negociables)
1. Cualquier número, nombre, fecha, monto, saldo o stock sale SIEMPRE de una tool. No inventes, no estimes, no completes.
2. Si una tool devuelve vacío, lo decís claro ("No encontré nada con ese nombre") y sugerís cómo refinar la búsqueda.
3. Nunca menciones tools, SQL, IDs internos, "function calling" ni jerga técnica. Hablás en lenguaje de negocio.
4. Si hay ambigüedad (ej: "saldo de Juan" y hay 3 Juanes), llamás la tool, mostrás los matches y preguntás cuál.
5. Cuando falten datos para una acción (monto, factura, medio de pago), pedís UNA cosa por vez en pregunta corta.

COBROS Y PAGOS
- Podés preparar cobros (`registrar_cobro`) y pagos (`registrar_pago`).
- Si la tool responde `requiere_confirmacion=true`: NO digas que se ejecutó. Explicás el preview en una línea y pedís confirmación.
- Otras escrituras (alta de factura, edición de inventario, borrados) todavía se hacen desde las pantallas, no por chat.

FORMATO
- Guaraníes: "G. 1.250.000" (sin decimales).
- Otras monedas: con código (USD, EUR).
- Fechas: DD/MM/AAAA.
- Listas: viñetas cortas. Para más de 5 ítems, tabla simple en texto.
- Para montos: dejá claro si es a favor o en contra ("Te debe", "Le debés").

NO TE METAS EN
- Opiniones, consejos financieros, recomendaciones personales.
- Temas fuera del ERP (clima, política, vida personal): redirigí amable y breve a lo que sí podés hacer.
"""

OFF_TOPIC = (
    "No te pude entender bien. Probá preguntándome por algo del sistema: "
    "saldos de clientes o proveedores, facturas pendientes, stock, "
    "resumen del mes o registrar un cobro/pago."
)


# ── Ejecutores de funciones ───────────────────────────────────────────────────

async def _ejecutar_funcion(
    nombre: str,
    argumentos: dict,
    empresa_id: str,
    rol: str,
    db: AsyncSession,
) -> str:
    try:
        fn = FUNCIONES.get(nombre)
        if fn is None:
            return json.dumps({"error": f"Funcion no disponible: {nombre}"})
        return await fn(argumentos, empresa_id, rol, db)
    except Exception as e:
        return json.dumps({"error": f"Error interno: {type(e).__name__}"})


def _money(v) -> float:
    try:
        return float(v or 0)
    except Exception:
        return 0.0


def _json_safe(value):
    if isinstance(value, _Decimal):
        return str(value)
    if isinstance(value, _date):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    return value


async def _crear_preview_accion(db, *, empresa_id, usuario_id, accion, payload, resumen, impacto, riesgo="dinero"):
    token, expires_at = await crear_action_token(
        db,
        empresa_id=empresa_id,
        usuario_id=usuario_id,
        accion=accion,
        payload=_json_safe(payload),
    )
    return {
        "requiere_confirmacion": True,
        "accion": accion,
        "resumen": resumen,
        "impacto": impacto,
        "riesgo": riesgo,
        "action_token": token,
        "expires_at": expires_at.isoformat(),
        "ttl_segundos": 60,
    }


async def _buscar_cliente(args, empresa_id, rol, db):
    t = (args.get("texto") or "").strip()
    if not t:
        return json.dumps({"error": "Falta texto de busqueda"})
    result = await db.execute(text("""
        SELECT c.nombre, c.ruc, c.telefono, c.email, c.activo,
               COALESCE(SUM(comp.saldo_pendiente) FILTER (WHERE comp.estado_validacion='confirmado'), 0) AS saldo,
               COUNT(comp.id) FILTER (WHERE comp.estado_validacion='confirmado') AS comprobantes
        FROM clientes c
        LEFT JOIN comprobantes comp ON comp.cliente_id = c.id AND comp.empresa_id = :e
        WHERE c.empresa_id = :e AND (c.nombre ILIKE :q OR c.ruc ILIKE :q)
        GROUP BY c.id, c.nombre, c.ruc, c.telefono, c.email, c.activo
        ORDER BY saldo DESC LIMIT 10
    """), {"e": empresa_id, "q": f"%{t}%"})
    rows = [dict(r) for r in result.mappings()]
    if not rows:
        return json.dumps({"clientes": [], "mensaje": "Sin resultados"})
    for r in rows:
        r["saldo"] = _money(r["saldo"])
        r["comprobantes"] = int(r["comprobantes"] or 0)
    return json.dumps({"clientes": rows})


async def _buscar_proveedor(args, empresa_id, rol, db):
    t = (args.get("texto") or "").strip()
    if not t:
        return json.dumps({"error": "Falta texto de busqueda"})
    result = await db.execute(text("""
        SELECT p.nombre, p.ruc, p.telefono, p.email, p.activo,
               COALESCE(SUM(comp.saldo_pendiente) FILTER (WHERE comp.estado_validacion='confirmado'), 0) AS saldo,
               COUNT(comp.id) FILTER (WHERE comp.estado_validacion='confirmado') AS comprobantes
        FROM proveedores p
        LEFT JOIN comprobantes comp ON comp.proveedor_id = p.id AND comp.empresa_id = :e
        WHERE p.empresa_id = :e AND (p.nombre ILIKE :q OR p.ruc ILIKE :q)
        GROUP BY p.id, p.nombre, p.ruc, p.telefono, p.email, p.activo
        ORDER BY saldo DESC LIMIT 10
    """), {"e": empresa_id, "q": f"%{t}%"})
    rows = [dict(r) for r in result.mappings()]
    if not rows:
        return json.dumps({"proveedores": [], "mensaje": "Sin resultados"})
    for r in rows:
        r["saldo"] = _money(r["saldo"])
        r["comprobantes"] = int(r["comprobantes"] or 0)
    return json.dumps({"proveedores": rows})


async def _listar_clientes_top(args, empresa_id, rol, db):
    orden = args.get("orden", "facturado")
    direccion = (args.get("direccion") or "mayor").lower()  # 'mayor' o 'menor'
    solo_con_deuda = bool(args.get("solo_con_deuda", False))
    limite = min(int(args.get("limite") or 10), 50)
    col = "total_facturado" if orden == "facturado" else "saldo"
    sort = "ASC" if direccion == "menor" else "DESC"
    having = "HAVING COALESCE(SUM(comp.saldo_pendiente) FILTER (WHERE comp.estado_validacion='confirmado'), 0) > 0" if solo_con_deuda else ""
    result = await db.execute(text(f"""
        SELECT c.nombre, c.ruc,
               COALESCE(SUM(comp.monto_total) FILTER (WHERE comp.estado_validacion='confirmado'), 0) AS total_facturado,
               COALESCE(SUM(comp.saldo_pendiente) FILTER (WHERE comp.estado_validacion='confirmado'), 0) AS saldo
        FROM clientes c
        LEFT JOIN comprobantes comp ON comp.cliente_id = c.id AND comp.empresa_id = :e
        WHERE c.empresa_id = :e AND c.activo = TRUE
        GROUP BY c.id, c.nombre, c.ruc
        {having}
        ORDER BY {col} {sort} LIMIT :l
    """), {"e": empresa_id, "l": limite})
    rows = [dict(r) for r in result.mappings()]
    for r in rows:
        r["total_facturado"] = _money(r["total_facturado"])
        r["saldo"] = _money(r["saldo"])
    return json.dumps({"clientes": rows, "orden": orden, "direccion": direccion})


async def _listar_proveedores_top(args, empresa_id, rol, db):
    orden = args.get("orden", "comprado")
    direccion = (args.get("direccion") or "mayor").lower()  # 'mayor' o 'menor'
    solo_con_deuda = bool(args.get("solo_con_deuda", False))
    limite = min(int(args.get("limite") or 10), 50)
    col = "total_comprado" if orden == "comprado" else "saldo"
    sort = "ASC" if direccion == "menor" else "DESC"
    having = "HAVING COALESCE(SUM(comp.saldo_pendiente) FILTER (WHERE comp.estado_validacion='confirmado'), 0) > 0" if solo_con_deuda else ""
    result = await db.execute(text(f"""
        SELECT p.nombre, p.ruc,
               COALESCE(SUM(comp.monto_total) FILTER (WHERE comp.estado_validacion='confirmado'), 0) AS total_comprado,
               COALESCE(SUM(comp.saldo_pendiente) FILTER (WHERE comp.estado_validacion='confirmado'), 0) AS saldo
        FROM proveedores p
        LEFT JOIN comprobantes comp ON comp.proveedor_id = p.id AND comp.empresa_id = :e
        WHERE p.empresa_id = :e AND p.activo = TRUE
        GROUP BY p.id, p.nombre, p.ruc
        {having}
        ORDER BY {col} {sort} LIMIT :l
    """), {"e": empresa_id, "l": limite})
    rows = [dict(r) for r in result.mappings()]
    for r in rows:
        r["total_comprado"] = _money(r["total_comprado"])
        r["saldo"] = _money(r["saldo"])
    return json.dumps({"proveedores": rows, "orden": orden, "direccion": direccion})


async def _buscar_comprobante(args, empresa_id, rol, db):
    numero = (args.get("numero") or "").strip()
    if not numero:
        return json.dumps({"error": "Falta numero"})
    result = await db.execute(text("""
        SELECT comp.numero_comprobante, comp.fecha_emision, comp.fecha_vencimiento,
               comp.monto_total, comp.monto_iva, comp.saldo_pendiente,
               comp.estado_validacion, comp.condicion, comp.medio_pago_contado,
               comp.ubicacion_fisica,
               COALESCE(c.nombre, p.nombre) AS contraparte,
               CASE WHEN comp.cliente_id IS NOT NULL THEN 'venta' ELSE 'compra' END AS tipo
        FROM comprobantes comp
        LEFT JOIN clientes c ON c.id = comp.cliente_id
        LEFT JOIN proveedores p ON p.id = comp.proveedor_id
        WHERE comp.empresa_id = :e AND comp.numero_comprobante ILIKE :n
        ORDER BY comp.fecha_emision DESC LIMIT 5
    """), {"e": empresa_id, "n": f"%{numero}%"})
    rows = [dict(r) for r in result.mappings()]
    if not rows:
        return json.dumps({"comprobantes": [], "mensaje": "Sin resultados"})
    for r in rows:
        r["monto_total"] = _money(r["monto_total"])
        r["monto_iva"] = _money(r["monto_iva"])
        r["saldo_pendiente"] = _money(r["saldo_pendiente"])
        for k in ("fecha_emision", "fecha_vencimiento"):
            if r.get(k): r[k] = str(r[k])
    return json.dumps({"comprobantes": rows})


async def _listar_comprobantes_pendientes(args, empresa_id, rol, db):
    tipo = args.get("tipo", "todos")
    limite = min(int(args.get("limite") or 10), 50)
    filtro = {"cobrar": "AND comp.cliente_id IS NOT NULL",
              "pagar":  "AND comp.proveedor_id IS NOT NULL"}.get(tipo, "")
    result = await db.execute(text(f"""
        SELECT comp.numero_comprobante, comp.fecha_emision, comp.fecha_vencimiento,
               comp.monto_total, comp.saldo_pendiente,
               COALESCE(c.nombre, p.nombre) AS contraparte,
               CASE WHEN comp.cliente_id IS NOT NULL THEN 'cobrar' ELSE 'pagar' END AS tipo
        FROM comprobantes comp
        LEFT JOIN clientes c ON c.id = comp.cliente_id
        LEFT JOIN proveedores p ON p.id = comp.proveedor_id
        WHERE comp.empresa_id = :e AND comp.estado_validacion='confirmado'
          AND comp.saldo_pendiente > 0 {filtro}
        ORDER BY comp.saldo_pendiente DESC LIMIT :l
    """), {"e": empresa_id, "l": limite})
    rows = [dict(r) for r in result.mappings()]
    for r in rows:
        r["monto_total"] = _money(r["monto_total"])
        r["saldo_pendiente"] = _money(r["saldo_pendiente"])
        for k in ("fecha_emision", "fecha_vencimiento"):
            if r.get(k): r[k] = str(r[k])
    return json.dumps({"comprobantes": rows, "total": len(rows)})


async def _listar_comprobantes_vencidos(args, empresa_id, rol, db):
    tipo = args.get("tipo", "todos")
    limite = min(int(args.get("limite") or 10), 50)
    filtro = {"cobrar": "AND comp.cliente_id IS NOT NULL",
              "pagar":  "AND comp.proveedor_id IS NOT NULL"}.get(tipo, "")
    result = await db.execute(text(f"""
        SELECT comp.numero_comprobante, comp.fecha_emision, comp.fecha_vencimiento,
               comp.monto_total, comp.saldo_pendiente,
               (CURRENT_DATE - comp.fecha_vencimiento) AS dias_vencido,
               COALESCE(c.nombre, p.nombre) AS contraparte,
               CASE WHEN comp.cliente_id IS NOT NULL THEN 'cobrar' ELSE 'pagar' END AS tipo
        FROM comprobantes comp
        LEFT JOIN clientes c ON c.id = comp.cliente_id
        LEFT JOIN proveedores p ON p.id = comp.proveedor_id
        WHERE comp.empresa_id = :e AND comp.estado_validacion='confirmado'
          AND comp.saldo_pendiente > 0
          AND comp.condicion = 'credito'
          AND comp.fecha_vencimiento IS NOT NULL
          AND comp.fecha_vencimiento < CURRENT_DATE
          {filtro}
        ORDER BY comp.fecha_vencimiento ASC LIMIT :l
    """), {"e": empresa_id, "l": limite})
    rows = [dict(r) for r in result.mappings()]
    for r in rows:
        r["monto_total"] = _money(r["monto_total"])
        r["saldo_pendiente"] = _money(r["saldo_pendiente"])
        r["dias_vencido"] = int(r["dias_vencido"] or 0)
        for k in ("fecha_emision", "fecha_vencimiento"):
            if r.get(k): r[k] = str(r[k])
    return json.dumps({"vencidos": rows, "total": len(rows)})


async def _ultimos_comprobantes(args, empresa_id, rol, db):
    limite = min(int(args.get("limite") or 10), 50)
    tipo = args.get("tipo", "todos")
    filtro = {"venta":  "AND comp.cliente_id IS NOT NULL",
              "compra": "AND comp.proveedor_id IS NOT NULL"}.get(tipo, "")
    result = await db.execute(text(f"""
        SELECT comp.numero_comprobante, comp.fecha_emision, comp.monto_total,
               comp.saldo_pendiente, comp.estado_validacion, comp.condicion,
               COALESCE(c.nombre, p.nombre) AS contraparte,
               CASE WHEN comp.cliente_id IS NOT NULL THEN 'venta' ELSE 'compra' END AS tipo
        FROM comprobantes comp
        LEFT JOIN clientes c ON c.id = comp.cliente_id
        LEFT JOIN proveedores p ON p.id = comp.proveedor_id
        WHERE comp.empresa_id = :e {filtro}
        ORDER BY comp.fecha_emision DESC, comp.fecha_creacion DESC LIMIT :l
    """), {"e": empresa_id, "l": limite})
    rows = [dict(r) for r in result.mappings()]
    for r in rows:
        r["monto_total"] = _money(r["monto_total"])
        r["saldo_pendiente"] = _money(r["saldo_pendiente"])
        if r.get("fecha_emision"): r["fecha_emision"] = str(r["fecha_emision"])
    return json.dumps({"comprobantes": rows})


async def _detalle_comprobante(args, empresa_id, rol, db):
    numero = (args.get("numero") or "").strip()
    if not numero:
        return json.dumps({"error": "Falta numero"})
    comp = await db.execute(text("""
        SELECT id, numero_comprobante, monto_total, saldo_pendiente
        FROM comprobantes WHERE empresa_id = :e AND numero_comprobante = :n
        LIMIT 1
    """), {"e": empresa_id, "n": numero})
    c = comp.mappings().first()
    if not c:
        return json.dumps({"error": "Comprobante no encontrado"})
    items = await db.execute(text("""
        SELECT descripcion, cantidad, precio_unitario, subtotal, iva
        FROM detalle_comprobantes
        WHERE comprobante_id = :id
        ORDER BY id
    """), {"id": c["id"]})
    rows = [dict(r) for r in items.mappings()]
    for r in rows:
        for k in ("cantidad", "precio_unitario", "subtotal", "iva"):
            if k in r: r[k] = _money(r[k])
    return json.dumps({
        "numero": c["numero_comprobante"],
        "monto_total": _money(c["monto_total"]),
        "saldo_pendiente": _money(c["saldo_pendiente"]),
        "items": rows,
    })


async def _historial_contraparte(args, empresa_id, rol, db):
    tipo = args.get("tipo", "cliente")
    nombre = (args.get("nombre") or "").strip()
    tabla = "clientes" if tipo == "cliente" else "proveedores"
    fk = "cliente_id" if tipo == "cliente" else "proveedor_id"
    ent = await db.execute(text(f"""
        SELECT id, nombre, ruc FROM {tabla}
        WHERE empresa_id = :e AND (nombre ILIKE :q OR ruc ILIKE :q)
        ORDER BY nombre LIMIT 1
    """), {"e": empresa_id, "q": f"%{nombre}%"})
    e = ent.mappings().first()
    if not e:
        return json.dumps({"error": f"{tipo.capitalize()} no encontrado"})
    facturas = await db.execute(text(f"""
        SELECT numero_comprobante, fecha_emision, fecha_vencimiento,
               monto_total, saldo_pendiente, estado_validacion, condicion
        FROM comprobantes
        WHERE empresa_id = :e AND {fk} = :id
        ORDER BY fecha_emision DESC LIMIT 50
    """), {"e": empresa_id, "id": e["id"]})
    fact_rows = [dict(r) for r in facturas.mappings()]
    for r in fact_rows:
        r["monto_total"] = _money(r["monto_total"])
        r["saldo_pendiente"] = _money(r["saldo_pendiente"])
        for k in ("fecha_emision", "fecha_vencimiento"):
            if r.get(k): r[k] = str(r[k])
    pagos = await db.execute(text(f"""
        SELECT p.fecha_pago, p.monto_pagado, p.medio_pago, p.notas,
               comp.numero_comprobante
        FROM pagos p
        JOIN comprobantes comp ON comp.id = p.comprobante_id
        WHERE p.empresa_id = :e AND comp.{fk} = :id
        ORDER BY p.fecha_pago DESC LIMIT 50
    """), {"e": empresa_id, "id": e["id"]})
    pago_rows = [dict(r) for r in pagos.mappings()]
    for r in pago_rows:
        r["monto_pagado"] = _money(r["monto_pagado"])
        if r.get("fecha_pago"): r["fecha_pago"] = str(r["fecha_pago"])
    return json.dumps({
        "contraparte": {"nombre": e["nombre"], "ruc": e["ruc"]},
        "facturas": fact_rows,
        "pagos": pago_rows,
    })


async def _listar_pagos_recientes(args, empresa_id, rol, db):
    limite = min(int(args.get("limite") or 10), 50)
    tipo = args.get("tipo", "todos")
    filtro = ""
    if tipo == "cobros":
        filtro = "AND comp.cliente_id IS NOT NULL"
    elif tipo == "pagos":
        filtro = "AND comp.proveedor_id IS NOT NULL"
    result = await db.execute(text(f"""
        SELECT p.fecha_pago, p.monto_pagado, p.medio_pago, p.numero_recibo,
               comp.numero_comprobante,
               COALESCE(c.nombre, pr.nombre) AS contraparte,
               CASE WHEN comp.cliente_id IS NOT NULL THEN 'cobro' ELSE 'pago' END AS tipo
        FROM pagos p
        JOIN comprobantes comp ON comp.id = p.comprobante_id
        LEFT JOIN clientes c ON c.id = comp.cliente_id
        LEFT JOIN proveedores pr ON pr.id = comp.proveedor_id
        WHERE p.empresa_id = :e {filtro}
        ORDER BY p.fecha_pago DESC, p.fecha_creacion DESC LIMIT :l
    """), {"e": empresa_id, "l": limite})
    rows = [dict(r) for r in result.mappings()]
    for r in rows:
        r["monto_pagado"] = _money(r["monto_pagado"])
        if r.get("fecha_pago"): r["fecha_pago"] = str(r["fecha_pago"])
    return json.dumps({"pagos": rows})


async def _consultar_stock(args, empresa_id, rol, db):
    p = (args.get("producto") or "").strip()
    if not p:
        return json.dumps({"error": "Falta producto"})
    result = await db.execute(text("""
        SELECT i.descripcion, i.codigo, i.unidad_medida,
               i.cantidad_actual, i.punto_reorden, i.costo_unitario,
               cat.nombre AS categoria,
               CASE WHEN i.cantidad_actual <= i.punto_reorden THEN 'CRITICO' ELSE 'OK' END AS estado
        FROM inventario i
        LEFT JOIN categorias_inventario cat ON cat.id = i.categoria_id
        WHERE i.empresa_id = :e AND i.activo = TRUE
          AND (i.descripcion ILIKE :q OR i.codigo ILIKE :q)
        ORDER BY i.descripcion LIMIT 15
    """), {"e": empresa_id, "q": f"%{p}%"})
    rows = [dict(r) for r in result.mappings()]
    if not rows:
        return json.dumps({"productos": [], "mensaje": "Sin resultados"})
    for r in rows:
        r["cantidad_actual"] = _money(r["cantidad_actual"])
        r["punto_reorden"] = _money(r["punto_reorden"])
        r["costo_unitario"] = _money(r["costo_unitario"])
    return json.dumps({"productos": rows})


async def _items_stock_critico(args, empresa_id, rol, db):
    result = await db.execute(text("""
        SELECT i.descripcion, i.codigo, i.unidad_medida,
               i.cantidad_actual, i.punto_reorden,
               ROUND((i.cantidad_actual/NULLIF(i.punto_reorden,0)*100)::numeric,1) AS porcentaje
        FROM inventario i
        WHERE i.empresa_id = :e AND i.activo = TRUE
          AND i.punto_reorden > 0 AND i.cantidad_actual <= i.punto_reorden
        ORDER BY porcentaje ASC NULLS FIRST LIMIT 30
    """), {"e": empresa_id})
    rows = [dict(r) for r in result.mappings()]
    for r in rows:
        r["cantidad_actual"] = _money(r["cantidad_actual"])
        r["punto_reorden"] = _money(r["punto_reorden"])
        r["porcentaje"] = _money(r["porcentaje"])
    return json.dumps({"criticos": rows, "total": len(rows)})


async def _listar_inventario(args, empresa_id, rol, db):
    cat = (args.get("categoria") or "").strip()
    limite = min(int(args.get("limite") or 30), 100)
    if cat:
        result = await db.execute(text("""
            SELECT i.descripcion, i.codigo, i.cantidad_actual, i.punto_reorden,
                   i.unidad_medida, cat.nombre AS categoria
            FROM inventario i
            JOIN categorias_inventario cat ON cat.id = i.categoria_id
            WHERE i.empresa_id = :e AND i.activo = TRUE AND cat.nombre ILIKE :c
            ORDER BY i.descripcion LIMIT :l
        """), {"e": empresa_id, "c": f"%{cat}%", "l": limite})
    else:
        result = await db.execute(text("""
            SELECT i.descripcion, i.codigo, i.cantidad_actual, i.punto_reorden,
                   i.unidad_medida, cat.nombre AS categoria
            FROM inventario i
            LEFT JOIN categorias_inventario cat ON cat.id = i.categoria_id
            WHERE i.empresa_id = :e AND i.activo = TRUE
            ORDER BY i.descripcion LIMIT :l
        """), {"e": empresa_id, "l": limite})
    rows = [dict(r) for r in result.mappings()]
    for r in rows:
        r["cantidad_actual"] = _money(r["cantidad_actual"])
        r["punto_reorden"] = _money(r["punto_reorden"])
    return json.dumps({"productos": rows, "total": len(rows)})


async def _resumen_financiero(args, empresa_id, rol, db):
    kpis = await db.execute(text("""
        SELECT
            COUNT(*) FILTER (WHERE saldo_pendiente > 0 AND estado_validacion='confirmado') AS fact_pend,
            COALESCE(SUM(saldo_pendiente) FILTER (WHERE cliente_id IS NOT NULL AND estado_validacion='confirmado'),0) AS cobrar,
            COALESCE(SUM(saldo_pendiente) FILTER (WHERE proveedor_id IS NOT NULL AND estado_validacion='confirmado'),0) AS pagar,
            COUNT(*) FILTER (WHERE estado_validacion='pendiente_revision') AS pend_val
        FROM comprobantes WHERE empresa_id = :e
    """), {"e": empresa_id})
    k = dict(kpis.mappings().first() or {})
    stock = await db.execute(text("""
        SELECT COUNT(*) AS criticos FROM inventario
        WHERE empresa_id = :e AND activo=TRUE AND punto_reorden > 0 AND cantidad_actual <= punto_reorden
    """), {"e": empresa_id})
    s = dict(stock.mappings().first() or {})
    return json.dumps({
        "facturas_pendientes": int(k.get("fact_pend") or 0),
        "total_por_cobrar_gs": _money(k.get("cobrar")),
        "total_por_pagar_gs": _money(k.get("pagar")),
        "comprobantes_pendientes_validar": int(k.get("pend_val") or 0),
        "items_stock_critico": int(s.get("criticos") or 0),
    })


async def _flujo_mensual(args, empresa_id, rol, db):
    from datetime import date as _date, timedelta as _td
    meses = min(int(args.get("meses") or 6), 24)
    # Calcular rango en Python (cross-DB compatible)
    hoy = _date.today()
    anio, mes = hoy.year, hoy.month - (meses - 1)
    while mes <= 0:
        mes += 12; anio -= 1
    inicio = _date(anio, mes, 1)
    cy, cm = inicio.year, inicio.month
    rows = []
    for _ in range(meses):
        rows.append({"mes": f"{cy:04d}-{cm:02d}", "ingresos": 0, "egresos": 0})
        cm += 1
        if cm > 12: cm = 1; cy += 1
    fin = _date(cy, cm, 1)
    result = await db.execute(text("""
        SELECT substr(CAST(fecha_emision AS TEXT), 1, 7) AS mes,
               COALESCE(SUM(CASE WHEN cliente_id   IS NOT NULL THEN monto_total ELSE 0 END), 0) AS ingresos,
               COALESCE(SUM(CASE WHEN proveedor_id IS NOT NULL THEN monto_total ELSE 0 END), 0) AS egresos
        FROM comprobantes
        WHERE empresa_id = :e
          AND estado_validacion = 'confirmado'
          AND fecha_emision >= :desde AND fecha_emision < :fin
        GROUP BY substr(CAST(fecha_emision AS TEXT), 1, 7)
    """), {"e": empresa_id, "desde": inicio.isoformat(), "fin": fin.isoformat()})
    by_mes = {r["mes"]: r for r in result.mappings()}
    for r in rows:
        if r["mes"] in by_mes:
            r["ingresos"] = _money(by_mes[r["mes"]]["ingresos"])
            r["egresos"]  = _money(by_mes[r["mes"]]["egresos"])
        else:
            r["ingresos"] = _money(0); r["egresos"] = _money(0)
        r["flujo_neto"] = r["ingresos"] - r["egresos"]
    return json.dumps({"flujo": rows})


async def _distribucion_medios_pago(args, empresa_id, rol, db):
    result = await db.execute(text("""
        SELECT medio_pago, COUNT(*) AS cantidad, COALESCE(SUM(monto_pagado),0) AS total
        FROM pagos
        WHERE empresa_id = :e AND fecha_pago >= CURRENT_DATE - INTERVAL '90 days'
        GROUP BY medio_pago
        ORDER BY total DESC
    """), {"e": empresa_id})
    rows = [dict(r) for r in result.mappings()]
    for r in rows:
        r["total"] = _money(r["total"])
        r["cantidad"] = int(r["cantidad"])
    return json.dumps({"medios_pago": rows})


async def _info_empresa(args, empresa_id, rol, db):
    result = await db.execute(text("""
        SELECT nombre, ruc, direccion, telefono, email, moneda_principal
        FROM empresas WHERE id = :e
    """), {"e": empresa_id})
    row = result.mappings().first()
    return json.dumps({"empresa": dict(row) if row else {}})


async def _listar_usuarios(args, empresa_id, rol, db):
    if rol != "admin":
        return json.dumps({"error": "Solo disponible para administradores"})
    result = await db.execute(text("""
        SELECT u.nombre, u.email, u.telefono, u.cargo, u.activo, r.nombre AS rol
        FROM usuarios u
        JOIN roles_usuario r ON r.id = u.id_rol
        WHERE u.empresa_id = :e
        ORDER BY u.nombre
    """), {"e": empresa_id})
    return json.dumps({"usuarios": [dict(r) for r in result.mappings()]})


# ── Acciones de escritura: cobros y pagos ────────────────────────────────────


_AYUDA_TEMAS = {
    "factura": (
        "Para cargar una factura: Inicio > 'Cargar factura' (foto o Excel) o "
        "'Factura manual' si no hay imagen. Tambien podes subir una foto desde "
        "Carga IA. Toda factura queda en Comprobantes."
    ),
    "cobro": (
        "Cobros de clientes: desde Movimientos boton 'Cargar cobro' o desde la "
        "fila de la factura en Comprobantes (icono billetera). Tambien podes "
        "pedirmelo en lenguaje natural: 'cobra G. 500.000 de la factura 001-001-...'."
    ),
    "pago": (
        "Pagos a proveedores: desde Movimientos boton 'Cargar pago' o desde la "
        "fila de la factura de compra en Comprobantes. Yo tambien lo registro: "
        "deci 'paga G. 300.000 al proveedor X factura 001-...'."
    ),
    "ocr": (
        "OCR: subi una foto o PDF de la factura desde Carga IA y el sistema "
        "extrae los datos con Gemini Vision. Reviza y confirma para guardar."
    ),
    "excel": (
        "Plantilla Excel: en Carga IA boton 'Descargar modelo'. Completa la "
        "hoja Facturas y subila para importar varias facturas a la vez."
    ),
    "iva": (
        "Resumen IVA: menu Reportes > IVA. Suma simple del IVA de ventas y "
        "compras del periodo, con desglose 10%/5%."
    ),
    "clientes": "Clientes: ABM en Clientes. Cada cliente tiene saldo pendiente y comprobantes asociados.",
    "proveedores": "Proveedores: ABM en Proveedores. Mismo formato que clientes.",
    "inventario": "Inventario: productos con stock actual y punto de reorden. Carga IA tambien usa inventario.",
    "asistente": (
        "Asistente IA: yo, disponible siempre desde el boton flotante o "
        "Atajo Ctrl+/. Puedo consultar saldos, listar facturas, registrar "
        "cobros y pagos."
    ),
    "atajos": (
        "Atajos: Ctrl+/ abre el asistente desde cualquier pantalla. Enter "
        "envia mensaje, Shift+Enter agrega linea."
    ),
}


async def _ayuda_sistema(args, empresa_id, rol, db):
    tema = (args.get("tema") or "").strip().lower()
    if tema and tema in _AYUDA_TEMAS:
        return json.dumps({"tema": tema, "respuesta": _AYUDA_TEMAS[tema]})
    return json.dumps({
        "respuesta": (
            "Sistema ERP simplificado para micro y medianas empresas paraguayas. "
            "Modulos disponibles: Inicio (dashboard), Facturas/Comprobantes, "
            "Carga IA (OCR + Excel), Cuentas por cobrar/pagar, Movimientos "
            "(cobros y pagos), IVA simple, Clientes, Proveedores, Inventario, "
            "Asistente, Actividad y Administracion. Yo puedo registrar cobros "
            "y pagos por chat, consultar saldos, listar pendientes y vencidos. "
            "Atajo Ctrl+/ abre este asistente."
        ),
        "temas_disponibles": list(_AYUDA_TEMAS.keys()),
    })


async def _registrar_pago_chatbot(args, empresa_id, rol, db, *, es_venta: bool):
    """Implementacion comun: valida y devuelve preview confirmable."""
    from decimal import Decimal as _D, InvalidOperation
    from datetime import date as _date

    if rol == "viewer":
        return json.dumps({"error": "Tu rol no permite registrar movimientos. Pedi a un admin u operador."})
    usuario_id = args.get("__usuario_id__")
    if not usuario_id:
        return json.dumps({"error": "No se pudo identificar el usuario para confirmar la accion."})

    factura_numero = (args.get("factura_numero") or "").strip()
    if not factura_numero:
        return json.dumps({"error": "Falta el numero de factura."})

    medio_pago = (args.get("medio_pago") or "").strip().lower()
    if medio_pago not in {"efectivo", "transferencia", "cheque", "tarjeta", "otro"}:
        return json.dumps({"error": "Medio de pago invalido. Usa efectivo, transferencia, cheque, tarjeta u otro."})

    try:
        monto = _D(str(args.get("monto")))
    except (InvalidOperation, TypeError):
        return json.dumps({"error": "Monto invalido."})
    if monto <= 0:
        return json.dumps({"error": "El monto debe ser mayor a cero."})

    fecha_str = (args.get("fecha") or "").strip()
    if fecha_str:
        try:
            fecha = _date.fromisoformat(fecha_str)
        except ValueError:
            return json.dumps({"error": "Fecha invalida (usa YYYY-MM-DD)."})
    else:
        fecha = _date.today()

    contraparte_texto = args.get("cliente_texto") if es_venta else args.get("proveedor_texto")

    from .pagos_service import resolver_comprobante_pendiente

    candidatos = await resolver_comprobante_pendiente(
        db=db,
        empresa_id=empresa_id,
        factura_numero=factura_numero,
        contraparte_texto=contraparte_texto,
        es_venta=es_venta,
    )
    if not candidatos:
        tipo = "venta" if es_venta else "compra"
        return json.dumps({
            "error": f"No encontre ninguna factura de {tipo} pendiente que coincida con '{factura_numero}'.",
        })
    if len(candidatos) > 1:
        return json.dumps({
            "ambiguo": True,
            "mensaje": "Hay varias facturas pendientes que coinciden, indica cual:",
            "candidatos": [
                {
                    "numero": c["numero_comprobante"],
                    "contraparte": c["contraparte"],
                    "fecha": str(c["fecha_emision"]),
                    "saldo": float(c["saldo_pendiente"]),
                }
                for c in candidatos
            ],
        })

    factura = candidatos[0]
    saldo = _D(str(factura["saldo_pendiente"]))
    if monto > saldo:
        formateado = f"{saldo:,.0f}".replace(",", ".")
        return json.dumps({"error": f"El monto supera el saldo pendiente (G. {formateado}). Ajusta el monto."})

    payload = {
        "comprobante_id": str(factura["id"]),
        "factura_numero": factura["numero_comprobante"],
        "contraparte": factura["contraparte"],
        "monto_pagado": str(monto),
        "medio_pago": medio_pago,
        "fecha_pago": fecha.isoformat(),
        "numero_recibo": args.get("numero_recibo"),
        "notas": args.get("notas"),
        "es_venta": es_venta,
    }
    tipo = "cobro" if es_venta else "pago"
    preview = await _crear_preview_accion(
        db,
        empresa_id=empresa_id,
        usuario_id=usuario_id,
        accion="registrar_cobro" if es_venta else "registrar_pago",
        payload=payload,
        resumen=f"Registrar {tipo} de G. {int(monto):,}".replace(",", "."),
        impacto=f"Factura {factura['numero_comprobante']} - {factura['contraparte']} - saldo actual G. {int(saldo):,}".replace(",", "."),
        riesgo="dinero",
    )

    return json.dumps({
        **preview,
        "tipo": tipo,
        "factura_numero": factura["numero_comprobante"],
        "contraparte": factura["contraparte"],
        "monto": float(monto),
        "medio_pago": medio_pago,
        "fecha": fecha.isoformat(),
        "mensaje": "Revise el preview y confirme para ejecutar la accion.",
    })


async def _registrar_cobro(args, empresa_id, rol, db):
    return await _registrar_pago_chatbot(args, empresa_id, rol, db, es_venta=True)


async def _registrar_pago(args, empresa_id, rol, db):
    return await _registrar_pago_chatbot(args, empresa_id, rol, db, es_venta=False)


async def confirmar_accion_chatbot(
    *,
    action_token: str,
    empresa_id: str,
    usuario_id: str,
    rol: str,
    db: AsyncSession,
) -> dict:
    """Ejecuta una accion previamente validada por preview."""
    token_data = await consumir_action_token(
        db,
        token=action_token,
        empresa_id=empresa_id,
        usuario_id=usuario_id,
    )
    accion = token_data["accion"]
    payload = token_data["payload"]

    if accion in {"registrar_cobro", "registrar_pago"}:
        if rol == "viewer":
            raise HTTPException(status_code=403, detail="Tu rol no permite registrar movimientos")
        from datetime import date as _date
        from decimal import Decimal as _D
        from .pagos_service import RegistrarPagoError, registrar_pago_core

        try:
            resultado = await registrar_pago_core(
                db=db,
                empresa_id=empresa_id,
                usuario={"sub": usuario_id, "empresa_id": empresa_id, "rol": rol},
                comprobante_id=payload["comprobante_id"],
                monto_pagado=_D(str(payload["monto_pagado"])),
                medio_pago=payload["medio_pago"],
                fecha_pago=_date.fromisoformat(payload["fecha_pago"]),
                numero_recibo=payload.get("numero_recibo"),
                notas=payload.get("notas"),
                commit=False,
                audit_origen="chatbot",
            )
        except RegistrarPagoError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.detail)

        await db.commit()
        return {
            "ok": True,
            "accion": accion,
            "resultado": {
                "pago_id": str(resultado["id"]),
                "factura_numero": resultado["numero_comprobante"],
                "contraparte": resultado["contraparte"],
                "monto": float(resultado["monto_pagado"]),
                "medio_pago": resultado["medio_pago"],
                "saldo_restante": resultado["saldo_restante"],
                "totalmente_cancelado": resultado["totalmente_cancelado"],
            },
            "mensaje": "Accion ejecutada",
        }

    raise HTTPException(status_code=400, detail=f"Accion no soportada: {accion}")


FUNCIONES = {
    "buscar_cliente": _buscar_cliente,
    "buscar_proveedor": _buscar_proveedor,
    "listar_clientes_top": _listar_clientes_top,
    "listar_proveedores_top": _listar_proveedores_top,
    "buscar_comprobante": _buscar_comprobante,
    "listar_comprobantes_pendientes": _listar_comprobantes_pendientes,
    "listar_comprobantes_vencidos": _listar_comprobantes_vencidos,
    "ultimos_comprobantes": _ultimos_comprobantes,
    "detalle_comprobante": _detalle_comprobante,
    "historial_contraparte": _historial_contraparte,
    "listar_pagos_recientes": _listar_pagos_recientes,
    "consultar_stock": _consultar_stock,
    "items_stock_critico": _items_stock_critico,
    "listar_inventario": _listar_inventario,
    "resumen_financiero": _resumen_financiero,
    "flujo_mensual": _flujo_mensual,
    "distribucion_medios_pago": _distribucion_medios_pago,
    "info_empresa": _info_empresa,
    "listar_usuarios": _listar_usuarios,
    "registrar_cobro": _registrar_cobro,
    "registrar_pago": _registrar_pago,
    "ayuda_sistema": _ayuda_sistema,
}


# ── Motor principal ───────────────────────────────────────────────────────────

async def chat(
    mensaje: str,
    historial: list[dict],
    empresa_id: str,
    db: AsyncSession,
    rol: str = "operador",
    usuario_id: str = "",
    forzar_gemini: bool = True,  # compat
) -> dict:
    """Procesa un mensaje del usuario con Gemini 2.5 Flash + function calling."""
    acciones: list = []

    api_key = key_store.get_key()
    if not api_key:
        return {
            "respuesta": (
                "El asistente IA no esta disponible: falta configurar la clave de Gemini. "
                "Ingresa a Configuracion y guardala."
            ),
            "acciones": [],
            "motor_usado": "sin_ia",
        }

    mensajes = list(historial[-10:])
    mensajes.append({"role": "user", "content": mensaje})

    try:
        resultado = await _chat_gemini(mensajes, empresa_id, rol, usuario_id, db, acciones, api_key)
        return {**resultado, "acciones": acciones, "motor_usado": "gemini"}
    except httpx.HTTPStatusError as e:
        return {"respuesta": f"El asistente no pudo responder (HTTP {e.response.status_code}).",
                "acciones": acciones, "motor_usado": "error"}
    except Exception as e:
        return {"respuesta": f"El asistente no esta disponible: {type(e).__name__}.",
                "acciones": acciones, "motor_usado": "error"}


async def _chat_gemini(
    mensajes: list[dict],
    empresa_id: str,
    rol: str,
    usuario_id: str,
    db: AsyncSession,
    acciones: list,
    api_key: str,
) -> dict:
    contents = []
    for msg in mensajes:
        if msg.get("role") == "system":
            continue
        role = "user" if msg.get("role") == "user" else "model"
        contents.append({"role": role, "parts": [{"text": msg.get("content", "")}]})

    gemini_tools = [{
        "function_declarations": [
            {"name": t["name"], "description": t["description"], "parameters": t["parameters"]}
            for t in TOOLS
        ]
    }]

    url = f"{GEMINI_URL}?key={api_key}"

    # Maximo 8 iteraciones de function-calling para flujos con preview.
    for _ in range(8):
        payload = {
            "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": contents,
            "tools": gemini_tools,
            "generationConfig": {
                "temperature": 0.1,
                "topP": 0.8,
                "maxOutputTokens": 1024,
            },
            "safetySettings": [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ],
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()

        cands = data.get("candidates") or []
        if not cands:
            return {"respuesta": OFF_TOPIC}
        candidate = cands[0].get("content") or {}
        parts = candidate.get("parts", [])

        fn_calls = [p for p in parts if "functionCall" in p]
        if not fn_calls:
            texto = " ".join(p.get("text", "") for p in parts if "text" in p).strip()
            return {"respuesta": texto or OFF_TOPIC}

        contents.append({"role": "model", "parts": parts})
        fn_responses = []
        for part in fn_calls:
            fn = part["functionCall"]
            fn_name = fn.get("name", "")
            fn_args = dict(fn.get("args", {}) or {})
            if fn_name in ("registrar_cobro", "registrar_pago"):
                fn_args["__usuario_id__"] = usuario_id
            resultado_str = await _ejecutar_funcion(fn_name, fn_args, empresa_id, rol, db)
            try:
                resultado_obj = json.loads(resultado_str)
            except Exception:
                resultado_obj = {"raw": resultado_str}
            acciones.append({"funcion": fn_name, "argumentos": fn_args, "resultado": resultado_obj})
            fn_responses.append({
                "functionResponse": {
                    "name": fn_name,
                    "response": {"content": resultado_str},
                }
            })
        contents.append({"role": "user", "parts": fn_responses})

    return {"respuesta": OFF_TOPIC}


GEMINI_STREAM_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:streamGenerateContent"
)


async def chat_stream(
    mensaje: str,
    historial: list[dict],
    empresa_id: str,
    db: AsyncSession,
    rol: str = "operador",
    usuario_id: str = "",
):
    """Async generator que produce eventos JSON para SSE.

    Eventos:
        {"type": "token", "text": "..."}            # chunk de texto del modelo
        {"type": "accion", "accion": {...}}         # function call ejecutada
        {"type": "done", "acciones": [...]}         # fin exitoso
        {"type": "error", "message": "..."}         # error
    """
    api_key = key_store.get_key()
    if not api_key:
        yield {"type": "error",
               "message": "El asistente IA no esta disponible: falta configurar la clave de Gemini."}
        return

    acciones: list = []
    mensajes = list(historial[-10:]) + [{"role": "user", "content": mensaje}]

    contents = []
    for msg in mensajes:
        if msg.get("role") == "system":
            continue
        role = "user" if msg.get("role") == "user" else "model"
        contents.append({"role": role, "parts": [{"text": msg.get("content", "")}]})

    gemini_tools = [{
        "function_declarations": [
            {"name": t["name"], "description": t["description"], "parameters": t["parameters"]}
            for t in TOOLS
        ]
    }]

    url = f"{GEMINI_STREAM_URL}?alt=sse&key={api_key}"

    try:
        for _ in range(8):
            payload = {
                "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
                "contents": contents,
                "tools": gemini_tools,
                "generationConfig": {
                    "temperature": 0.1,
                    "topP": 0.8,
                    "maxOutputTokens": 1024,
                },
                "safetySettings": [
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                ],
            }

            fn_calls: list[dict] = []
            text_emitted = False
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream("POST", url, json=payload) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if not line or not line.startswith("data:"):
                            continue
                        raw = line[5:].strip()
                        if not raw or raw == "[DONE]":
                            continue
                        try:
                            chunk = json.loads(raw)
                        except Exception:
                            continue
                        cands = chunk.get("candidates") or []
                        if not cands:
                            continue
                        parts = (cands[0].get("content") or {}).get("parts", []) or []
                        for part in parts:
                            if "text" in part:
                                txt = part.get("text") or ""
                                if txt:
                                    text_emitted = True
                                    yield {"type": "token", "text": txt}
                            elif "functionCall" in part:
                                fn_calls.append(part["functionCall"])

            if not fn_calls:
                # Si la iteracion no produjo ni texto ni function calls, mensaje generico
                if not text_emitted:
                    yield {"type": "token", "text": OFF_TOPIC}
                yield {"type": "done", "acciones": acciones}
                return

            # Ejecutar function calls y agregar al contexto para la proxima iteracion
            contents.append({"role": "model", "parts": [{"functionCall": fc} for fc in fn_calls]})
            fn_responses = []
            for fc in fn_calls:
                fn_name = fc.get("name", "")
                fn_args = dict(fc.get("args", {}) or {})
                if fn_name in ("registrar_cobro", "registrar_pago"):
                    fn_args["__usuario_id__"] = usuario_id
                resultado_str = await _ejecutar_funcion(fn_name, fn_args, empresa_id, rol, db)
                try:
                    resultado_obj = json.loads(resultado_str)
                except Exception:
                    resultado_obj = {"raw": resultado_str}
                accion = {"funcion": fn_name, "argumentos": fn_args, "resultado": resultado_obj}
                acciones.append(accion)
                yield {"type": "accion", "accion": accion}
                fn_responses.append({
                    "functionResponse": {
                        "name": fn_name,
                        "response": {"content": resultado_str},
                    }
                })
            contents.append({"role": "user", "parts": fn_responses})

        # Agotamos las 8 iteraciones sin respuesta final
        yield {"type": "token", "text": OFF_TOPIC}
        yield {"type": "done", "acciones": acciones}

    except httpx.HTTPStatusError as e:
        yield {"type": "error",
               "message": f"El asistente no pudo responder (HTTP {e.response.status_code})."}
    except Exception as e:
        yield {"type": "error", "message": f"El asistente no esta disponible: {type(e).__name__}."}


async def verificar_estado() -> dict:
    key = key_store.get_key()
    return {
        "motor": GEMINI_MODEL,
        "gemini_configurado": bool(key),
        "gemini_configurado_en_env": bool(settings.GEMINI_API_KEY),
        "herramientas": len(TOOLS),
    }
