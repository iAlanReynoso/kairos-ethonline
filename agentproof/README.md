# agentproof — accountability drop-in para agentes de IA

**El problema (validado empíricamente):** el Reputation Registry de ERC-8004 está roto —
de ~170k agentes, 3–15% tienen endpoint vivo y 60–90% de los reviews son Sybil. La reputación
de agentes hoy es teatro manipulable.

**El wedge:** reputación = **calibración verificable + skin-in-the-game**, no reviews. Numerai lo
probó con dinero institucional ($950M AUM). `agentproof` te da ese primitivo en 5 líneas, gratis,
sin token, sin atarte a ningún framework ni chain.

```python
from agentproof import Attestor

kit = Attestor()                                    # identidad del agente (clave eth; portable)
receipt = kit.attest(                               # firma su razonamiento (keccak + EIP-191, $0, offline)
    claim="BTC > $100k by 2026-12-31",
    confidence=0.72,
    reasoning="ETF inflows + on-chain accumulation...",
)
assert Attestor.verify(receipt)                     # CUALQUIERA lo verifica offline, sin red, sin clave
rep = kit.calibration([0.72, 0.41, 0.90], [1, 0, 1])# reputación 0-100 (Brier) — su track record real
```

- **$0 / offline / sin token:** firma local (EIP-191), verificación sin red. Zero gas.
- **Anti-Sybil:** la reputación es el historial de calibración de UNA identidad con stake, no reviews.
- **Compatible con el tooling Ethereum:** al firmar con EIP-191 + keccak256, cualquiera verifica un receipt con `ethers.verifyMessage` o Solidity `ecrecover`, sin nuestro código. Verificador JS de referencia en `verify.js` (**probado bit-a-bit** contra una firma Python); formato exacto en `SPEC.md`.
- **Alcance EXACTO del "verificable en cualquier lenguaje"** (medido, no prometido): vale para todo receipt que `attest()` acepte firmar — o sea, con los números de `meta` finitos y `|x| ≤ 9.0e7`, comprometidos con **8 decimales** de precisión (`SPEC.md` §1.1). Fuera de ese dominio `attest()` **rechaza y no firma**, en vez de emitir un receipt que dice válido en Python y roto en JS. Probado con 17 917 valores fuzzeados verificados en Python **y** en JS con `ethers`: 0 divergencias (con la regla anterior, `format('.8f')` vs `toFixed(8)`, divergían 2 038 — el 11%).
- **Neutral por diseño:** no ata a ningún framework ni chain. Integraciones nativas a ERC-8004 / x402 / EAS y anclaje on-chain están en el **roadmap** (hoy: firma + verificación offline, $0, sin token).

## CLI — usable por un TERCERO sin escribir código

```bash
python -m agentproof demo                       # el wedge en 30s (calibrado vs fanfarrón + tamper)
python -m agentproof attest --claim "BTC>100k EOY" --confidence 0.72 \
    --reasoning "ETF inflows" --out receipt.json # firma una decisión → receipt.json
python -m agentproof verify receipt.json         # verificación OFFLINE paso a paso (exit 0=válido)
python -m agentproof score --preds 0.7,0.4,0.9 --outcomes 1,0,1   # reputación por calibración
```

**Auto-verificable por un escéptico:** `verify` no devuelve un "confiá en mí" booleano — recomputa el
digest keccak-256 y recupera al firmante del EIP-191 **a la vista**, imprimiendo el string canónico exacto.
Alterar un solo byte del receipt rompe el digest **y** la recuperación de la firma → `INVÁLIDO`, exit 1.
Es reproducible en cualquier lenguaje (keccak256 del canonical + ecrecover del `personal_sign`), sin red.

Comprobalo vos mismo, en JS, sin nuestro Python:

```bash
mkdir -p /tmp/agentproof-js && cd /tmp/agentproof-js && npm i ethers   # el repo no trae node_modules
cd /ruta/al/repo && python -m agentproof attest --claim "BTC>100k EOY" --confidence 0.72 --out /tmp/r.json
NODE_PATH=/tmp/agentproof-js/node_modules node agentproof/verify.js /tmp/r.json   # exit 0 = válido
```

Parte de **Kairos** (agente cuant calibrado, compitiendo vivo en Metaculus). El leaderboard de
calibración con staking es la fase siguiente.
