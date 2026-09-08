#!/usr/bin/env python
"""Kairos — fachada PUBLICA: plataforma (UI) + endpoint x402, todo en una URL.

Expone (puerto 8788, detras del funnel publico https://ialanreynoso.tail3a9281.ts.net):
  GET  /            → la PLATAFORMA interactiva (misma UI del demo; pregunta y responde en vivo)
  POST /forecast    → forecast gratis con limite por IP (5 por 10 min — para jueces, no para abuso)
  GET  /health      → salud del servicio
  GET  /v1/forecast → x402 (402 sin pago; pago real via Blocky402 + audit HCS si paga)
Cualquier otra ruta → 404. CORS abierto (la UI de GitHub/raw puede llamar al endpoint).
"""
from __future__ import annotations

import os
import sys
import time
from typing import Any

from aiohttp import ClientSession, web

UPSTREAM = "http://127.0.0.1:8787"
UI_PATH = os.environ.get("KAIROS_UI_PATH",
                          "/home/reyno/polymarket-bot/docs/demo/kairos_ui_v3.html")

# limite anti-abuso del POST gratis: por IP, 5 ventanas de 10 min
_hits: dict[str, list[float]] = {}
RATE_LIMIT = 5
RATE_WINDOW = 600

@web.middleware
async def cors(request: web.Request, handler: Any) -> web.StreamResponse:
    if request.method == "OPTIONS":
        return web.Response(status=204, headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, X-PAYMENT",
        })
    resp = await handler(request)
    resp.headers["Access-Control-Allow-Origin"] = "*"
    return resp

def _rate_ok(ip: str) -> bool:
    now = time.time()
    hits = [t for t in _hits.get(ip, []) if now - t < RATE_WINDOW]
    if len(hits) >= RATE_LIMIT:
        return False
    hits.append(now)
    _hits[ip] = hits
    return True

async def ui(_: web.Request) -> web.Response:
    try:
        with open(UI_PATH, encoding="utf-8") as f:
            return web.Response(text=f.read(), content_type="text/html")
    except Exception:
        return web.Response(text="UI no disponible", status=503)

async def forecast_public(request: web.Request) -> web.Response:
    ip = request.remote or "?"
    if not _rate_ok(ip):
        return web.json_response({"error": "rate limit (5 por 10 min por IP)"}, status=429)
    body = await request.read()
    async with ClientSession() as s:
        async with s.post(f"{UPSTREAM}/forecast", data=body, timeout=600) as r:
            data = await r.read()
            return web.Response(status=r.status, body=data, headers={"Content-Type": "application/json"})


# el stream en vivo NO tiene limite por IP: detras del funnel todas las visitas
# comparten request.remote (127.0.0.1) y un cupo por IP dejaba la demo "rota" en cuanto
# Alan o los jueces probaban el diseno (429 silencioso). Guard suave de concurrencia.
_stream_active = 0
MAX_STREAMS = 3


async def stream_public(request: web.Request) -> web.StreamResponse:
    global _stream_active
    if _stream_active >= MAX_STREAMS:
        return web.json_response({"error": "busy (max 3 concurrentes); reintenta en unos segundos"}, status=429)
    _stream_active += 1
    body = await request.read()
    resp = web.StreamResponse(status=200, headers={
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Access-Control-Allow-Origin": "*",
    })
    await resp.prepare(request)
    try:
        async with ClientSession() as s:
            async with s.post(f"{UPSTREAM}/forecast/stream", data=body, timeout=None) as r:
                async for chunk in r.content.iter_any():
                    await resp.write(chunk)
    except Exception:
        pass
    finally:
        _stream_active -= 1
    return resp


OG_PATH = "/home/reyno/polymarket-bot/docs/ethonline/assets_form/og.png"

async def og_image(_: web.Request) -> web.Response:
    try:
        with open(OG_PATH, "rb") as f:
            return web.Response(body=f.read(), content_type="image/png")
    except Exception:
        return web.Response(status=404)

async def health(_: web.Request) -> web.Response:
    async with ClientSession() as s:
        async with s.get(f"{UPSTREAM}/health", timeout=10) as r:
            body = await r.read()
            return web.Response(status=r.status, body=body, headers={"Content-Type": "application/json"})

async def x402(request: web.Request) -> web.Response:
    headers = {k: v for k, v in request.headers.items()
               if k.lower() in ("accept", "x-payment", "x-payment-address", "x-payment-amount",
                                "x-payment-asset", "x-payment-network", "x-payment-chain-id",
                                "x-payment-scheme", "x-payment-max-required", "x-receipt")}
    qs = f"?{request.query_string}" if request.query_string else ""
    async with ClientSession() as s:
        async with s.get(f"{UPSTREAM}/v1/forecast{qs}", headers=headers, timeout=600) as r:
            body = await r.read()
            return web.Response(status=r.status, body=body, headers={"Content-Type": "application/json"})

def main() -> int:
    port = int(sys.argv[sys.argv.index("--port") + 1]) if "--port" in sys.argv else 8788
    app = web.Application(middlewares=[cors])
    app.router.add_get("/", ui)
    app.router.add_post("/forecast", forecast_public)
    app.router.add_post("/forecast/stream", stream_public)
    app.router.add_get("/og.png", og_image)
    app.router.add_get("/health", health)
    app.router.add_get("/v1/forecast", x402)
    print(f"Kairos fachada publica en http://127.0.0.1:{port} (UI + stream en vivo sin limite + /forecast limitado + /health + /v1/forecast x402)")
    web.run_app(app, host="127.0.0.1", port=port)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
