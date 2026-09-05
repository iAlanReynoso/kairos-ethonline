# Kairos 🔮 — Signed Forecast Oracle on Hedera

**A disciplined AI forecasting agent that signs every decision, anchors it on Hedera Consensus Service,
and lets the network execute the next action — no keeper.**

> Live in Metaculus tournaments ($0 at risk). ETHOnline 2026 · track ♻️ **Continuity** · partners
> **Hedera** (x402 + Continuity), **The Graph** (AI use case), **Bazantic** (agentic recipes).

---

## What this is

For any question Kairos returns an explicit **BET / PASS / BLOCKED** with a human-readable reasoning
trace, **signs** it (EIP-191), and **anchors** the digest to Hedera Consensus Service — so "we said
this *before* the close" is a fact on a mirror node, not a promise. The next action is a **scheduled
transaction executed by the network itself**: no cron, no keeper.

It competes **live, fully automated, with $0 at risk** in Metaculus's AI-bot tournament ($50K,
bot-only) and the Cup. It **refuses good-looking edges** when they fail its risk discipline — and it
shows the refusal, signed.

---

## Before / After — the ♻️ Continuity line

| Before (pre-existing, on Hedera — Aug 2026) | After (new in this window, Sep 4–16) |
|---|---|
| Proof-of-concept spike (de-risking the SDK): account `0.0.10107589` · topic `0.0.10114138` · scheduled tx `0.0.10114149` **executed by the network** | **Production integration**: forecast digests anchored to HCS (Sept timestamps) · next action scheduled on-chain · HFS receipt with SHA-256 · **x402 pay-per-forecast** |
| Forecasts signed EIP-191, verifiable off-chain | Payment audit trail in HCS · recurring access via scheduled transactions |

> The August objects were the proof-of-concept spike. The September work integrates HCS anchoring +
> Schedule execution + HFS receipts + x402 into the production pipeline. Every object above is clickable on Hashscan.

---

## Proof links (each claim → clickable evidence)

| Claim | Proof |
|---|---|
| Forecast digests anchored pre-close | [HCS topic `0.0.10213059`](https://hashscan.io/testnet/topic/0.0.10213059) · [mirror node](https://testnet.mirrornode.hedera.com/api/v1/topics/0.0.10213059/messages) |
| Pre-existing spike executed by the network | [Schedule `0.0.10114149`](https://hashscan.io/testnet/schedule/0.0.10114149) · [Topic `0.0.10114138`](https://hashscan.io/testnet/topic/0.0.10114138) |
| Receipt on HFS | [File `0.0.10215927`](https://hashscan.io/testnet/file/0.0.10215927) |
| EIP-191 signature verifiable | `node verify.js receipt.json` (see [VERIFY.md](VERIFY.md)) |

---

---

## Partner integrations (Hedera + The Graph + Ledger)

We apply to three partner prizes. For each, we document exactly how we used their tools and our
feedback — see [PARTNERS.md](PARTNERS.md). Summary:

| Partner | What we use | Evidence |
|---|---|---|
| **Hedera** | HCS (anchor) + Schedule Service (no-keeper) + HFS (receipt) | topic 0.0.10213059 · schedule 0.0.10114149 · file 0.0.10215927 |
| **The Graph** | Messari Standardized Subgraphs as live evidence for the committee | Subgraph Studio API key (live, never mocked) |
| **Ledger** | Key Ring + device confirmation on the BLOCKED/high-risk path | wallet-cli ring as key backend |

## How it works

```
question → multi-source research (GDELT + Wikipedia + market price)
        → committee of 5 cross-lab LLMs (log-odds pooling, outlier trimming)
        → Platt calibration (out-of-sample, anti-degradation guard)
        → risk discipline (fractional Kelly + hard drawdown / daily-loss gates)
        → BET / PASS / BLOCKED (reasoning trace) → EIP-191 signature
        → HCS anchor (pre-close) → scheduled execution of the next action (no keeper)
```

---

## AI attribution (required by the track)

The engine is AI by design: a committee of cross-lab LLMs produces every decision, fully automated
(DeepSeek v4-flash is the primary frontier model since Sep 2). Development is also AI-assisted under
human supervision — the commit history is the audit trail. We do not claim hand-written code where AI
did the work; the live tournament results are the verifiable evidence of what the system actually does.

---

## Security & boundaries

- **Bounded agent**: read/analyse freely; write (anchor, schedule, pay) only within declared policy and caps.
- **Claim boundaries**: no x402 monetization in production yet (the pay-per-forecast is the *new work*
  of this window); no invented traction; $0 at risk.
- **Keys** live in env vars, never committed; testnet only.

---

*MIT — see [LICENSE](LICENSE). Not financial advice. Testnet demo.*
