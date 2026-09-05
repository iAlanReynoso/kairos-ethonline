"""Anclaje HCS de producción — el forecast firmado queda anclado ANTES del cierre.

HCS = consenso de orden + timestamp de red. El digest del forecast se submit como mensaje al
topic; el mirror node lo expone con un link clickeable que un juez puede abrir. Es la prueba
anti-timing: "se dijo antes del cierre" pasa de promesa a hecho verificable.

Port de scripts/research/spike_hedera_hcs.py (17-ago, probado on-ledger). Testnet, $0 real.
"""
from __future__ import annotations

import hashlib
import json
import time

import httpx
from hiero_sdk_python import (
    Client,
    Network,
    TopicCreateTransaction,
    TopicMessageSubmitTransaction,
)

from kairos.hedera.keys import account_id, private_key

MIRROR = "https://testnet.mirrornode.hedera.com/api/v1"


def _client() -> Client:
    c = Client(Network("testnet"))
    c.set_operator(account_id(), private_key())
    return c


def create_topic(memo: str = "kairos-oracle") -> str:
    """Crea un topic HCS y devuelve su id (0.0.x)."""
    c = _client()
    tx = TopicCreateTransaction()
    receipt = tx.execute(c)
    return str(receipt.topic_id)


def anchor_digest(topic_id: str, payload: dict[str, object]) -> dict[str, object]:
    """Submit el digest del payload al topic y devuelve {status, mirror_url, sha256}.

    payload: dict con al menos {proyecto, tipo, question_id, p, ts_forecast}.
    El sha256 del JSON ordenado es lo que viaja (el contenido completo vive en HFS).
    """
    c = _client()
    sha = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    msg = json.dumps({**payload, "sha256": sha}, sort_keys=True)
    sub = TopicMessageSubmitTransaction()
    sub.set_topic_id(__import__("hiero_sdk_python", fromlist=["TopicId"]).TopicId.from_string(topic_id))
    sub.set_message(msg)
    receipt = sub.execute(c)
    return {
        "status": str(getattr(receipt, "status", "?")),
        "topic_id": topic_id,
        "sha256": sha,
        "mirror_url": f"{MIRROR}/topics/{topic_id}/messages",
        "hashscan": f"https://hashscan.io/testnet/topic/{topic_id}",
    }


def wait_mirror(topic_id: str, timeout_s: float = 180.0) -> list[dict[str, object]]:
    """Espera a que el mirror node exponga los mensajes del topic y los devuelve."""
    url = f"{MIRROR}/topics/{topic_id}/messages"
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        try:
            r = httpx.get(url, timeout=20.0)
            msgs = (r.json() or {}).get("messages") or []
        except Exception:
            msgs = []
        if msgs:
            return msgs
        time.sleep(3.0)
    return []
