# Kairos Oracle 🔮

**A disciplined AI forecasting agent — competing live in real tournaments, with signed, verifiable decisions.**

> *Baseline (pre-hackathon): what actually existed before the ETHOnline 2026 build window.
> The Hedera integrations are the new work — see the "Before / After" section added in September.*

---

## What this is (honest baseline, July 2026)

Kairos is a forecasting agent that competes **live, fully automated, with $0 capital at risk** in real
forecasting tournaments — today in Metaculus's **AI-bot tournament ($50K, bot-only)** and the Metaculus Cup.

For any question it produces an explicit **BET / PASS / BLOCKED** decision with a human-readable
reasoning trace — and **signs** it (EIP-191), so the provenance of every forecast is verifiable
off-chain by anyone, cross-language (`agentproof/` + `verify.js`).

The moment that matters: it **refuses good-looking edges** when they fail its risk discipline —
and it shows the refusal, signed.

## How it works

```
question → multi-source research (GDELT news + Wikipedia base rates)
        → committee of cross-lab LLMs (aggregated by log-odds pooling)
        → Platt calibration against resolved outcomes
        → risk discipline (fractional Kelly + hard drawdown / daily-loss gates)
        → BET / PASS / BLOCKED (reasoning trace) → EIP-191 signature → verifiable receipt
```

- **Committee of cross-lab LLMs** — Google Gemini lineages + models via OpenRouter + a GLM
  tie-breaker on disagreement — aggregated by log-odds pooling.
- **Multi-source research** — GDELT news + Wikipedia base rates, injected per question.
- **Calibration** — Platt scaling fitted out-of-sample (cross-validated guard) on resolved outcomes.
- **Risk discipline** — fractional Kelly + hard drawdown / daily-loss gates → the BLOCKED that
  LLM-YOLO agents don't have.
- **Verifiable** — every forecast is signed (EIP-191) and machine-checkable with a 5-line verifier.

## What is NOT here (deliberately)

- **No on-chain anchoring yet** — the Hedera Consensus Service integration is the *new work* of
  the hackathon window (September 2026), not part of this baseline.
- **No x402 monetization** — an earlier draft pitch mentioned pay-per-forecast; it was never
  deployed. The agent competes in judged arenas, it does not sell calls.
- **No EAS attestations** — same story: drafted, never shipped.

## Track record (verifiable, not claimed)

- Competes **today** in Metaculus's AI-bot tournament and Cup — the public leaderboard shows its
  official peer score, updated by the platform (we show it even when it's negative — that's the
  point of a reputation you can *check*).
- Every submitted forecast leaves a signed receipt; the system's weekly self-score against public
  data (FRED/Cboe) is in the repo's `data/series_scores.jsonl`.

## License

MIT — see `LICENSE`.

---

*This README documents the state of the project **before** the ETHOnline 2026 build window
(4–16 September 2026). The Hedera integrations (HCS anchoring + Schedule Service execution) are
the new work, documented separately with the same before/after separation the Continuity track asks for.*
