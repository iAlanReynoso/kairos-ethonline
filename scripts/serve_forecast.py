#!/usr/bin/env python
"""Servidor REAL de forecast de Kairos — ciclo completo, militar, on-chain.

POST /forecast {question, market_price?, volume_24h?} ->
  1. investiga (GDELT + wiki + market)
  2. comité DeepSeek v4-flash + GLM tie-breaker estima P(YES)
  3. decide_from_belief: Kelly-alpha (alpha=0.25) + gates de riesgo -> BET/PASS/BLOCKED
  4. FIRMA EIP-191 (identidad estable KAIROS_AGENT_SIGNER_KEY)
  5. ANCLA el digest a HCS (Hedera testnet) en vivo — link Hashscan clickeable.
"""
from __future__ import annotations

import os
import sys
from typing import Any

from aiohttp import ClientSession, web

sys.path.insert(0, "/home/reyno/polymarket-bot/src")

from agentproof.core import Attestor

from kairos.agent.core import Market, PredictionMarketAgent
from kairos.agent.forecastbench import build_committee
from kairos.agent.news import build_news_retriever
from kairos.engine.risk import RiskConfig, RiskManager
from kairos.hedera import anchor

# Comité 4 miembros decorrelacionados (deepseek + claude + gpt via OpenRouter + GLM tie-breaker).
# La diversidad de linajes baja la sigma por ensamble y es la táctica ganadora del AIB (frente D).
COMMITTEE_SPEC = (
    "deepseek:deepseek-v4-flash,openrouter:anthropic/claude-opus-5,"
    "openrouter:openai/gpt-5.6-luna,?zai:glm-4.7-flash"
)
NEWS_SPEC = "gdelt+wiki+market"
DEMO_CAPITAL = 2_000.0
DEMO_TOPIC = os.environ.get("KAIROS_DEMO_TOPIC", "0.0.10374210")
ANCHOR_ONCHAIN = os.environ.get("KAIROS_ANCHOR_ONCHAIN", "1") == "1"


def _fuentes(question: str) -> list[str]:
    """Fuentes REALES del forecast (honestidad de superficie): thegraph aparece solo si se usó."""
    fuentes = NEWS_SPEC.split("+")
    try:
        from kairos.graph_evidence import graph_evidence_sync
        ev = graph_evidence_sync(question)
        if "metrics" in ev and ev.get("metrics"):
            fuentes.append("thegraph")
    except Exception:
        pass
    return fuentes


def _agent() -> PredictionMarketAgent:
    return PredictionMarketAgent(RiskManager(RiskConfig(), initial_capital=DEMO_CAPITAL), market_anchor_weight=0.3)


async def forecast(question: str, market_price: float, volume_24h: float) -> dict[str, Any]:
    retriever = build_news_retriever(NEWS_SPEC)
    researcher = build_committee(COMMITTEE_SPEC, retriever=retriever)
    yes_ask = max(0.01, min(0.99, market_price))
    market = Market(market_id="demo", question=question, yes_ask=yes_ask, yes_bid=yes_ask, volume_24h_usd=volume_24h)
    belief = await researcher.research(market)
    decision = _agent().decide_from_belief(
        market, posterior_p=belief.p_yes, posterior_sigma=belief.sigma,
        capital_available=DEMO_CAPITAL, belief_notes=belief.factors[:4],
    )

    signer_key = os.environ.get("KAIROS_AGENT_SIGNER_KEY") or None
    attestor = Attestor(signer_key)
    receipt = attestor.attest(
        claim=question,
        confidence=round(decision.decision_p, 4),
        reasoning=f"{decision.action.value}: {belief.summary[:200]}",
        meta={"verdict": decision.action.value, "p_posterior": round(decision.posterior_p, 4)},
    )

    anchor_info: dict[str, Any] = {}
    if ANCHOR_ONCHAIN and os.environ.get("HEDERA_ACCOUNT_ID") and os.environ.get("HEDERA_PRIVATE_KEY"):
        try:
            anchor_info = anchor.anchor_digest(DEMO_TOPIC, {
                "proyecto": "kairos-oracle",
                "tipo": "forecast-live",
                "question": question[:120],
                "p": round(decision.decision_p, 4),
                "verdict": decision.action.value,
                "digest": receipt.digest,
                "signer": receipt.signer,
            })
        except Exception as exc:
            anchor_info = {"error": f"{type(exc).__name__}: {str(exc)[:120]}"}

    return {
        "p": round(decision.posterior_p, 4),
        "sigma": round(decision.posterior_sigma, 4),
        "decision_p": round(decision.decision_p, 4),
        "verdict": decision.action.value,
        "side": decision.side,
        "edge": round(decision.edge, 4),
        "size_usd": round(decision.executed_size_usd, 2),
        "summary": (belief.summary or "")[:600],
        "factors": belief.factors[:6],
        "fuentes": _fuentes(question),
        "reasoning": decision.reasoning,
        "signature": {"signer": receipt.signer, "digest": receipt.digest},
        "device_confirmation": "pending" if getattr(decision, "requires_device_signature", False) else "none",
        "anchor": anchor_info,
        "votos": [
            {"modelo": v.get("modelo", "?"), "p_yes": round(float(v.get("p_yes", 0.5)), 3)}
            for v in (belief.votos or [])
        ],
    }


async def handle(request: web.Request) -> web.Response:
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "JSON inválido"}, status=400)
    question = (data.get("question") or "").strip()
    if len(question) < 5:
        return web.json_response({"error": "pregunta demasiado corta"}, status=400)
    market_price = float(data.get("market_price", 0.5))
    volume_24h = float(data.get("volume_24h", 0.0))
    try:
        result = await forecast(question, market_price, volume_24h)
    except Exception as exc:
        err = {"error": f"{type(exc).__name__}: {str(exc)[:160]}", "verdict": "PASS", "p": 0.5}
        return web.json_response(err, status=500)
    return web.json_response(result)


async def health(_: web.Request) -> web.Response:
    health_payload = {
        "ok": True, "committee": COMMITTEE_SPEC, "research": NEWS_SPEC,
        "anchor_onchain": ANCHOR_ONCHAIN, "topic": DEMO_TOPIC,
    }
    return web.json_response(health_payload)


# ── x402 paywall (track Hedera $6K): 402 -> paga HBAR -> 200 firmado + audit HCS ──
async def x402_requirements(_: web.Request) -> web.Response:
    from kairos.hedera.keys import account_id as hedera_account
    from kairos.pay.hedera_x402 import build_hedera_requirements
    req = build_hedera_requirements("/v1/forecast", 0.001, str(hedera_account()))
    return web.json_response({"x402Version": 2, "accepts": [req], "settlement": "Blocky402"}, status=402)


def _parse_x402_payload(header: str) -> dict[str, Any] | None:
    """X-PAYMENT = base64(JSON(paymentPayload)) o JSON crudo. Devuelve el paymentPayload."""
    import base64
    import json as _json

    raw = header.strip()
    candidates = [raw]
    try:
        decoded = base64.b64decode(raw, validate=False).decode()
        if decoded.strip().startswith("{"):
            candidates.append(decoded)
    except Exception:
        pass
    for c in candidates:
        try:
            obj = _json.loads(c)
            if isinstance(obj, dict) and ("payload" in obj or "accepted" in obj):
                return obj
        except Exception:
            continue
    return None


async def _blocky402_call(endpoint: str, body: dict[str, Any]) -> dict[str, Any]:
    """POST /verify o /settle al facilitator Blocky402 (open access en testnet)."""
    from kairos.pay.hedera_x402 import FACILITATOR_URL

    async with ClientSession() as s:
        async with s.post(f"{FACILITATOR_URL}{endpoint}", json=body, timeout=30) as r:
            return await r.json()


async def x402_paid(request: web.Request) -> web.Response:
    question = request.query.get("question", "")
    if len(question) < 5:
        return web.json_response({"error": "pregunta requerida"}, status=400)
    header = request.headers.get("X-PAYMENT", "")
    if not header:
        return await x402_requirements(request)
    payload = _parse_x402_payload(header)
    if payload is None:
        return web.json_response({"error": "X-PAYMENT ilegible (base64 del paymentPayload x402 v2)"}, status=400)
    requirements = payload.get("accepted", {})
    envelope = {"x402Version": 2, "paymentPayload": payload, "paymentRequirements": requirements}
    try:
        verify = await _blocky402_call("/verify", envelope)
    except Exception as exc:
        return web.json_response({"error": f"facilitator /verify inalcanzable: {exc}"}, status=502)
    if not verify.get("isValid"):
        return web.json_response({"error": "pago invalido", "facilitator": verify}, status=402)
    try:
        settle = await _blocky402_call("/settle", envelope)
    except Exception as exc:
        return web.json_response({"error": f"facilitator /settle inalcanzable: {exc}"}, status=502)
    if not settle.get("success"):
        return web.json_response({"error": "settlement fallo", "facilitator": settle}, status=402)
    result = await forecast(question, 0.5, 0.0)
    payer = verify.get("payer", "?")
    txid = settle.get("transaction", "")
    audit: dict[str, Any] = {}
    if os.environ.get("HEDERA_ACCOUNT_ID"):
        from kairos.pay.hedera_x402 import audit_payment_to_hcs
        audit = audit_payment_to_hcs(
            market_id=question[:60], amount_tinybar=str(requirements.get("amount", "100000")),
            from_addr=payer, topic_id=DEMO_TOPIC,
        )
        audit["settlement_tx"] = txid
        audit["hashscan"] = f"https://hashscan.io/testnet/transaction/{txid}" if txid else None
    return web.json_response({
        **result,
        "x402_settled_via": "Blocky402",
        "payment": {"payer": payer, "amount_tinybar": requirements.get("amount"), "settlement_tx": txid},
        "payment_audit": audit,
    })


def main() -> None:
    port = int(sys.argv[sys.argv.index("--port") + 1]) if "--port" in sys.argv else 8787
    app = web.Application()
    app.router.add_post("/forecast", handle)
    app.router.add_get("/v1/forecast", x402_paid)
    app.router.add_get("/health", health)
    print(f"Kairos forecast server en http://127.0.0.1:{port}  (POST /forecast, GET /v1/forecast x402)")
    web.run_app(app, host="127.0.0.1", port=port)


if __name__ == "__main__":
    main()
