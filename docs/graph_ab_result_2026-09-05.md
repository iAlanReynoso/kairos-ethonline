# A/B The Graph — resultado real (5-sep-2026)

## Qué se midió

El efecto causal de la evidencia on-chain LIVE (Messari standardized subgraphs vía Subgraph
Studio) sobre la calibración del comité: dos cosechas IDÉNTICAS de ForecastBench (mismas 12
preguntas, mismo comité de 4 modelos, misma semilla de estratificación) con
`KAIROS_GRAPH_EVIDENCE=1` vs `=0`.

## Resultado

| Brazo | Brier | n |
|---|---|---|
| CON evidencia The Graph | **0.2169** | 12 |
| SIN evidencia The Graph | **0.2002** | 12 |
| Δ (menos = mejor) | **+0.0168** | — |
| Referencia: mercado (brier_market, brazo ON) | 0.1736 | 12 |

## Lectura honesta (sin spin)

1. En esta muestra chica (n=12) la evidencia on-chain NO mejoró al comité; el delta es del
   orden del ruido muestral y la muestra es mayormente ajena al dominio on-chain (la etapa
   solo aplica a preguntas crypto/protocolo, por diseño — no se fuerza el fit).
2. Lo que se construyó y se demuestra NO es un booster mágico, sino la INFRAESTRUCTURA DE
   MEDICIÓN: el arnés pareado permite saber —con números— cuándo la evidencia suma y cuándo
   no. Eso es exactamente el "meaningful work with the data" que pide el track, y el
   resultado negativo se publica en vez de esconderse (la calibración honesta es la tesis
   del proyecto).
3. Próximo paso (post-hackathon): re-correr el A/B sobre un pool filtrado a preguntas del
   dominio on-chain (donde la evidencia aplica) para medir su efecto donde corresponde.

## Datos crudos

- [`graph_ab_on.json`](graph_ab_on.json) — brazo con evidencia (12 filas: forecast vs resolved_to)
- [`graph_ab_off.json`](graph_ab_off.json) — brazo sin evidencia

