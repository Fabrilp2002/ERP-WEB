"""
Fixtures para los tests del chatbot.

No requieren DB real ni conexion a Gemini — todo se mockea para que los tests
corran rapido y sin creds.
"""
from __future__ import annotations
import json
import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-for-pytest")


# Asegurar que el paquete `backend` sea importable cuando corremos pytest desde la raiz
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class FakeMappings:
    def __init__(self, rows):
        self._rows = rows

    def __iter__(self):
        return iter(self._rows)

    def first(self):
        return self._rows[0] if self._rows else None

    def all(self):
        return list(self._rows)


class FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def mappings(self):
        return FakeMappings(self._rows)


class FakeDB:
    """
    DB stub que guarda las queries ejecutadas y devuelve rows programaticamente.
    Uso:
        db = FakeDB()
        db.stub([{"nombre": "ACME", "saldo": 0}])
        await svc._buscar_cliente({"texto": "acme"}, "e1", "admin", db)
        assert "e1" in db.calls[0]["params"].values()
    """
    def __init__(self):
        self.calls: list[dict] = []
        self._queue: list[list[dict]] = []

    def stub(self, rows: list[dict]):
        self._queue.append(rows)

    async def execute(self, stmt, params=None):
        self.calls.append({"sql": str(stmt), "params": params or {}})
        rows = self._queue.pop(0) if self._queue else []
        return FakeResult(rows)


@pytest.fixture
def db():
    return FakeDB()


class FakeGeminiResponse:
    def __init__(self, payload: dict, status: int = 200):
        self._payload = payload
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            import httpx
            raise httpx.HTTPStatusError(
                f"status {self.status_code}",
                request=None,  # type: ignore
                response=self,  # type: ignore
            )

    def json(self):
        return self._payload


class FakeAsyncClient:
    """
    Stub de httpx.AsyncClient. Comparte la cola de respuestas con el Holder
    para que llamadas en distintos `async with` consuman secuencialmente.
    """
    def __init__(self, holder):
        self._holder = holder

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, json=None):
        self._holder.requests.append({"url": url, "body": json})
        payload = self._holder._queued.pop(0) if self._holder._queued else {"candidates": []}
        return FakeGeminiResponse(payload)


@pytest.fixture
def fake_httpx(monkeypatch):
    """
    Monkey-patchea httpx.AsyncClient. Respuestas se consumen en orden FIFO
    aunque esten en distintas iteraciones del loop de function-calling.
    """
    class Holder:
        def __init__(self):
            self._queued: list[dict] = []
            self.requests: list[dict] = []

        def queue(self, payload: dict):
            self._queued.append(payload)

        def reset(self):
            self._queued = []
            self.requests = []

    holder = Holder()

    def _factory(*args, **kwargs):
        return FakeAsyncClient(holder)

    import httpx
    monkeypatch.setattr(httpx, "AsyncClient", _factory)
    return holder


@pytest.fixture(autouse=True)
def _reset_key(monkeypatch):
    """Por default ponemos una key valida para que el chat no corte en 'sin_ia'."""
    from backend.core import key_store
    monkeypatch.setattr(key_store, "get_key", lambda: "FAKE_KEY_12345")
    yield


def gemini_text_response(texto: str) -> dict:
    """Payload que simula una respuesta de texto simple de Gemini."""
    return {
        "candidates": [
            {"content": {"parts": [{"text": texto}]}}
        ]
    }


def gemini_function_call(name: str, args: dict) -> dict:
    """Payload que simula un function call."""
    return {
        "candidates": [
            {"content": {"parts": [{"functionCall": {"name": name, "args": args}}]}}
        ]
    }


@pytest.fixture
def anyio_backend():
    return "asyncio"
