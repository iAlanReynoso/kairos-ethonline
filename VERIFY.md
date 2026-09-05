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

---

*This file documents exactly what a judge can click or run. If something here 404s or fails, it's a bug — not an excuse.*
