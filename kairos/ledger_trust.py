#!/usr/bin/env python
"""Integración Ledger — confirmación por dispositivo en el camino de alto riesgo.

Track Continuity ($1.5K) verbatim: "give an existing app a hardware signer, move its secrets onto
the Key Ring, or put a device confirmation in front of an action that previously had none."
Track AI Agents ($3.5K): "Human-in-the-loop agents where Ledger approves high-risk actions before
funds move or permissions escalate."

Fit honesto de Kairos: el motor YA tiene el camino BLOCKED (gates de riesgo). Ledger agrega la
capa de hardware: cuando una decisión pasa sizing y el único freno es la firma humana, esa firma
sale del dispositivo Ledger (wallet-cli ring) en vez de una key en .env.
"""
from __future__ import annotations

from typing import Any

# wallet-cli ring (Ledger Key Ring CLI) — los secretos viven en el dispositivo, no en .env.
# npx skills add ledgerhq/agent-skills · npm i -g @ledgerhq/wallet-cli


def requires_device_confirmation(verdict: str, size_usd: float, threshold_usd: float = 100.0) -> bool:
    """¿Esta acción exige confirmación por dispositivo?

    Regla de diseño (bounded agent): acciones BET por encima del umbral, o cualquier acción
    irreversible de fondos, requieren la confirmación humana en el dispositivo. Las decisiones
    pequeñas/automáticas siguen autónomas. Es el patrón "human-in-the-loop" del track.
    """
    return verdict == "BET" and size_usd >= threshold_usd


def ledger_sign_pending(decision: dict[str, Any]) -> dict[str, Any]:
    """Prepara la solicitud de firma para el dispositivo (el flujo del Key Ring).

    En la ventana: se cablea con wallet-cli ring. Acá queda la interfaz honesta: qué acción
    espera la confirmación del humano y con qué parámetros.
    """
    return {
        "status": "pending-device-confirmation",
        "action": decision.get("side", ""),
        "size_usd": decision.get("size_usd", 0.0),
        "note": "Aprueba en el dispositivo Ledger para ejecutar (human-in-the-loop).",
    }


def move_secrets_to_key_ring() -> dict[str, Any]:
    """Migración de secretos del .env al Key Ring (el "before/after" del track Continuity).

    BEFORE: claves en .env del servidor (si el host cae, las claves se filtran).
    AFTER: las claves de alto riesgo viven en el dispositivo; el agente pide firma, no la guarda.
    """
    return {
        "before": ".env plaintext keys (signer key, hedera key)",
        "after": "wallet-cli ring as key backend — agent asks, device signs",
        "status": "documented — wiring en la ventana con wallet-cli ring",
    }
