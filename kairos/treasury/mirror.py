"""Cross-check del ancla HCS contra el mirror node (sin clave, sin confianza)."""
from __future__ import annotations

import base64
import json
from typing import Any

import aiohttp

MIRROR_URL = "https://testnet.mirrornode.hedera.com/api/v1/topics/{topic}/messages"


async def verify_anchor_crosscheck(
    envelope: dict[str, Any], *, mirror_url: str = MIRROR_URL, timeout_s: float = 30.0
) -> tuple[bool, dict[str, str]]:
    """Verifica que el digesto firmado esté publicado en el tópico HCS declarado."""
    checks: dict[str, str] = {}
    anchor = envelope.get("anchor") or {}
    sig = envelope.get("signature") or {}
    topic = anchor.get("topic_id")
    seq = anchor.get("sequence")
    digest = sig.get("digest", "")
    if not topic or seq is None:
        return False, {"ancla": "ausente o incompleta"}
    url = mirror_url.format(topic=topic)
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, params={"limit": 100}, timeout=aiohttp.ClientTimeout(total=timeout_s)) as r:
                if r.status != 200:
                    return False, {"mirror": f"HTTP {r.status}"}
                data = await r.json()
    except Exception as exc:
        return False, {"mirror": f"{type(exc).__name__}: {str(exc)[:120]}"}
    messages = data.get("messages") or []
    for m in messages:
        if int(m.get("sequence_number", -1)) != int(seq):
            continue
        try:
            body = base64.b64decode(m.get("message", "")).decode("utf-8", "replace")
        except Exception:
            body = ""
        checks["topic_id"] = str(topic)
        checks["sequence"] = str(seq)
        checks["consensus_timestamp"] = str(m.get("consensus_timestamp", "?"))
        if digest and digest in body:
            checks["digest_en_ancla"] = "OK"
            return True, checks
        checks["digest_en_ancla"] = "NO ESTÁ EN EL MENSAJE"
        return False, checks
    return False, {"topic_id": str(topic), "sequence": str(seq),
                    "mirror": "secuencia no encontrada en los últimos 100 mensajes"}