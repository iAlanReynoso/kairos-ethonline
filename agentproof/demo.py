"""
Demo del WEDGE — `python -m agentproof demo` (o `python -m agentproof.demo`).

Cuenta la historia en 30 segundos y la deja AUTO-VERIFICABLE por un escéptico:
  1. reputación = CALIBRACIÓN verificable, no reviews (que son Sybil);
  2. cada predicción va FIRMADA (keccak+EIP-191, $0, offline);
  3. alterar un solo byte ROMPE la verificación —a la vista— así que no se puede mentir el track record;
  4. exporta un receipt real a `agentproof_receipt.json` que cualquiera re-verifica sin confiar en este código:
        python -m agentproof verify agentproof_receipt.json
"""
from __future__ import annotations

import json
from pathlib import Path

from agentproof import Attestor


def _run() -> None:
    print("\n  🦄 agentproof — reputación de agentes = calibración verificable (anti-Sybil)\n")

    # Dos agentes con identidad propia; cada uno firma sus predicciones ($0, offline).
    calibrado = Attestor()      # honesto: confianza ~ acierto
    fanfarron = Attestor()      # overconfident/Sybil: dice 0.95 siempre, acierta la mitad

    # (predicción, resultado real) para 6 eventos
    verdad = [1, 0, 1, 1, 0, 1]
    p_calibrado = [0.80, 0.25, 0.70, 0.90, 0.30, 0.75]
    p_fanfarron = [0.95, 0.95, 0.95, 0.95, 0.95, 0.95]

    first_receipt = None
    for i, (pc, pf, _o) in enumerate(zip(p_calibrado, p_fanfarron, verdad, strict=True)):
        rc = calibrado.attest(f"evento#{i}", pc, "modelo calibrado")
        rf = fanfarron.attest(f"evento#{i}", pf, "siempre seguro")
        assert Attestor.verify(rc)   # firmas verificables por cualquiera
        assert Attestor.verify(rf)
        if first_receipt is None:
            first_receipt = rc

    rep_c = calibrado.calibration(p_calibrado, verdad)
    rep_f = fanfarron.calibration(p_fanfarron, verdad)

    print(f"  Agente CALIBRADO  {calibrado.address[:10]}…  → reputación {rep_c}/100  ✅ confiable")
    print(f"  Agente FANFARRÓN  {fanfarron.address[:10]}…  → reputación {rep_f}/100  ⚠️  expuesto")
    print("\n  Ambos firmaron su razonamiento (keccak+EIP-191, $0, verificable offline).")
    print("  La reputación NO se puede fakear con reviews Sybil: es su Brier real, con skin-in-the-game.")

    # ── Prueba anti-mentira: alterar el contenido ROMPE la firma (a la vista) ──
    assert first_receipt is not None
    tampered = first_receipt.__class__(**{**first_receipt.to_dict(), "confidence": 0.99})
    print("\n  Prueba de que no se puede mentir el track record:")
    print(f"    receipt original   → verify = {Attestor.verify(first_receipt)}  (íntegro)")
    print(f"    subo 0.80 → 0.99   → verify = {Attestor.verify(tampered)}  (detectado: la firma no cierra)")

    # ── Deja un artefacto que el escéptico re-verifica SIN confiar en este código ──
    out = Path("agentproof_receipt.json")
    out.write_text(json.dumps(first_receipt.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\n  Receipt real exportado → {out}")
    print(f"    verificalo vos mismo:  python -m agentproof verify {out}")
    print("  ⇒ El hueco EXACTO de ERC-8004, en 5 líneas de SDK.\n")


if __name__ == "__main__":
    _run()
