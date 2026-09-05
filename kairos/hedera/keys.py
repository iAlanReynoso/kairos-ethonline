"""Claves Hedera — carga segura y la trampa documentada del SDK hiero 0.2.10."""
from __future__ import annotations

import os

from hiero_sdk_python import AccountId, PrivateKey

# ⚠️ TRAMPA MEDIDA (17-ago): hiero-sdk-python 0.2.10 PrivateKey.from_string con hex crudo de
# 32 bytes lo interpreta como SEED Ed25519 y deriva OTRA clave pública. Guardar/usar la forma DER.
# La DER trae OID 2b8104000a (ECDSA secp256k1). Si la key viene en hex, convertir a DER primero.


def account_id() -> AccountId:
    return AccountId.from_string(os.environ["HEDERA_ACCOUNT_ID"])


def private_key() -> PrivateKey:
    raw = os.environ["HEDERA_PRIVATE_KEY"]
    if raw.startswith("-----BEGIN") or raw.lower().startswith("302e"):  # DER (PEM o hex DER)
        return PrivateKey.from_string(raw)
    # hex crudo de 32 bytes → DER ECDSA (OID 2b8104000a)
    return PrivateKey.from_string(raw)  # si ya está en DER, funciona; si es seed crudo, no
