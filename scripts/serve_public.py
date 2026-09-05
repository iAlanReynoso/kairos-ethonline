#!/usr/bin/env python
"""Kairos — fachada PUBLICA del forecast server (para el funnel de Tailscale).

Expone SOLO lo que un juez necesita para verificar el x402 en vivo:
  GET /health      → salud del servicio (publica, sin datos sensibles)
  GET /            → mapa de endpoints + link al repo
  GET /v1/forecast → proxy 1:1 al server 8787 (402 x402 sin pago; pago+audit HCS si paga)
Cualquier otra ruta (incluido POST /forecast, que cuesta tokens) → 404.
El server real (8787) sigue en 127.0.0.1 y nunca escucha en 0.0.0.0.
"""
from __future__ import annotations

import sys
from typing import Any

from aiohttp import ClientSession, web

UPSTREAM = "http://127.0.0.1:8787"

async def proxy(request: web.Request, path: str) -> web.Response:
    headers = {k: v for k, v in request.headers.items()
               if k.lower() in ("accept", "x-payment", "x-payment-address", "x-payment-amount",
                                "x-payment-asset", "x-payment-network", "x-payment-chain-id",
                                "x-payment-scheme", "x-payment-max-required", "x-receipt")}
    qs = f"?{request.query_string}" if request.query_string else ""
    async with ClientSession() as s:
        async with s.get(f"{UPSTREAM}{path}{qs}", headers=headers, timeout=600) as r:
            body = await r.read()
            return web.Response(status=r.status, body=body, headers={"Content-Type": "application/json"})

async def health(_: web.Request) -> web.Response:
    async with ClientSession() as s:
        async with s.get(f"{UPSTREAM}/health", timeout=10) as r:
            body = await r.read()
            return web.Response(status=r.status, body=body, headers={"Content-Type": "application/json"})

async def index(_: web.Request) -> web.Response:
    return web.json_response({
        "service": "kairos-forecast (fachada publica)",
        "endpoints": [
            "GET /health",
            "GET /v1/forecast  (x402: 402 HBAR por forecast con pago + audit trail en HCS)",
        ],
        "repo": "https://github.com/iAlanReynoso/kairos-ethonline",
        "verify": "https://github.com/iAlanReynoso/kairos-ethonline/blob/main/VERIFY.md",
    })

def main() -> int:
    port = int(sys.argv[sys.argv.index("--port") + 1]) if "--port" in sys.argv else 8788
    app = web.Application()
    app.router.add_get("/", index)
    app.router.add_get("/health", health)
    app.router.add_get("/v1/forecast", lambda r: proxy(r, "/v1/forecast"))
    print(f"Kairos fachada publica en http://127.0.0.1:{port} (solo /health y /v1/forecast)")
    web.run_app(app, host="127.0.0.1", port=port)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
