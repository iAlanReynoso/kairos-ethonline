# Kairos Oracle 🔮

**An AI forecasting agent that signs its calibrated bets on-chain and sells them via x402.**

> *The only forecasting agent that shows you — signed and verifiable — **why** it says no.*

Built for **ETHOnline 2026**. Battle-tested: forecasts live in Metaculus AI tournaments today.

---

## The thesis

Every "AI trading agent" tells you *what* to bet. Kairos produces a **disciplined, auditable decision** —
and proves it. For any market or question it returns an explicit **BET / PASS / BLOCKED** with a
human-readable reasoning trace, then **signs** the decision (EIP-712) and **anchors** an attestation
**on-chain** (EAS). You buy an audited decision with verifiable risk discipline, not an opaque LLM opinion.

The moment that matters: watch it **refuse a +36% edge** because the market is too illiquid — signed,
on-chain, impossible to fake.

## How it works

```
signals → Bayesian posterior (σ) → EV/σ/GL gates → Kelly-α sizing → risk envelope
        → BET / PASS / BLOCKED (with reasoning trace)
        → EIP-712 signature → x402 pay-per-forecast → EAS on-chain attestation
```

- **Committee of 5 cross-lab LLMs** — Gemini 2.5 Pro/Flash, Gemini 3 Flash, Claude Sonnet 5,
  + a GLM tie-breaker — aggregated by **log-odds pooling with outlier trimming**.
- **Multi-source research** — GDELT news + Wikipedia base rates, injected per question.
- **Calibration** — Platt scaling against resolved outcomes (decoupled, tournament-native).
- **Risk discipline** — fractional Kelly + hard drawdown / daily-loss gates → the BLOCKED that others lack.
- **Verifiable** — keccak256 digest + EIP-712 signature, anchored via the Ethereum Attestation Service.
- **Monetized** — x402 (HTTP-402): a client pays a USDC micro-fee and receives the signed forecast.

## Quickstart

```bash
kairos agent demo          # the reasoning trace: BET / PASS / BLOCKED, live
kairos agent x402-demo     # full flow: decision → sign → x402 pay → on-chain attestation
kairos agent x402-serve    # real HTTP paywall: GET /forecast → 402 → pay → 200 signed
kairos agent anchor        # anchor the signed decision on-chain (EAS, Base Sepolia)
```

## Status

- 🏆 Competing live in **Metaculus** — AI Benchmark (FutureEval, $50K) + Metaculus Cup.
- 🔮 **ETHOnline 2026** hacker — hack Sept 4-16.
- 🛡️ Fail-closed by design ("Doctrine B"): any error degrades to neutral, never crashes.

## Partner tech

Ethereum Attestation Service (EAS) · x402 · EVM (Base) · eth-account (EIP-712).
Sponsor-specific integrations land when ETHOnline bounties are announced (late August).

---

*Not financial advice. Testnet demo. Secrets live only in a gitignored `.env` — never committed.*
