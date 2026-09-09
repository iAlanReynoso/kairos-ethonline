#!/usr/bin/env python
"""Verificador INDEPENDIENTE de expedientes Kairos Treasury Review.

Uso:
  python scripts/ethonline/verify_receipt.py recibo.json [--signer 0x...] [--mirror]

Sin clave y sin confianza: recalcula el digesto del payload, verifica la firma EIP-191
contra la identidad esperada del agente, valida expiración/audiencia y (con --mirror)
cruza el digesto contra el tópico HCS en el mirror node de Hedera testnet.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

from kairos.treasury.mirror import verify_anchor_crosscheck
from kairos.treasury.receipt import verify_local

DEFAULT_SIGNER = os.environ.get("KAIROS_EXPECTED_SIGNER", "0x87a49Abd203BFBB12Ec3761A9E3697fe406e5Ee3")


def main() -> int:
    ap = argparse.ArgumentParser(description="Verificador independiente de recibos Treasury Review")
    ap.add_argument("recibo", help="ruta al JSON del sobre (envelope)")
    ap.add_argument("--signer", default=DEFAULT_SIGNER, help="dirección esperada del firmante")
    ap.add_argument("--mirror", action="store_true", help="cruzar el digesto contra HCS (mirror node)")
    args = ap.parse_args()
    with open(args.recibo, encoding="utf-8") as f:
        envelope = json.load(f)
    print("== VERIFICACIÓN LOCAL ==")
    ok, checks = verify_local(envelope, expected_signer=args.signer)
    for k, v in checks.items():
        print(f"  {k}: {v}")
    if args.mirror:
        print("== CROSS-CHECK HCS (mirror node) ==")
        ok_m, checks_m = asyncio.run(verify_anchor_crosscheck(envelope))
        for k, v in checks_m.items():
            print(f"  {k}: {v}")
        ok = ok and ok_m
    verdict = "ACEPTADO ✓" if ok else "RECHAZADO ✗"
    print(f"\nVEREDICTO DEL VERIFICADOR: {verdict}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())