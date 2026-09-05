# Verify Kairos — copy-paste, no auth

Everything on this page is checkable by anyone, in seconds, without our servers.

## 1. Forecast anchors on Hedera (HCS)

The digest of each forecast is submitted to the topic **`0.0.10213059`** *before* the question closes.
Hedera Consensus Service orders and timestamps every message — that timestamp is the proof of "before close".

```bash
# Mirror node (public REST, no key):
curl -s https://testnet.mirrornode.hedera.com/api/v1/topics/0.0.10213059/messages | python3 -m json.tool
```

Each message is a base64-encoded JSON anchor: `{proyecto, tipo, question_id, p, ts_forecast, sha256}`.
Or browse it: <https://hashscan.io/testnet/topic/0.0.10213059>

## 2. Pre-existing spike (Aug, executed by the network)

| Object | Hashscan |
|---|---|
| account | <https://hashscan.io/testnet/account/0.0.10107589> |
| topic (spike) | <https://hashscan.io/testnet/topic/0.0.10114138> |
| scheduled tx (executed by network) | <https://hashscan.io/testnet/schedule/0.0.10114149> |

## 3. Receipt on HFS

The full receipt is stored on Hedera File Service, file **`0.0.10215927`** (271 bytes), its SHA-256
anchored back to the topic.

> ⚠️ The mirror node REST does **not** expose file contents on testnet. To verify the HFS receipt,
> use a consensus-node query:
>
> ```bash
> # via hiero-sdk-python (FileContentsQuery) — the canonical path
> python -c "from hiero_sdk_python import *; ... FileContentsQuery().set_file_id(FileId.from_string('0.0.10215927')) ..."
> ```
>
> Browse: <https://hashscan.io/testnet/file/0.0.10215927>

## 4. EIP-191 signature (off-chain, cross-language)

Every forecast is signed (EIP-191). The verifier is a 5-line script: `node verify.js receipt.json`.
(The `agentproof/` verifier and a sample receipt ship with the full source; this repo carries the
submission UI and the proof pointers.)

## 5. Live public endpoint (x402, no auth)

The service is live. Anyone can check it in two commands:

```bash
# service health
curl -s https://ialanreynoso.tail3a9281.ts.net/health

# ask for a forecast → HTTP 402 with x402 requirements (payTo 0.0.10107589, 100000 tinybar HBAR)
curl -s https://ialanreynoso.tail3a9281.ts.net/v1/forecast?question=Will%20ETH%20hit%2010k%20in%202026%3F
```

Paying triggers the real flow — **verified end-to-end on Sep 5, 2026, twice** (once locally, once
through the public endpoint): the client (an agent wallet, account `0.0.10381472`) sends a
partially-signed Hedera TransferTransaction with the **Blocky402 facilitator as fee payer**
(`POST /verify` → valid, `POST /settle` → consensus SUCCESS), and the service returns the signed
forecast + a payment audit anchor on HCS.

| What happened | Proof (clickable) |
|---|---|
| Agent wallet created on testnet (5 HBAR) | [account 0.0.10381472](https://hashscan.io/testnet/account/0.0.10381472) |
| Settlement #1 (facilitator paid the network fee) | [0.0.7162784@1788631480.119182348](https://hashscan.io/testnet/transaction/0.0.7162784@1788631480.119182348) |
| Settlement #2 (via the public internet endpoint) | [0.0.7162784@1788631598.935375690](https://hashscan.io/testnet/transaction/0.0.7162784@1788631598.935375690) |
| Full request/response evidence (verdicts PASS and BLOCKED, signed) | [docs/x402_paid_evidence_20260905-120631.json](docs/x402_paid_evidence_20260905-120631.json) · [120834](docs/x402_paid_evidence_20260905-120834.json) |
| Payment audit anchors on HCS | [topic 0.0.10374210](https://hashscan.io/testnet/topic/0.0.10374210) (messages `tipo: x402-payment-audit`) |

To pay yourself: clone the repo and run `python scripts/ethonline/pay_x402.py --question "..." --url https://ialanreynoso.tail3a9281.ts.net` with a funded testnet account, or build the
payment payload with `@x402/hedera` (the same wire format: x402 v2, scheme `exact`,
`network: hedera:testnet`, `asset: 0.0.0`, `extra.feePayer: 0.0.7162784`).

---

*This file documents exactly what a judge can click or run. If something here 404s or fails, it's a bug — not an excuse.*
