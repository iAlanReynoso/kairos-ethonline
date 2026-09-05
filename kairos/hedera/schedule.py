"""Schedule Service de producción — la próxima acción ejecutada POR LA RED, sin keeper.

En Hedera una scheduled tx ejecuta cuando JUNTA las firmas requeridas (no a una hora de reloj).
La coreografía: crear schedule con la firma del operador ⇒ la red la ejecuta sola. Para el demo
de Continuity eso es "sin keeper, sin cron, sin 'el laptop estaba dormido'".

Port de scripts/research/spike_hedera_schedule.py (17-ago, probado on-ledger: schedule ejecutada
por la red). Testnet, $0 real.
"""
from __future__ import annotations

import base64
import contextlib
import time

import httpx
from hiero_sdk_python import (
    Client,
    Network,
    ScheduleCreateTransaction,
    TopicId,
    TopicMessageSubmitTransaction,
)

from kairos.hedera.keys import account_id, private_key

MIRROR = "https://testnet.mirrornode.hedera.com/api/v1"


def _client() -> Client:
    c = Client(Network("testnet"))
    c.set_operator(account_id(), private_key())
    return c


def schedule_anchor(topic_id: str, message: str) -> dict[str, object]:
    """Agenda un submit al topic que la red ejecuta al juntar las firmas.

    Devuelve {schedule_id, status, mirror_url}. El mensaje entra al topic SIN que nosotros
    lo enviemos directamente: es la red la que ejecuta la tx agendada.
    """
    c = _client()
    inner = TopicMessageSubmitTransaction()
    inner.set_topic_id(TopicId.from_string(topic_id))
    inner.set_message(message)
    with contextlib.suppress(Exception):  # 0.2.10: freeze_with puede no estar
        inner.freeze_with(c)
    sched = ScheduleCreateTransaction()
    sched.set_scheduled_transaction(inner)
    receipt = sched.execute(c)
    return {
        "schedule_id": str(getattr(receipt, "schedule_id", "?")),
        "status": str(getattr(receipt, "status", "?")),
        "mirror_url": f"{MIRROR}/topics/{topic_id}/messages",
        "hashscan": f"https://hashscan.io/testnet/schedule/{getattr(receipt, 'schedule_id', '')}",
    }


def wait_execution(topic_id: str, baseline_seq: int = 0, timeout_s: float = 180.0) -> list[dict[str, object]]:
    """Espera a que la red ejecute la tx agendada (nuevo mensaje con seq > baseline)."""
    url = f"{MIRROR}/topics/{topic_id}/messages"
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        try:
            r = httpx.get(url, timeout=20.0)
            msgs = (r.json() or {}).get("messages") or []
        except Exception:
            msgs = []
        nuevos = [m for m in msgs if int(m.get("sequence_number", 0)) > baseline_seq]
        if nuevos:
            for m in nuevos:
                try:
                    m["decoded"] = base64.b64decode(m.get("message", "")).decode("utf-8", "replace")
                except Exception:
                    m["decoded"] = "<binary>"
            return nuevos
        time.sleep(3.0)
    return []
