# SPECS.md — spec-driven artifacts (ETHOnline rules E34)

> If you use spec-driven workflows, you must include all spec files, prompts, and planning
> artifacts in your submission repository. — this file is that disclosure, with the actual
> operational specs.

## 1. Committee spec (COMMITTEE_SPEC)

```
deepseek:deepseek-v4-flash,
openrouter:anthropic/claude-opus-5,
openrouter:openai/gpt-5.6-luna,
?zai:glm-4.7-flash
```

Four independent models → one probability each → log-odds pooling with outlier trimming.
`?` = optional member (skipped if the provider is down; the forecast reports the n actually used).
DeepSeek is primary (migrated from Gemini on Sep 2, 2026; thinking mode disabled to keep JSON
deterministic).

## 2. Research stage spec

Sources: **GDELT** (news) + **Wikipedia** (base knowledge) + **market price** (live). Later in the
window: **The Graph Messari Standardized Subgraphs** as on-chain evidence (live data only — mocked/
local/static datasets are explicitly excluded by the partner rules).

## 3. Decision & risk gates (the discipline)

```
fractional Kelly alpha = 0.25
ladder: $2,000 → $10,000 (capital only moves with explicit human authorization)
hard drawdown gate: 15%
daily loss gate: 5%
min edge gate: EV < 3σ → PASS (refuse)
verdict: BET / PASS / BLOCKED (always shown, always signed)
```

The system publishes refusals — including honest negative peer scores — instead of hiding them.
That refusal is the demo: a forecaster that says 'no' with a signed trace.

## 4. The pre-existing → new line (Continuity)

**Before (Aug 2026, on Hedera):** proof-of-concept spike — account `0.0.10107589`, topic
`0.0.10114138`, scheduled transaction `0.0.10114149` executed by the network (SDK de-risking).

**New in this window (Sep 4–16, 2026):**
1. production HCS anchoring of every forecast digest (topic `0.0.10374210`, live Sept timestamps)
2. x402 pay-per-forecast endpoint, live on Hedera testnet, settlement via Blocky402 + payment
   audit trail on HCS
3. public HTTP facade (health + x402) reachable without an API key
4. The Graph live on-chain evidence stage for the committee (in progress)
5. Ledger Key Ring + device-confirmation in front of the high-risk path (in progress)
6. the public demo UI (this repo) with the full decision trace per answer

## 5. Honesty policy (load-bearing)

- 'no pude mirar' ≠ 'no hay nada': surfaces never claim more than they verified.
- No invented traction, no mocked data, no fabricated users. $0 at risk in tournaments.
- Every on-chain claim in this repo is clickable on Hashscan or the mirror node.

