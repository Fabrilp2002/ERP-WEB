"""Rate limiting liviano para endpoints sensibles.

Implementación in-memory por proceso. Para el tamaño actual del ERP y Render/Railway
single worker es suficiente; si escala a múltiples workers se puede reemplazar por
Redis/SlowAPI manteniendo una interfaz centralizada `limiter.check(...)`.
"""
from __future__ import annotations

import time
from collections import defaultdict, deque
from fastapi import HTTPException, Request, status


class SimpleLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    @staticmethod
    def _parse_limit(limit: str) -> tuple[int, int]:
        count_s, window_s = limit.split("/", 1)
        count = int(count_s)
        window_s = window_s.lower().strip()
        if window_s in {"second", "segundo", "s"}:
            seconds = 1
        elif window_s in {"minute", "minuto", "m"}:
            seconds = 60
        elif window_s in {"hour", "hora", "h"}:
            seconds = 3600
        else:
            raise ValueError(f"Ventana de rate limit no soportada: {limit}")
        return count, seconds

    @staticmethod
    def _client_ip(request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",", 1)[0].strip()
        return request.client.host if request.client else "unknown"

    def check(self, request: Request, limit: str) -> None:
        max_hits, seconds = self._parse_limit(limit)
        now = time.monotonic()
        key = f"{self._client_ip(request)}:{request.url.path}"
        hits = self._hits[key]
        while hits and now - hits[0] > seconds:
            hits.popleft()
        if len(hits) >= max_hits:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Demasiados intentos. Esperá un minuto y probá de nuevo.",
            )
        hits.append(now)


limiter = SimpleLimiter()
