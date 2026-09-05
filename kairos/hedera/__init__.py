"""Integración de producción con Hedera (testnet) — el trabajo NUEVO de la ventana ETHOnline 4-16 sep.

Consolida los spikes de scripts/research/spike_hedera_*.py en una API limpia:

- :mod:`kairos.hedera.anchor` — HCS: crea topic, ancla el digest del forecast.
- :mod:`kairos.hedera.schedule` — Schedule Service: la próxima acción ejecutada POR LA RED (sin keeper).
- :mod:`kairos.hedera.hfs` — HFS: recibo completo como archivo on-ledger, SHA-256 anclado al topic.

Honestidad load-bearing: testnet, $0 real, clave NUNCA impresa. La trampa del SDK 0.2.10
(PrivateKey.from_string con hex crudo → Ed25519 derivada; usar DER) vive en kairos.hedera.keys.
"""
from kairos.hedera import anchor, hfs, keys, schedule

__all__ = ["anchor", "hfs", "keys", "schedule"]
