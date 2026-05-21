"""
Tests de guardrails del chatbot.

Se enfocan en que las reglas anti-divague NO se rompan por cambios accidentales:
1. Sin clave de Gemini: no intenta conectar, responde sin_ia.
2. Fuera de alcance (Gemini responde texto sin tool call): se propaga el texto
   (y si el modelo sigue el prompt, sera la frase OFF_TOPIC).
3. Respuesta vacia de Gemini: devuelve OFF_TOPIC, no string vacio.
4. Error HTTP: responde error generico, no filtra stack trace.
5. Multi-tenant: todas las queries reciben empresa_id.
6. Rol operador NO puede listar_usuarios (chequeo en el ejecutor, no en el prompt).
7. Tool desconocida: error controlado.
8. Cada TOOL declarada tiene un ejecutor en FUNCIONES.
9. SYSTEM_PROMPT contiene las frases clave (no se diluyo por edicion).
10. Errores de tool no filtran detalles tecnicos.
"""
from __future__ import annotations
import json

import pytest

from backend.services import chatbot as svc
from tests.conftest import gemini_text_response, gemini_function_call

pytestmark = pytest.mark.anyio


# ───────────────────────────────────────── 1. Sin API key ──

async def test_sin_api_key_retorna_sin_ia(monkeypatch, db):
    from backend.core import key_store
    monkeypatch.setattr(key_store, "get_key", lambda: None)
    result = await svc.chat("hola", [], "e1", db, rol="admin")
    assert result["motor_usado"] == "sin_ia"
    assert "Configuracion" in result["respuesta"] or "Gemini" in result["respuesta"]
    # No debe haber ejecutado queries
    assert db.calls == []


# ───────────────────────────────────────── 2. Respuesta off-topic pasa tal cual ──

async def test_respuesta_sin_tool_call_se_propaga(fake_httpx, db):
    fake_httpx.queue(gemini_text_response(svc.OFF_TOPIC))
    result = await svc.chat("cual es la capital de francia?", [], "e1", db, rol="admin")
    assert result["respuesta"] == svc.OFF_TOPIC
    assert result["motor_usado"] == "gemini"
    assert result["acciones"] == []


# ───────────────────────────────────────── 3. Respuesta vacia ──

async def test_respuesta_vacia_retorna_off_topic(fake_httpx, db):
    fake_httpx.queue({"candidates": []})
    result = await svc.chat("???", [], "e1", db, rol="admin")
    assert result["respuesta"] == svc.OFF_TOPIC


async def test_parts_sin_texto_retorna_off_topic(fake_httpx, db):
    fake_httpx.queue({"candidates": [{"content": {"parts": []}}]})
    result = await svc.chat("???", [], "e1", db, rol="admin")
    assert result["respuesta"] == svc.OFF_TOPIC


# ───────────────────────────────────────── 4. Error HTTP no filtra stack ──

async def test_error_http_mensaje_controlado(monkeypatch, db):
    import httpx
    class BoomClient:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def post(self, *a, **kw):
            class R:
                status_code = 503
                def raise_for_status(self):
                    raise httpx.HTTPStatusError("boom", request=None, response=self)  # type: ignore
                def json(self): return {}
            return R()
    monkeypatch.setattr(httpx, "AsyncClient", lambda *a, **kw: BoomClient())

    result = await svc.chat("saldo de acme", [], "e1", db, rol="admin")
    assert result["motor_usado"] == "error"
    assert "503" in result["respuesta"]
    assert "Traceback" not in result["respuesta"]
    assert "httpx" not in result["respuesta"]


# ───────────────────────────────────────── 5. Multi-tenant ──

async def test_empresa_id_se_pasa_en_todas_las_queries(db):
    db.stub([{"nombre": "ACME", "ruc": "123", "telefono": None, "email": None,
              "activo": True, "saldo": 0, "comprobantes": 0}])
    await svc._buscar_cliente({"texto": "acme"}, "EMPRESA_X", "admin", db)
    assert db.calls[0]["params"]["e"] == "EMPRESA_X"


async def test_todos_los_ejecutores_filtran_por_empresa(db):
    # Tools simples sin args requeridos que podemos llamar
    casos = [
        (svc._resumen_financiero, {}),
        (svc._items_stock_critico, {}),
        (svc._listar_inventario, {}),
        (svc._info_empresa, {}),
        (svc._flujo_mensual, {}),
        (svc._distribucion_medios_pago, {}),
    ]
    for fn, args in casos:
        db.calls.clear()
        db.stub([])
        db.stub([])  # algunos hacen 2 queries
        await fn(args, "EMPRESA_Y", "admin", db)
        # cada query debe incluir "e": "EMPRESA_Y"
        for c in db.calls:
            assert c["params"].get("e") == "EMPRESA_Y", (fn.__name__, c["params"])


# ───────────────────────────────────────── 6. listar_usuarios requiere admin ──

async def test_operador_no_puede_listar_usuarios(db):
    resultado_str = await svc._listar_usuarios({}, "e1", "operador", db)
    data = json.loads(resultado_str)
    assert "error" in data
    assert "admin" in data["error"].lower()
    # Crucial: NO debe haber ejecutado la query
    assert db.calls == []


async def test_viewer_tampoco_puede_listar_usuarios(db):
    resultado_str = await svc._listar_usuarios({}, "e1", "viewer", db)
    data = json.loads(resultado_str)
    assert "error" in data
    assert db.calls == []


async def test_admin_si_puede_listar_usuarios(db):
    db.stub([{"nombre": "Admin", "email": "a@b.com", "telefono": None,
              "cargo": None, "activo": True, "rol": "admin"}])
    resultado_str = await svc._listar_usuarios({}, "e1", "admin", db)
    data = json.loads(resultado_str)
    assert "usuarios" in data
    assert len(data["usuarios"]) == 1


# ───────────────────────────────────────── 7. Tool desconocida ──

async def test_tool_desconocida_retorna_error_controlado(db):
    resultado_str = await svc._ejecutar_funcion("funcion_inexistente", {}, "e1", "admin", db)
    data = json.loads(resultado_str)
    assert "error" in data
    assert "no disponible" in data["error"].lower()


# ───────────────────────────────────────── 8. Integridad TOOLS <-> FUNCIONES ──

def test_toda_tool_declarada_tiene_ejecutor():
    nombres_tools = {t["name"] for t in svc.TOOLS}
    nombres_ejecutores = set(svc.FUNCIONES.keys())
    faltantes = nombres_tools - nombres_ejecutores
    assert not faltantes, f"Tools sin ejecutor: {faltantes}"


def test_no_hay_ejecutores_huerfanos():
    nombres_tools = {t["name"] for t in svc.TOOLS}
    nombres_ejecutores = set(svc.FUNCIONES.keys())
    huerfanos = nombres_ejecutores - nombres_tools
    assert not huerfanos, f"Ejecutores sin tool declarada: {huerfanos}"


# ───────────────────────────────────────── 9. System prompt preserva reglas ──

def test_prompt_contiene_reglas_clave():
    p = svc.SYSTEM_PROMPT.lower()
    # Invariantes semanticas (sin frases literales rigidas, para no chocar
    # cuando el prompt se reformula a un tono mas conversacional).
    checks = [
        ("no inventar datos",              ["no inventes", "no inventas"]),
        ("tools obligatorias para datos",  ["tool", "tools"]),
        ("no exponer jerga tecnica",       ["lenguaje de negocio", "no menciones", "nunca menciones"]),
        ("cobros/pagos con confirmacion",  ["requiere_confirmacion", "registrar_cobro", "registrar_pago"]),
        ("alcance limitado al ERP",        ["alcance", "fuera del erp", "datos de su empresa", "datos de la empresa"]),
    ]
    for descripcion, alternativas in checks:
        assert any(alt.lower() in p for alt in alternativas), (
            f"Falta la regla critica: {descripcion} (al menos una de {alternativas})"
        )


def test_off_topic_redirige_sin_sonar_robotico():
    # OFF_TOPIC se usa como fallback. Mantenemos su intencion (decirle al
    # usuario que reformule) pero sin atarlo a una frase exacta.
    txt = svc.OFF_TOPIC.lower()
    # Debe contener una redireccion util, no ser solo "no puedo".
    assert any(k in txt for k in ["probá", "proba", "preguntá", "pregunta", "intentá", "intenta"]), (
        "OFF_TOPIC debe sugerir como reformular, no solo negarse."
    )
    # Debe mencionar al menos una capacidad real para guiar al usuario.
    assert any(k in txt for k in ["saldo", "factura", "cobro", "pago", "stock", "cliente"]), (
        "OFF_TOPIC debe mencionar al menos una capacidad concreta del ERP."
    )


# ───────────────────────────────────────── 10. Errores de tool no filtran detalles ──

async def test_error_en_ejecutor_no_filtra_traceback(db):
    # Simulamos que db.execute explota con algo muy tecnico
    class BoomDB:
        async def execute(self, *a, **kw):
            raise RuntimeError("asyncpg.exceptions.UniqueViolationError: detalle SQL expuesto")
    resultado_str = await svc._ejecutar_funcion(
        "buscar_cliente", {"texto": "x"}, "e1", "admin", BoomDB()
    )
    data = json.loads(resultado_str)
    assert "error" in data
    # El mensaje debe ser generico, no el texto completo de la excepcion
    assert "asyncpg" not in data["error"]
    assert "UniqueViolation" not in data["error"]
    assert "detalle SQL expuesto" not in data["error"]
    # Pero si el tipo de excepcion (eso esta OK, ayuda a debugging sin filtrar data)
    assert "RuntimeError" in data["error"] or "Error interno" in data["error"]


# ───────────────────────────────────────── 11. Input vacio / invalido ──

async def test_buscar_cliente_sin_texto(db):
    resultado_str = await svc._buscar_cliente({}, "e1", "admin", db)
    data = json.loads(resultado_str)
    assert "error" in data
    # No debe hacer query con wildcard global
    assert db.calls == []


async def test_buscar_cliente_texto_vacio(db):
    resultado_str = await svc._buscar_cliente({"texto": "   "}, "e1", "admin", db)
    data = json.loads(resultado_str)
    assert "error" in data
    assert db.calls == []


# ───────────────────────────────────────── 12. Limits capeados ──

async def test_listar_clientes_top_limite_capeado_a_50(db):
    db.stub([])
    await svc._listar_clientes_top({"orden": "facturado", "limite": 9999}, "e1", "admin", db)
    assert db.calls[0]["params"]["l"] == 50


async def test_listar_inventario_limite_capeado_a_100(db):
    db.stub([])
    await svc._listar_inventario({"limite": 99999}, "e1", "admin", db)
    assert db.calls[0]["params"]["l"] == 100


# ───────────────────────────────────────── 13. Function calling flow ──

async def test_function_call_loop_ejecuta_tool_y_devuelve_texto(fake_httpx, db):
    # Primera respuesta: function call a buscar_cliente
    # Segunda respuesta: texto final con la info
    fake_httpx.queue(gemini_function_call("buscar_cliente", {"texto": "acme"}))
    fake_httpx.queue(gemini_text_response("ACME tiene saldo G. 500.000."))
    db.stub([{"nombre": "ACME", "ruc": "123", "telefono": None, "email": None,
              "activo": True, "saldo": 500000, "comprobantes": 2}])

    result = await svc.chat("saldo de acme", [], "e1", db, rol="admin")
    assert result["motor_usado"] == "gemini"
    assert "ACME" in result["respuesta"]
    assert len(result["acciones"]) == 1
    assert result["acciones"][0]["funcion"] == "buscar_cliente"


async def test_loop_maximo_8_iteraciones(fake_httpx, db):
    # Si Gemini insiste en function call infinitamente, debe cortar en OFF_TOPIC
    for _ in range(10):
        fake_httpx.queue(gemini_function_call("buscar_cliente", {"texto": "x"}))
        db.stub([])
    result = await svc.chat("loop", [], "e1", db, rol="admin")
    assert result["respuesta"] == svc.OFF_TOPIC
    # Se debe haber cortado en 8 iteraciones max
    assert len(result["acciones"]) <= 8
