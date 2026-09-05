"""
agentproof CLI — drop-in accountability para agentes, usable por un TERCERO sin escribir código.

    python -m agentproof attest  --claim "BTC>100k EOY" --confidence 0.72 --reasoning "ETF..." --out r.json
    python -m agentproof verify  r.json           # verificación OFFLINE paso a paso ($0, sin red)
    python -m agentproof score   --preds 0.7,0.4  --outcomes 1,0
    python -m agentproof demo                      # el wedge en 30s, con tamper visible

Zero deps extra (solo argparse + el stack eth ya requerido). El comando `verify` reproduce la
CRIPTOGRAFÍA a la vista —recomputa el digest keccak-256 y recupera al firmante del EIP-191— para
que un ESCÉPTICO confirme el receipt sin confiar en nuestro código ni en la red.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from eth_account import Account
from eth_account.messages import encode_defunct
from eth_hash.auto import keccak

from agentproof.core import Attestor, CanonicalError, brier, calibration_score, canonical_string

# ── El SPEC de canonicalización (reimplementable en cualquier lenguaje — ver SPEC.md) ──
#   canonical = JSON de {claim, confidence_bp, meta, reasoning, ts_ms} con claves ordenadas y
#               sin espacios (separators (",",":")). TODO número (confidence y los de meta) pasa
#               por el entero escalado half-up del SPEC §1.1 — nunca por format/toFixed, que
#               divergen entre Python y JS en -0.0, |x|≥1e21 y los empates exactos.
#   digest    = "0x" + keccak256(canonical_utf8).
#   firma     = EIP-191 personal_sign del string canonical (encode_defunct(text=canonical)).


def _canonical_from_receipt(d: dict[str, Any]) -> str:
    """Reconstruye el string canónico EXACTO desde un receipt cargado (vía el SPEC único de core)."""
    return canonical_string(d["claim"], d["confidence"], d["reasoning"], d["ts_ms"], d.get("meta") or {})


def _cmd_attest(args: argparse.Namespace) -> int:
    kit = Attestor(args.key)
    receipt = kit.attest(args.claim, float(args.confidence), args.reasoning or "")
    out = json.dumps(receipt.to_dict(), ensure_ascii=False, indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(out + "\n")
        print(f"receipt firmado por {receipt.signer} → {args.out}")
        if args.key is None:
            print(f"(clave efímera; para una identidad PERSISTENTE pasá --key {kit.private_key})")
    else:
        print(out)
    return 0


def _cmd_verify(args: argparse.Namespace) -> int:
    """Verifica un receipt OFFLINE mostrando la matemática — el escéptico no confía, comprueba."""
    with open(args.file, encoding="utf-8") as fh:
        d = json.load(fh)

    try:
        canonical = _canonical_from_receipt(d)
    except CanonicalError as exc:
        # Doctrina B: un receipt con números fuera del dominio del SPEC §1.1 no es "una firma que
        # no matchea" — es un receipt que NINGÚN lenguaje puede canonizar igual. Se dice por qué.
        print(f"❌ INVÁLIDO — receipt no canonizable: {exc}" if not args.quiet else "INVALID")
        return 1
    recomputed_digest = "0x" + keccak(canonical.encode("utf-8")).hex()
    digest_ok = recomputed_digest.lower() == str(d["digest"]).lower()

    signer_ok = False
    recovered = "<error>"
    try:
        sig = bytes.fromhex(str(d["signature"]).removeprefix("0x"))
        recovered = Account.recover_message(encode_defunct(text=canonical), signature=sig)
        signer_ok = recovered.lower() == str(d["signer"]).lower()
    except Exception as exc:  # un receipt corrupto es INVALID, no un crash
        recovered = f"<no recuperable: {exc}>"

    ok = digest_ok and signer_ok
    if not args.quiet:
        print("  agentproof · verificación OFFLINE ($0, sin red)\n")
        print(f"  canonical  : {canonical}")
        print(f"  digest recomputado : {recomputed_digest}")
        print(f"  digest del receipt : {d['digest']}")
        print(f"    → keccak-256 coincide : {'SÍ' if digest_ok else 'NO'}")
        print(f"  firmante declarado : {d['signer']}")
        print(f"  firmante recuperado: {recovered}  (EIP-191 recover)")
        print(f"    → la firma recupera al firmante : {'SÍ' if signer_ok else 'NO'}\n")
        print(f"  VEREDICTO: {'✅ VÁLIDO — íntegro y auténtico' if ok else '❌ INVÁLIDO — alterado o mal firmado'}")
        # Claim ACOTADO a lo probado: SPEC §1.1 fija el dominio numérico y `attest` no firma
        # fuera de él. Antes decía "cualquier lenguaje" a secas y un receipt con bss=-0.0 lo
        # refutaba en 30 segundos con `node agentproof/verify.js`.
        print("  (reproducible en cualquier lenguaje: keccak256 del canonical + ecrecover del")
        print("   personal_sign; números por SPEC §1.1 — finitos, |x| ≤ 9.0e7, 8 decimales)")
    else:
        print("VALID" if ok else "INVALID")
    return 0 if ok else 1


def _cmd_score(args: argparse.Namespace) -> int:
    preds = [float(x) for x in args.preds.split(",") if x.strip()]
    outs = [int(x) for x in args.outcomes.split(",") if x.strip()]
    b = brier(preds, outs)
    rep = calibration_score(preds, outs)
    print(f"  n={len(preds)}  Brier={b:.4f}  →  reputación {rep}/100")
    print("  (menor Brier = mejor calibrado; reputación = 100·(1−2·Brier), clamp 0-100)")
    return 0


def _cmd_demo(_args: argparse.Namespace) -> int:
    from agentproof.demo import _run

    _run()
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="agentproof", description=__doc__.strip().splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("attest", help="firmar una decisión (keccak+EIP-191, $0, offline)")
    a.add_argument("--claim", required=True)
    a.add_argument("--confidence", required=True, help="prob. en [0,1]")
    a.add_argument("--reasoning", default="")
    a.add_argument("--key", default=None, help="clave privada eth (default: identidad efímera)")
    a.add_argument("--out", default=None, help="guardar el receipt JSON")
    a.set_defaults(fn=_cmd_attest)

    v = sub.add_parser("verify", help="verificar un receipt OFFLINE, paso a paso (exit 0=válido)")
    v.add_argument("file", help="ruta a un receipt JSON")
    v.add_argument("-q", "--quiet", action="store_true", help="solo VALID/INVALID")
    v.set_defaults(fn=_cmd_verify)

    s = sub.add_parser("score", help="reputación por calibración desde predicciones + resultados")
    s.add_argument("--preds", required=True, help="probs separadas por coma, ej. 0.7,0.4,0.9")
    s.add_argument("--outcomes", required=True, help="0/1 separados por coma, ej. 1,0,1")
    s.set_defaults(fn=_cmd_score)

    d = sub.add_parser("demo", help="el wedge en 30s (calibrado vs fanfarrón + tamper)")
    d.set_defaults(fn=_cmd_demo)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.fn(args))


if __name__ == "__main__":
    sys.exit(main())
