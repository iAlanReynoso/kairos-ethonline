"""
agentproof — accountability drop-in para agentes de IA (5 líneas, $0, sin token).

    from agentproof import Attestor
    kit = Attestor()                                  # identidad del agente (clave eth)
    receipt = kit.attest("BTC>100k EOY", 0.72, "flujos on-chain + ETF...")   # firma su razonamiento
    assert Attestor.verify(receipt)                   # cualquiera lo verifica OFFLINE, $0
    rep = kit.calibration([0.72, 0.4], [1, 0])        # reputación 0-100 (Brier, estilo Numerai)

El wedge: la reputación de ERC-8004 está empíricamente rota (Sybil). agentproof la hace
= calibración VERIFICABLE + skin-in-the-game. Neutral: no atás a ningún framework ni chain.
"""
from agentproof.core import Attestor, Receipt, brier, calibration_score

__all__ = ["Attestor", "Receipt", "brier", "calibration_score"]
__version__ = "0.1.0"
