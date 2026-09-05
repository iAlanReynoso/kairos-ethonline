"""HFS de producción — el recibo completo como archivo on-ledger, SHA-256 anclado al topic.

HCS ancla el DIGEST; el recibo firmado COMPLETO (pregunta, comité, creencia, rationale, firma)
es demasiado grande para un mensaje HCS razonable. HFS lo guarda como archivo on-ledger y su
SHA-256 se ancla al topic. Verificar = leer el archivo y recomputar el hash.

Port de scripts/research/spike_hedera_hfs.py (24-ago, probado on-ledger). Testnet, $0 real.
"""
from __future__ import annotations

import hashlib
import json

from hiero_sdk_python import (
    Client,
    FileCreateTransaction,
    Network,
    TopicId,
    TopicMessageSubmitTransaction,
)

from kairos.hedera.keys import account_id, private_key

MIRROR = "https://testnet.mirrornode.hedera.com/api/v1"


def _client() -> Client:
    c = Client(Network("testnet"))
    c.set_operator(account_id(), private_key())
    return c


def store_receipt(receipt: dict[str, object], topic_id: str) -> dict[str, object]:
    """Guarda el recibo como archivo HFS y ancla su sha256 al topic.

    Devuelve {file_id, bytes, sha256, hashscan}. El contenido es el JSON ordenado del recibo;
    su sha256 es lo que se ancla a HCS (proveniencia completa on-chain).
    """
    c = _client()
    content = json.dumps(receipt, sort_keys=True).encode("utf-8")
    sha = hashlib.sha256(content).hexdigest()

    tx = FileCreateTransaction()
    tx.set_contents(content)
    fr = tx.execute(c)
    file_id = str(getattr(fr, "file_id", "?"))

    # anclar el hash al topic
    anchor_payload = {"tipo": "hfs-anchor", "file_id": file_id, "sha256": sha, "servicio": "HFS+HCS"}
    anchor_msg = json.dumps(anchor_payload, sort_keys=True)
    sub = TopicMessageSubmitTransaction()
    sub.set_topic_id(TopicId.from_string(topic_id))
    sub.set_message(anchor_msg)
    sub.execute(c)

    return {
        "file_id": file_id,
        "bytes": len(content),
        "sha256": sha,
        "hashscan": f"https://hashscan.io/testnet/file/{file_id}",
        "mirror_note": "mirror REST no expone files en testnet; verificar via FileContentsQuery",
    }
