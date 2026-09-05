#!/usr/bin/env python
"""Kairos — CLIENTE x402 real (el 'agente que paga' del track AI & Agentic Payments).

Flujo completo contra el endpoint vivo:
  1. GET /v1/forecast?question=...  → 402 + requirements (asset 0.0.0, extra.feePayer)
  2. construye la TransferTransaction con el facilitator (Blocky402) como payer, la firma
     con NUESTRA clave y la serializa base64 → paymentPayload x402 v2
  3. POST /verify al facilitator (chequeo previo)
  4. GET el recurso con X-PAYMENT: base64(paymentPayload) → el server /verify + /settle
     (el facilitator paga la fee de red y submitea) → 200 con forecast firmado + audit HCS

Uso: uv run python scripts/ethonline/pay_x402.py --question '...' [--url http://127.0.0.1:8788]
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from hiero_sdk_python import (AccountCreateTransaction, AccountId, Client, PrivateKey,
                             TransactionId, TransferTransaction)


def http_json(url: str, method: str = "GET", body: dict | None = None, headers: dict | None = None, **kwargs):
    req = urllib.request.Request(url, method=method,
                                 data=json.dumps(body).encode() if body else None,
                                 headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=kwargs.get("timeout", 60)) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:  # 402 es parte del protocolo, no un error de cliente
        return e.code, json.loads(e.read().decode())


def balance_tinybar(account: str) -> int:
    _, data = http_json(f"https://testnet.mirrornode.hedera.com/api/v1/accounts/{account}")
    return int(data["balance"]["balance"])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--question", default="Will ETH hit 10k in 2026?",
                    help="pregunta que el agente paga por contestar")
    ap.add_argument("--url", default=os.environ.get("KAIROS_X402_URL", "http://127.0.0.1:8788"),
                    help="base del forecast server (8787 local, 8788 fachada publica)")
    ap.add_argument("--facilitator", default="https://api.testnet.blocky402.com")
    args = ap.parse_args()

    # Comprador = wallet propia del agente (creada on-chain la primera vez, 5 HBAR).
    # HEDERA_ACCOUNT_ID es el OPERADOR (servicio); el comprador es otra cuenta — pago real
    # entre dos partes, no un self-pay que la red colapsa a cero.
    buyer_file = "data/ethonline_buyer.json"
    if not os.path.exists(buyer_file):
        operator_key = PrivateKey.from_string(os.environ["HEDERA_PRIVATE_KEY"])
        client = Client.for_testnet()
        client.set_operator(AccountId.from_string(os.environ["HEDERA_ACCOUNT_ID"]), operator_key)
        new_key = PrivateKey.generate_ecdsa()
        create = AccountCreateTransaction()
        create.set_key(new_key)
        create.set_initial_balance(500000000)  # 5 HBAR (tinybar)
        create.freeze_with(client)
        create.sign(new_key)
        receipt = create.execute(client)  # ya es TransactionReceipt
        buyer_id = str(receipt.account_id)
        with open(buyer_file, "w", encoding="utf-8") as f:
            json.dump({"account": buyer_id, "key_der": new_key.to_string_der()}, f)
        print(f"WALLET DEL AGENTE CREADA: {buyer_id} (5 HBAR) — evidencia on-chain nueva")
        client.close()
    with open(buyer_file, encoding="utf-8") as f:
        buyer = json.load(f)
    account = buyer["account"]
    key = PrivateKey.from_string(buyer["key_der"])

    q = urllib.parse.quote(args.question)
    resource = f"/v1/forecast?question={q}"
    status, body = http_json(args.url + resource)
    if status != 402:
        print(f"ESPERABA 402, obtuve {status}: {json.dumps(body)[:200]}"); return 1
    req = body["accepts"][0]
    amount = int(req["amount"])
    pay_to = req["payTo"]
    fee_payer = req["extra"]["feePayer"]
    print(f"402 OK: {amount} tinybar → {pay_to} (feePayer {fee_payer})")

    bal = balance_tinybar(account)
    print(f"balance comprador {account}: {bal} tinybar ({bal/1e8} HBAR)")
    if bal < amount:
        print("FONDOS INSUFICIENTES — pedir faucet antes de pagar"); return 2

    # TransferTransaction parcialmente firmada: payer = facilitator (paga la fee),
    # nosotros firmamos la transferencia de valor.
    tx = TransferTransaction()
    tx.set_transaction_id(TransactionId.generate(AccountId.from_string(fee_payer)))
    tx.set_node_account_id(AccountId.from_string("0.0.3"))
    tx.add_hbar_transfer(AccountId.from_string(account), -amount)
    tx.add_hbar_transfer(AccountId.from_string(pay_to), +amount)
    tx.set_transaction_valid_duration(120)
    tx.freeze()
    tx.sign(key)
    b64 = base64.b64encode(tx.to_bytes()).decode()

    payment_payload = {
        "x402Version": 2,
        "scheme": "exact",
        "network": req["network"],
        "accepted": req,
        "payload": {"transaction": b64},
    }
    envelope = {"x402Version": 2, "paymentPayload": payment_payload, "paymentRequirements": req}

    # pre-verificacion opcional (honesta: valida firma antes de pagar)
    status_v, ver = http_json(args.facilitator + "/verify", "POST", envelope)
    print(f"/verify → {status_v} isValid={ver.get('isValid')} payer={ver.get('payer')}")
    if not ver.get("isValid"):
        print("VERIFY RECHAZO:", ver); return 3

    # pagar: el server settlea via facilitator y sirve el forecast
    xpay = base64.b64encode(json.dumps(payment_payload).encode()).decode()
    status2, result = http_json(args.url + resource, "GET", headers={"X-PAYMENT": xpay}, timeout=240)
    print(f"PAGADO → HTTP {status2}")
    print(json.dumps({k: result.get(k) for k in ("verdict", "p", "decision_p", "signature", "payment", "payment_audit")}, indent=2)[:1600])
    if status2 != 200:
        return 4

    evidence = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "question": args.question,
        "resource": resource,
        "amount_tinybar": amount,
        "payTo": pay_to,
        "payer": ver.get("payer"),
        "facilitator": args.facilitator,
        "verify": ver,
        "result": result,
    }
    out = f"docs/ethonline/x402_paid_evidence_{time.strftime('%Y%m%d-%H%M%S')}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(evidence, f, indent=2, ensure_ascii=False)
    print("EVIDENCIA:", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
