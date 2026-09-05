# CODE.md — qué código es nuevo en esta ventana (Continuity, regla E6)

> Regla global de Continuity: *All new parts of extending an existing project must remain open
> source.* Este repo contiene el trabajo NUEVO de la ventana (4–16 sep 2026) + los módulos
> necesarios para verificarlo. El motor pre-existente (research/commitment engine, histórico
> desde antes del hackathon) sigue en el repositorio interno y está declarado como pre-existente
> en el README before/after.

## Nuevo en esta ventana (lo que juzga el track Continuity)

| Path | Qué es | Servicio Hedera que usa
|---|---|---|
| scripts/serve_forecast.py | Servidor de forecast: research → comité 4 modelos → Platt → Kelly → EIP-191 → HCS. Endpoint x402 /v1/forecast con settlement REAL via Blocky402 (/verify + /settle). | HCS + x402
| scripts/serve_public.py | Fachada pública (solo /health + /v1/forecast; el POST gratis queda privado). | —
| scripts/pay_x402.py | El CLIENTE que paga: wallet del agente creada on-chain, TransferTransaction parcialmente firmada con el facilitator como fee payer, pago y verificación end-to-end. | (cliente) + Blocky402
| kairos/hedera/ | Módulos de producción: anchor.py (HCS), schedule.py (Schedule Service), hfs.py (File Service), keys.py. | HCS + Schedule + HFS
| kairos/pay/hedera_x402.py | Requirements x402 v2 del scheme exact de Hedera + audit trail de pagos en HCS. | HCS + x402
| kairos/graph_evidence.py | Evidencia on-chain LIVE de The Graph (subgraphs estandarizados Messari en la red descentralizada) como input del comité. Nunca mockea: sin GRAPH_API_KEY se declara ausente. | The Graph
| kairos/ledger_trust.py | Gate human-in-the-loop: apuestas ≥ umbral exigen confirmación en dispositivo Ledger (Key Ring). | Ledger
| scripts/graph_ab.py | Arnés A/B: mide el efecto causal de la evidencia The Graph sobre el Brier del comité (mismas preguntas, con/sin). | The Graph

## Pre-existente (declarado, no juzgado como nuevo)

- agentproof/ — el firmador EIP-191 (SPEC.md incluido). Existía antes del evento (las firmas
  pre-evento ya lo usaban). Se incluye para que cualquier juez verifique firmas con
  node agentproof/verify.js.
- El motor de research/risk completo (Kelly-α, gates, Platt) — pre-existente, en el repo interno.

## Cómo correrlo

```bash
pip install aiohttp 'hiero-sdk-python==0.2.10'  # o: uv pip install ...
export HEDERA_ACCOUNT_ID=0.0.XXXXX HEDERA_PRIVATE_KEY=<DER> KAIROS_AGENT_SIGNER_KEY=<0x..>
export DEEPSEEK_API_KEY=... OPENROUTER_API_KEY=...   # comité
python scripts/serve_forecast.py --port 8787        # server completo (necesita el motor interno)
python scripts/serve_public.py --port 8788          # fachada pública
python scripts/pay_x402.py --question 'Will ETH hit 10k in 2026?' --url http://127.0.0.1:8788
```

> El server importa el motor interno (kairos.agent.*) que es pre-existente; el endpoint vivo
> está publicado en README para verificación sin correr nada.

