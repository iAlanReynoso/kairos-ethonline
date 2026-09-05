# Partner integrations — how we used each tool

> ETHGlobal requires, for each partner prize selected: *"explain how you've used or integrated their
> tools, provide feedback, and share relevant comments."* This file is that record. Every claim points
> to clickable evidence (Hashscan / mirror node / code path).

---

## 1. Hedera — HCS + Schedule Service + HFS (+ x402)

**What we used:** Hedera Consensus Service (anchoring), Schedule Service (no-keeper execution),
Hedera File Service (receipt storage). SDK: `hiero-sdk-python` v0.2.10. Testnet.

**How it's integrated (evidence):**
| Service | What it does in Kairos | Proof |
|---|---|---|
| HCS | Forecast digest submitted *before* question close — consensus timestamp = anti-timing proof | [topic 0.0.10213059](https://hashscan.io/testnet/topic/0.0.10213059) · [mirror](https://testnet.mirrornode.hedera.com/api/v1/topics/0.0.10213059/messages) |
| Schedule Service | Next action executed **by the network** (no keeper) | [schedule 0.0.10114149](https://hashscan.io/testnet/schedule/0.0.10114149) |
| HFS | Full signed receipt on-ledger; SHA-256 anchored back to the topic | [file 0.0.10215927](https://hashscan.io/testnet/file/0.0.10215927) |

**Code path:** `src/kairos/hedera/` (anchor.py · schedule.py · hfs.py · keys.py).

**x402 (this window's new work):** pay-per-forecast endpoint returning HTTP 402 → HBAR payment →
forecast. Audit trail in HCS, recurring access via scheduled transactions. (The prior `src/kairos/pay/`
module was USDC/Base — being ported to HBAR/Hedera.)

**Feedback (asked by the form):**
- `hiero-sdk-python` v0.2.10: solid native-services coverage, but **`PrivateKey.from_string` with a raw
  32-byte hex mis-parses it as an Ed25519 seed and derives a *different* public key** — you must use the
  DER form (OID 2b8104000a). Documented trap; worth an upstream warning.
- Mirror node REST does **not** expose file contents on testnet (HFS verify needs `FileContentsQuery`).

---

## 2. The Graph — Standardized Subgraphs (Messari) as live evidence

**What we used:** The Graph as the **live on-chain data source** for crypto/protocol forecasts —
Messari Standardized Subgraphs (one shared schema across protocols), queried via Subgraph Studio.

**How it's integrated (evidence):**
- The forecasting committee consumes on-chain metrics (e.g. Uniswap/Aave/Lido volume, TVL) as evidence
  for crypto/protocol questions, in the research stage of the pipeline.
- A/B measured: does adding live Graph data improve calibration? (Platt/peer score on matched questions.)

**Code path:** `src/kairos/agent/research.py` (research stage) + a Graph adapter (this window).

**Feedback:** Standardized Subgraphs are the right abstraction — one query spans many protocols. The
continuity requirement "consume live data from a Graph provider" is satisfied via Subgraph Studio API key
(never mocked/local).

---

## 3. Ledger — Key Ring + device confirmation (human-in-the-loop)

**What we used:** Ledger Agent Stack — `wallet-cli ring` (Key Ring CLI) as the key backend for
high-risk actions, with **device confirmation in front of irreversible decisions**.

**How it's integrated (evidence):**
- Kairos already has a **BLOCKED** path: it refuses good-looking edges that fail risk gates. Ledger adds
  the hardware trust layer to exactly that boundary — a high-risk action (e.g. moving funds) now requires
  **device confirmation**, and secrets move onto the Key Ring instead of `.env`.
- Matches Ledger's Continuity ask: *"put a device confirmation in front of an action your product already
  performs"* and *"make wallet-cli ring the key backend for the .env files your repo already has."*

**Code path:** this window's build — a signer adapter behind the risk-gate decision.

**Feedback:** `npx skills add ledgerhq/agent-skills` + `npm i -g @ledgerhq/wallet-cli` install clean;
the DMK skills are instruction files an agent can wire up directly (good fit for spec-driven builds).

---

*This file is the record the submission form asks for. If a judge clicks any proof link and it 404s,
that's a bug — report it.*
