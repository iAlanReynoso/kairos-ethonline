# AI attribution — ETHOnline 2026 rules, E32/E33

*Clearly document in your submission where and how AI tools were used in the project.*
Kairos is an AI forecasting agent: AI is the product, so we document it exactly — no hand-waving.

## 1. The product itself (AI by design)

| Component | What AI does | Model/provider (as of Sep 5) |
|---|---|---|
| Research stage | pulls live evidence (GDELT news, Wikipedia, market price) and summarizes factors | `deepseek:deepseek-v4-flash` (primary; DeepSeek API, thinking mode disabled for deterministic JSON) |
| Forecast committee | 4 independent models each produce a probability; aggregated with log-odds pooling + outlier trimming | `deepseek:deepseek-v4-flash` · `openrouter:anthropic/claude-opus-5` · `openrouter:openai/gpt-5.6-luna` · `zai:glm-4.7-flash` (optional) |
| Calibration | Platt scaling refit on out-of-sample scores, with anti-degradation guard | statistical, not generative AI |
| Decision | fractional Kelly (α=0.25) + hard risk gates (drawdown 15%, daily loss 5%) | rule-based, deterministic |
| Signing/anchoring | EIP-191 signature + HCS anchor + scheduled next action | cryptography/ledger, no AI |

## 2. The development process (AI-assisted, human-supervised)

- The human (Alan) sets direction, reviews, and approves; the assistant (DeepSeek harness) drafts
  code, docs, and runbooks. Every decision is dated and logged in the workspace (`docs/ethonline/`,
  `nodes/`).
- **Nothing is claimed hand-written that AI produced.** The commit history is the audit trail.
- Spec-driven workflow artifacts (prompts, committee spec, risk config) live in this repo — see
  [SPECS.md](SPECS.md).

## 3. What is NOT AI

- The risk gates, sizing math, and the honesty policy (the system publishes refusals — negative
  peer scores included — instead of hiding them).
- The EIP-191 signer, the Hedera HCS/Schedule/HFS integration, and the x402 payment path.

