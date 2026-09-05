"""x402 en Hedera — el track "AI & Agentic Payments" ($6K) de ETHOnline.

Toma el módulo pay/x402 (flujo 402→verify→serve ya testeado) y lo instancia para Hedera:
- asset: HBAR (nativo, sin token contract)
- network: hedera-testnet
- settlement: Blocky402 facilitator (requisito literal del track). El facilitator settlea
  la autorización on-chain; este módulo expone los payment requirements conformes y el
  HCS_AUDIT_TRAIL: cada pago servido ancla su recibo a HCS (extra point "verifiable
  payment audit trails on HCS").

HONESTO: el settlement real contra Blocky402 se hace en la ventana (endpoint live). Este
módulo deja el flujo cableado y testeable; el facilitator se conecta en el endpoint HTTP.
"""
from __future__ import annotations

from typing import Any

# HBAR no es un contrato: el asset en x402 sobre Hedera es "HBAR" (nativo) — el facilitator
# Blocky402 lo settlea contra la red Hedera. Los 8 decimales de HBAR equivalen a tinybars.
HBAR_ASSET = "HBAR"
HBAR_NETWORK = "hedera:testnet"  # scheme exact del facilitator (hedera:testnet, no hedera-testnet)
HBAR_DECIMALS = 8


def to_tinybar(hbar: float | str) -> str:
    """HBAR → tinybars (string, 8 decimales). 0.001 HBAR → 100000 tinybar."""
    from decimal import Decimal

    q = Decimal(1).scaleb(-HBAR_DECIMALS)
    try:
        amount = Decimal(str(hbar)).quantize(q)
    except Exception as exc:
        raise ValueError(f"monto HBAR inválido: {hbar!r}") from exc
    if amount < 0:
        raise ValueError(f"monto HBAR negativo: {hbar!r}")
    return str(int(amount.scaleb(HBAR_DECIMALS)))


# Facilitador oficial del track (open access en testnet, sin API key):
#   GET  https://api.testnet.blocky402.com/supported  → hedera:testnet, feePayer 0.0.7162784
#   POST /verify + POST /settle (wire format x402 v2).
FACILITATOR_URL = "https://api.testnet.blocky402.com"
FACILITATOR_FEE_PAYER = "0.0.7162784"


def build_hedera_requirements(
    resource: str,
    price_hbar: float,
    pay_to: str,
    *,
    description: str = "Forecast calibrado + firmado (Kairos on Hedera)",
) -> dict[str, Any]:
    """PaymentRequirements x402 v2 del scheme exact de Hedera (asset 0.0.0 = HBAR nativo).

    extra.feePayer es OBLIGATORIO en el scheme: el cliente construye la TransferTransaction
    con el facilitator como payer, la firma, y el facilitator (Blocky402) la co-firma y
    settlea pagando la fee de red. Sin feePayer el client SDK del scheme no firma.
    """
    return {
        "scheme": "exact",
        "network": HBAR_NETWORK,
        "amount": to_tinybar(price_hbar),
        "payTo": pay_to,
        "maxTimeoutSeconds": 300,
        "asset": "0.0.0",  # HBAR nativo (tinybar)
        "description": description,
        "resource": resource,
        "mimeType": "application/json",
        "extra": {"feePayer": FACILITATOR_FEE_PAYER},
    }


def audit_payment_to_hcs(
    *,
    market_id: str,
    amount_tinybar: str,
    from_addr: str,
    topic_id: str,
) -> dict[str, Any]:
    """Ancla el recibo del pago a HCS (audit trail verifiable — extra point del track).

    Devuelve el resultado del anclaje (status, sha256, hashscan). Si hiero no está o falla,
    devuelve {"error": ...} — el forecast se sirve igual (doctrina B: el audit trail no debe
    tumbar el servicio).
    """
    try:
        from kairos.hedera import anchor

        return anchor.anchor_digest(topic_id, {
            "proyecto": "kairos-oracle",
            "tipo": "x402-payment-audit",
            "market_id": market_id,
            "amount_tinybar": amount_tinybar,
            "from": from_addr,
        })
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {str(exc)[:120]}"}
