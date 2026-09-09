"""Kairos Treasury Review — recibos verificables (payload canónico + sobre firmado/anclado).

Tesis de la extensión: un expediente de riesgo que VIAJA con evidencia. El payload se
serializa de forma canónica (json.dumps sort_keys, separadores compactos), se hashea
(keccak256) y se firma EIP-191 (personal_sign) con la wallet del agente; el digesto se
ancla en HCS. Un SEGUNDO cliente (sin clave, sin confianza) re-verifica: digest, firma,
firmante esperado, expiración, audiencia y el ancla en el mirror node. Una copia alterada
o un firmante no autorizado → RECHAZADO.

Línea roja: el recibo acredita REGISTRO y procedencia, no la veracidad del pronóstico.
"""
from __future__ import annotations

import json
import time
from typing import Any

from eth_account import Account
from eth_account.messages import encode_defunct
from eth_account.signers.local import LocalAccount
from eth_utils import keccak  # type: ignore[attr-defined]

RECEIPT_SCHEMA = "kairos-treasury-review/1"
MIRROR_URL = "https://testnet.mirrornode.hedera.com/api/v1/topics/{topic}/messages"


def canonical_json(payload: dict[str, Any]) -> str:
    """Serialización canónica del payload — los bytes exactos que se hashean y firman."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest_of(canonical: str) -> str:
    raw = keccak(text=canonical).hex()
    return raw if raw.startswith("0x") else "0x" + raw


def build_envelope(payload: dict[str, Any], account: LocalAccount) -> dict[str, Any]:
    """Construye el sobre: payload + firma EIP-191. El ancla y el pago se adjuntan después."""
    canonical = canonical_json(payload)
    digest = digest_of(canonical)
    signed = account.sign_message(encode_defunct(text=canonical))
    return {
        "schema": RECEIPT_SCHEMA,
        "payload": payload,
        "signature": {
            "scheme": "eip-191",
            "digest": digest,
            "signer": account.address,
            "signature": signed.signature.hex(),
        },
    }


def verify_local(
    envelope: dict[str, Any],
    *,
    expected_signer: str,
    now_s: float | None = None,
) -> tuple[bool, dict[str, str]]:
    """Verificación SIN red: digest, firma, firmante, expiración, audiencia y esquema."""
    checks: dict[str, str] = {}
    ok = True
    try:
        schema = envelope.get("schema")
        checks["schema"] = schema or "AUSENTE"
        if schema != RECEIPT_SCHEMA:
            ok = False
        payload = envelope.get("payload")
        sig = envelope.get("signature") or {}
        if not isinstance(payload, dict) or not isinstance(sig, dict):
            return False, {"schema": schema or "?", "estructura": "payload o signature inválidos"}
        canonical = canonical_json(payload)
        recomputed = digest_of(canonical)
        checks["digest"] = "OK" if recomputed == sig.get("digest") else "NO COINCIDE"
        if recomputed != sig.get("digest"):
            ok = False
        try:
            recovered = Account.recover_message(encode_defunct(text=canonical),
                                                signature=sig.get("signature"))
        except Exception as exc:
            recovered = f"error: {type(exc).__name__}"
        expected = expected_signer.lower()
        checks["signer"] = ("OK" if recovered.lower() == expected
                             else f"{recovered} ≠ {expected}")
        if recovered.lower() != expected:
            ok = False
        expires = payload.get("expires_at")
        now = now_s if now_s is not None else time.time()
        checks["expires_at"] = str(expires)
        if not isinstance(expires, (int, float)) or now > expires:
            ok = False
        audience = payload.get("audience")
        checks["audience"] = str(audience)
        if audience != "demo-testnet":
            ok = False
        checks["payload_hash_hex"] = recomputed[:18] + "…"
    except Exception as exc:
        return False, {"error": f"{type(exc).__name__}: {str(exc)[:160]}"}
    return ok, checks


def tamper(envelope: dict[str, Any], mutate) -> dict[str, Any]:
    """Copia profunda con mutación sobre payload (para casos adversos de la demo)."""
    import copy
    env = copy.deepcopy(envelope)
    mutate(env["payload"])
    return env