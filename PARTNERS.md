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

**x402 (this window's new work — LIVE, settled on-chain through Blocky402):** pay-per-forecast
endpoint returning HTTP 402 → HBAR payment → signed forecast. Audit trail in HCS.

Verified live (5-sep, twice — locally and via the public internet endpoint):

| Step | Proof |
|---|---|
| Agent wallet created on-chain (5 HBAR) | [0.0.10381472](https://hashscan.io/testnet/account/0.0.10381472) |
| Blocky402 /verify → valid (partially-signed TransferTransaction, fee payer 0.0.7162784) | facilitator [https://api.testnet.blocky402.com](https://api.testnet.blocky402.com/supported) |
| Blocky402 /settle → consensus SUCCESS (facilitator paid the network fee) | [settlement #1](https://hashscan.io/testnet/transaction/0.0.7162784@1788631480.119182348) · [settlement #2](https://hashscan.io/testnet/transaction/0.0.7162784@1788631598.935375690) |
| Signed forecast + HCS payment audit returned (verdicts PASS and BLOCKED, both honest) | [evidence JSONs](docs/x402_paid_evidence_20260905-120631.json) · [topic 0.0.10374210](https://hashscan.io/testnet/topic/0.0.10374210) |

Code: `kairos/pay/hedera_x402.py` (requirements v2, scheme exact, asset 0.0.0, feePayer),
`scripts/serve_forecast.py` (/verify+/settle reales antes de servir), `scripts/pay_x402.py` (el cliente).

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
- The forecasting committee consumes on-chain metrics (e.g. Uniswap/Aave volume, TVL) as evidence
  for crypto/protocol questions, in the research stage of the pipeline.
- **Live query verified 5-sep:** the gateway returned the latest uniswap-v3-ethereum daily snapshots
  (TVL ≈ $136.3B, daily volume ≈ $368M on the most recent snapshot) — real data, not fixtures. The
  stage feeds the committee prompt and the response's `fuentes` field reports `thegraph` only
  when the evidence was actually used.
- A/B measured (5-sep, n=12 matched questions, same committee, same seed): **Brier 0.2169 with the
  evidence vs 0.2002 without (+0.0168, market reference 0.1736)**. Honest read in
  [docs/graph_ab_result_2026-09-05.md](docs/graph_ab_result_2026-09-05.md) — on this small,
  mostly non-crypto sample the evidence did not help, and we publish the negative rather than hide
  it. What ships is the paired measurement infrastructure (and a domain-filtered re-run planned
  post-hackathon). Raw rows: [on](docs/graph_ab_on.json) / [off](docs/graph_ab_off.json).

**Code path:** `kairos/graph_evidence.py` — queries GraphQL LIVE contra la gateway de Subgraph
Studio con los subgraphs Messari en la red descentralizada (graph IDs del deployment.json oficial:
uniswap-v3-ethereum `4cKy6QQMc5tpfdx8yxfYeb9TLZmgLQe44ddW1G7NwkA6`, aave-v3-arbitrum
`4xyasjQeREe7PxnF6wVdobZvCw5mhoHZq3T7guRpuNPf`). El A/B se corre con `scripts/graph_ab.py`
(dos cosechas idénticas con KAIROS_GRAPH_EVIDENCE=1/0 y Brier pareado). Sin GRAPH_API_KEY la etapa
se declara ausente — never mocked.

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

**Code path:** `kairos/ledger_trust.py` + el gate cableado en el motor de decisión
(`AgentDecision.requires_device_signature`, opt-in vía KAIROS_LEDGER_MODE=1: toda apuesta BET ≥
umbral marca la decisión como pendiente de confirmación en dispositivo). `wallet-cli` v2.1.0
instalado y verificado (subcomando `ring`: init/encrypt/decrypt/keys/destroy, LKRP). El enroll del
dispositivo físico se hace con el hardware presente (before/after documentado en el repo).

**Track eligibility (from the source, developers.ledger.com/ethonline):** Track 01 "AI Agents x
Ledger" says "Start something new during the event" and "the track decides where you start from" →
it is the From-Scratch pool; as a Continuity project we compete in **Track 02 Continuity ($1,500)**,
whose ask we match literally (put a device confirmation in front of an action that previously had
none; make wallet-cli ring the key backend). We state this rather than guessing.

**Feedback (Ledger judges DX as much as code — "Every submission has to include feedback"):**
- Install experience: `npx skills add ledgerhq/agent-skills` + `npm i -g @ledgerhq/wallet-cli` is
  clean and fast (seconds). The CLI's JSON-first output is genuinely agent-friendly (no scraping).
- Gap found: `wallet-cli ring keys` fails with a generic "not initialized" error and no pointer to
  the `ring init` flow; a one-line hint (and an `init` dry-run mode) would save integrators a detour.
- Suggestion ("time-saver" for future integrators): a headless `ring init --key-id <name>` flag that
  derives the ring key without interactive prompts would make CI enrollment scriptable end-to-end.
- DMK skills are plain instruction files — ideal for spec-driven agent builds; we wired ours into the
  decision engine the same day.

---

*This file is the record the submission form asks for. If a judge clicks any proof link and it 404s,
that's a bug — report it.*
