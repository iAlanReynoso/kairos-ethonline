"""
agentproof.core — primitivo drop-in de accountability para agentes de IA.

Firma el razonamiento de CUALQUIER agente (keccak-256 + EIP-191, $0, offline, sin token) y mide su
CALIBRACIÓN (Brier). Neutral: no depende de ningún framework ni chain. El wedge de ERC-8004: la
reputación de un agente = calibración verificable + skin-in-the-game, resistente a Sybil.

Reutiliza la criptografía probada de Kairos (canonical → EIP-191 → recover). CERO gas, CERO red.
"""
from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass, field
from typing import Any

from eth_account import Account
from eth_account.messages import encode_defunct
from eth_hash.auto import keccak

__all__ = [
    "Attestor",
    "CanonicalError",
    "Receipt",
    "brier",
    "calibration_score",
    "canonical_number",
    "canonical_string",
]

CONFIDENCE_SCALE = 10000  # basis points: confidence se canoniza como ENTERO, no float.
META_DECIMALS = 8         # decimales fijos de TODO número de meta
META_SCALE = 10**META_DECIMALS

# ── Dominio numérico del canonical (SPEC §1) ─────────────────────────────────────────────────
# Fuera de este dominio NO se firma: se rompe ruidosamente. Antes se firmaba igual y el receipt
# resultaba inverificable fuera de Python (o directamente no era JSON válido, caso NaN/Infinity).
# El techo sale de 2**53 / META_SCALE = 90 071 992.53…: por encima, el entero escalado deja de ser
# exacto en un double y ``String(scaled)`` en JS puede caer a notación exponencial.
META_MAX_ABS = 9.0e7
# ts_ms viaja como número JSON: arriba de 2**53 el ``JSON.parse`` de JS lo redondea y el canonical
# reconstruido en JS ya no es el mismo string que se firmó.
MAX_SAFE_INT = 2**53


class CanonicalError(ValueError):
    """El valor no es canonizable ⇒ no se puede firmar algo verificable en otro lenguaje.

    Doctrina B: preferimos romper acá antes que emitir un receipt que dice ``VALIDO`` en Python
    y ``❌ INVALIDO`` en el verificador JS de referencia."""


def _scaled_half_up(x: float, scale: int) -> int:
    """``|x|·scale`` redondeado HALF-UP (alejándose del cero) como entero EXACTO.

    Sólo usa multiplicación, suma y ``floor`` de doubles IEEE-754 — las tres están definidas bit a
    bit por el estándar, así que Python, JS (``Math.floor(Math.abs(v)*scale+0.5)``), Rust y Go dan
    el MISMO entero. Reemplaza a ``format('.8f')``/``toFixed(8)``, que NO son la misma función."""
    return math.floor(abs(x) * scale + 0.5)  # math.floor ya devuelve int exacto en Python


def canonical_number(value: float | int) -> str:
    """Número → decimal fijo de 8 dec. LA regla numérica del SPEC, idéntica en TODO lenguaje.

    Medido el 2026-08-04 (firmar en Python, verificar con ethers en JS): ``format(x,'.8f')`` y
    ``x.toFixed(8)`` NO son la misma función y divergen en tres familias alcanzables:
      · ``-0.0`` — lo produce ``round(summary.bss, 4)`` en ``agent/backtest.py`` cuando bss≈0:
        Python ``'-0.00000000'`` vs JS ``'0.00000000'``;
      · ``|x| ≥ 1e21`` — JS cae a notación exponencial (``'1e+21'``);
      · empates exactos a 8 decimales (los diádicos ``m/512``, p.ej. ``1/512``): Python redondea
        half-EVEN (``'0.00195312'``), JS half-UP (``'0.00195313'``).
    Los tres daban ``Attestor.verify() == True`` en Python y ``digest match: false`` en
    ``verify.js`` ⇒ el receipt que emite el backtest de producción era INVERIFICABLE fuera de
    Python, que es justo lo que este primitivo promete que no pasa.

    Regla nueva, una sola y sin ``format``/``toFixed``/división: entero escalado half-up
    (:func:`_scaled_half_up`) y el string armado por relleno de ceros + slicing. **Cero es cero,
    sin signo.** Para todo valor en dominio y sin empate exacto el resultado es idéntico al de
    ``.8f`` ⇒ los digests que YA verificaban cross-lenguaje no cambian.

    Los no finitos (NaN/±Inf) y ``|x| > META_MAX_ABS`` levantan :class:`CanonicalError`.
    """
    if isinstance(value, bool):  # bool es int en Python; el SPEC lo deja como bool, no como número
        raise CanonicalError("los bool no son números canonizables")
    try:
        fx = float(value)
    except (OverflowError, ValueError) as exc:  # p.ej. un int de 400 dígitos
        raise CanonicalError(f"número no representable como double: {value!r}") from exc
    if not math.isfinite(fx):
        raise CanonicalError(
            f"no canonizable: {value!r} — NaN/Infinity ni siquiera es JSON válido para JS "
            "(JSON.parse falla). Pasá un valor finito o un string ya formateado."
        )
    if abs(fx) > META_MAX_ABS:
        raise CanonicalError(
            f"no canonizable: |{value!r}| supera META_MAX_ABS={META_MAX_ABS:.0f} — arriba de ahí el "
            "entero escalado deja de ser exacto en double y JS lo imprime en notación exponencial. "
            "Pasá el valor como string ya formateado."
        )
    scaled = _scaled_half_up(fx, META_SCALE)
    digits = str(scaled).rjust(META_DECIMALS + 1, "0")
    sign = "-" if fx < 0.0 and scaled != 0 else ""  # cero es cero: nada de "-0.00000000"
    return f"{sign}{digits[:-META_DECIMALS]}.{digits[-META_DECIMALS:]}"


def _to_bp(confidence: float) -> int:
    """confidence ∈ [0,1] → basis points enteros (half-up). Un entero serializa idéntico en
    Python/JS/Rust; un float NO (Python ``1.0``→``'1.0'`` pero JS→``'1'``) → el verify
    cross-lenguaje fallaba en los bordes (0.0/1.0). Con bp es reproducible bit-a-bit.

    Usa el MISMO ``_scaled_half_up`` que ``meta``: ``Math.round`` de JS redondea sobre el valor
    exacto del double, mientras que ``int(c*10000+0.5)`` redondea sobre la SUMA en punto flotante
    — divergen en ``c = 4.9999999999999994e-5`` (Python 1, JS 0). Una sola regla, cero divergencia.

    Y el MISMO dominio explícito que ``meta``: ``confidence`` fuera de ``[0,1]`` levanta
    :class:`CanonicalError`. Sin esta guarda, ``confidence`` era el único número del canonical sin
    dominio: un NaN reventaba ``math.floor`` con ``ValueError`` crudo (rompiendo el contrato de
    bool total de :meth:`Attestor.verify` y tirando stack trace en el CLI) y un valor grande
    canonizaba ``10000000000000000000000`` en Python y ``1e+22`` en JS — el mismo bug que §1.1
    cierra para ``meta``. ``attest`` ya rechazaba fuera de [0,1]; ahora también el verify."""
    try:
        c = float(confidence)
    except (OverflowError, ValueError) as exc:
        raise CanonicalError(f"confidence no representable como double: {confidence!r}") from exc
    if not (math.isfinite(c) and 0.0 <= c <= 1.0):
        raise CanonicalError(
            f"confidence={confidence!r} fuera del dominio [0,1] del SPEC §1 — NaN/Infinity ni "
            "siquiera es JSON válido para JS, y fuera de rango el entero de basis points canoniza "
            "en notación exponencial allá (otro string, otro digest)."
        )
    return _scaled_half_up(c, CONFIDENCE_SCALE)


def _canonicalize_numbers(obj: Any) -> Any:
    """Aplica :func:`canonical_number` recursivamente: TODO número (int y float) → string decimal
    fijo de 8 dec. (JS no distingue ``1.0`` de ``1`` tras ``JSON.parse`` → stringificar sólo los
    floats sería irreproducible.) Los bools se dejan como bool. Se aplica SOLO a ``meta``; los
    enteros de nivel superior (confidence_bp, ts_ms) van directos."""
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, (int, float)):
        return canonical_number(obj)
    if isinstance(obj, dict):
        return {k: _canonicalize_numbers(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        # tuple TAMBIÉN: json.dumps la serializa como array, así que sin este caso los números de
        # adentro salían crudos ("t":[1.0,2]) y JS canonizaba ["1.00000000","2.00000000"] ⇒ otro
        # digest sobre un receipt que attest firmaba igual. Mismo bug de §1.1, otra puerta.
        return [_canonicalize_numbers(v) for v in obj]
    return obj


def canonical_string(
    claim: str, confidence: float, reasoning: str, ts_ms: int, meta: dict[str, Any] | None
) -> str:
    """El SPEC canónico: mismo input ⇒ mismos bytes ⇒ mismo digest, en CUALQUIER lenguaje.

    ``confidence`` va como entero de basis points (``confidence_bp``); TODO número de ``meta`` va
    como string decimal fijo de 8 dec (:func:`canonical_number`). Claves ordenadas, sin espacios,
    UTF-8. Fuente única de verdad — la usan attest, verify y el CLI. Reimplementable en JS/Rust:
    ver ``SPEC.md`` + ``verify.js`` (el verificador de referencia que corre en CI a mano)."""
    stamp = int(ts_ms)
    if stamp != ts_ms:
        # `int()` truncaba en silencio: ts_ms=1.9 firmaba `"ts_ms":1` acá y el receipt guardaba
        # 1.9, que es lo que JS canoniza ⇒ otro digest. Se rompe ruidoso en vez de truncar.
        raise CanonicalError(f"ts_ms={ts_ms!r} no es entero: JS canoniza el valor tal cual")
    if abs(stamp) > MAX_SAFE_INT:
        raise CanonicalError(
            f"ts_ms={stamp} supera 2**53: JSON.parse en JS lo redondea y el canonical reconstruido "
            "deja de coincidir byte a byte con el firmado"
        )
    payload = {
        "claim": claim,
        "confidence_bp": _to_bp(confidence),
        "meta": _canonicalize_numbers(meta or {}),
        "reasoning": reasoning,
        "ts_ms": stamp,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _digest(canonical: str) -> str:
    return "0x" + keccak(canonical.encode("utf-8")).hex()


@dataclass(frozen=True)
class Receipt:
    """Atestación verificable de una decisión de agente. Serializable, verificable OFFLINE por cualquiera."""
    claim: str
    confidence: float
    reasoning: str
    signer: str
    digest: str
    signature: str
    ts_ms: int
    meta: dict[str, Any] = field(default_factory=dict)

    def canonical(self) -> str:
        return canonical_string(self.claim, self.confidence, self.reasoning, self.ts_ms, self.meta)

    def to_dict(self) -> dict[str, Any]:
        return {"claim": self.claim, "confidence": self.confidence, "reasoning": self.reasoning,
                "signer": self.signer, "digest": self.digest, "signature": self.signature,
                "ts_ms": self.ts_ms, "meta": self.meta}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Receipt:
        return cls(**d)


class Attestor:
    """Firma decisiones de agente. Drop-in: `Attestor().attest(claim, confidence, reasoning)`.

    Generá/pasá una clave privada (eth). La MISMA identidad firma todas las decisiones del agente →
    su historial de calibración es su reputación (portable, verificable, resistente a Sybil por stake)."""

    def __init__(self, private_key: str | None = None) -> None:
        self._acct = Account.from_key(private_key) if private_key else Account.create()

    @property
    def address(self) -> str:
        return str(self._acct.address)

    @property
    def private_key(self) -> str:
        return "0x" + str(self._acct.key.hex())

    def attest(self, claim: str, confidence: float, reasoning: str = "",
               *, meta: dict[str, Any] | None = None, ts_ms: int | None = None) -> Receipt:
        """Firma la decisión (EIP-191). $0, offline. Devuelve un Receipt verificable por cualquiera."""
        if not 0.0 <= float(confidence) <= 1.0:
            raise ValueError("confidence debe estar en [0,1]")
        stamp = ts_ms if ts_ms is not None else int(time.time() * 1000)
        canonical = canonical_string(claim, float(confidence), reasoning, stamp, meta or {})
        signed = self._acct.sign_message(encode_defunct(text=canonical))
        return Receipt(claim=claim, confidence=float(confidence), reasoning=reasoning,
                       signer=self._acct.address, digest=_digest(canonical),
                       signature="0x" + signed.signature.hex(), ts_ms=stamp, meta=meta or {})

    @staticmethod
    def verify(receipt: Receipt) -> bool:
        """Verifica OFFLINE (sin red, sin clave): el digest coincide Y la firma recupera al signer.

        Un receipt con números fuera del dominio del SPEC (:class:`CanonicalError`) es False: no
        es "la firma no matchea", es que ese receipt no es canonizable — ``attest`` ya no puede
        emitirlo, así que sólo llega desde afuera. El CLI ``python -m agentproof verify`` imprime
        el motivo exacto; acá el contrato es un bool total."""
        try:
            canonical = receipt.canonical()
        except CanonicalError:
            return False
        if _digest(canonical).lower() != receipt.digest.lower():
            return False
        try:
            sig = bytes.fromhex(receipt.signature.removeprefix("0x"))
            recovered = Account.recover_message(encode_defunct(text=canonical), signature=sig)
        except Exception:
            return False
        return str(recovered).lower() == receipt.signer.lower()

    def calibration(self, predictions: list[float], outcomes: list[int]) -> int:
        return calibration_score(predictions, outcomes)


def brier(predictions: list[float], outcomes: list[int]) -> float:
    """Brier score medio (menor = mejor calibrado). El motor de reputación estilo Numerai."""
    if not predictions or len(predictions) != len(outcomes):
        raise ValueError("predictions y outcomes deben tener el mismo largo y no ser vacíos")
    return sum((p - o) ** 2 for p, o in zip(predictions, outcomes, strict=True)) / len(predictions)


def calibration_score(predictions: list[float], outcomes: list[int]) -> int:
    """Reputación 0-100 desde el Brier (0.0→100 perfecto, 0.25 azar→50, 1.0→0). Verificable, anti-Sybil por stake."""
    b = brier(predictions, outcomes)
    return max(0, min(100, round(100 * (1.0 - 2.0 * b))))
