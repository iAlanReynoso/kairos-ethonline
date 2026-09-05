#!/usr/bin/env node
// agentproof — verificador de REFERENCIA en JavaScript.
//
// Prueba que un receipt firmado en Python verifica en JS bit-a-bit: reproduce el canonical del
// SPEC (SPEC.md), recomputa el digest keccak256 y recupera al firmante del EIP-191. Es el artefacto
// que FUERZA a que el claim "reproducible en cualquier lenguaje" sea verdadero (y el que destapó
// los dos bugs: confidence float -> confidence_bp ENTERO, y toFixed(8) != format('.8f')).
//
//   npm i ethers && node verify.js receipt.json      # exit 0 = válido
const fs = require("fs");
const { keccak256, toUtf8Bytes, verifyMessage } = require("ethers");

const META_DECIMALS = 8;
const META_SCALE = 1e8;
const META_MAX_ABS = 9.0e7; // = 2**53 / META_SCALE redondeado abajo (ver SPEC §1)
const MAX_SAFE_INT = 2 ** 53;

// Entero escalado half-up (alejándose del cero). Sólo mult + suma + floor de doubles IEEE-754:
// las tres están definidas bit a bit, así que este entero es EL MISMO que el de Python.
function scaledHalfUp(v, scale) {
  return Math.floor(Math.abs(v) * scale + 0.5);
}

// LA regla numérica del SPEC §1 — NO usa toFixed. `toFixed(8)` y `format('.8f')` divergen en
// -0.0 (JS "0.00000000" vs Python "-0.00000000"), en |x| >= 1e21 (JS cae a "1e+21") y en los
// empates exactos a 8 decimales (JS half-up vs Python half-even: 1/512 -> 0.00195313 vs
// 0.00195312). Medido el 2026-08-04: los tres daban verify() True en Python y digest match
// false acá. Acá el string se arma por relleno de ceros + slicing: exacto y sin división.
function canonNumber(v) {
  if (!Number.isFinite(v)) throw new Error(`no canonizable: ${v} (NaN/Infinity no es JSON válido)`);
  if (Math.abs(v) > META_MAX_ABS) throw new Error(`no canonizable: |${v}| > ${META_MAX_ABS}`);
  const scaled = scaledHalfUp(v, META_SCALE);
  const d = String(scaled).padStart(META_DECIMALS + 1, "0");
  const sign = v < 0 && scaled !== 0 ? "-" : ""; // cero es cero: nada de "-0.00000000"
  return sign + d.slice(0, -META_DECIMALS) + "." + d.slice(-META_DECIMALS);
}

// meta: todos los números (int y float) -> string decimal fijo de 8 dec (ver SPEC §1).
function canonNumbers(v) {
  if (typeof v === "boolean") return v;
  if (typeof v === "number") return canonNumber(v);
  if (Array.isArray(v)) return v.map(canonNumbers);
  if (v && typeof v === "object") {
    const o = {};
    for (const k of Object.keys(v)) o[k] = canonNumbers(v[k]);
    return o;
  }
  return v;
}

// json.dumps(sort_keys=True, separators=(",",":")) — claves ordenadas, sin espacios.
function stableStringify(x) {
  if (Array.isArray(x)) return "[" + x.map(stableStringify).join(",") + "]";
  if (x && typeof x === "object") {
    return "{" + Object.keys(x).sort()
      .map((k) => JSON.stringify(k) + ":" + stableStringify(x[k])).join(",") + "}";
  }
  return JSON.stringify(x);
}

function canonicalFromReceipt(d) {
  if (!Number.isFinite(d.ts_ms) || Math.abs(d.ts_ms) > MAX_SAFE_INT) {
    throw new Error(`ts_ms fuera de 2**53: ${d.ts_ms} (JSON.parse ya lo redondeó)`);
  }
  // Mismo dominio que Python (SPEC §1): confidence es el otro número que NO pasa por canonNumber.
  // Sin esta guarda, confidence = 1e18 canoniza "1e+22" acá y "10000000000000000000000" allá.
  if (!Number.isFinite(d.confidence) || d.confidence < 0 || d.confidence > 1) {
    throw new Error(`confidence fuera de [0,1]: ${d.confidence}`);
  }
  return stableStringify({
    claim: d.claim,
    // ENTERO half-up, MISMA regla que meta. Math.round() NO sirve: redondea sobre el valor exacto
    // del double y diverge de Python en confidence = 4.9999999999999994e-5.
    confidence_bp: scaledHalfUp(d.confidence, 10000),
    meta: canonNumbers(d.meta || {}),
    reasoning: d.reasoning,
    ts_ms: d.ts_ms,
  });
}

let receipt, canonical;
try {
  // JSON.parse también revienta acá si el receipt trae NaN/Infinity: Python los escribía bare
  // (json.dumps los admite) y no son JSON válido -> ni se podían leer. Ahora attest los rechaza.
  receipt = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
  canonical = canonicalFromReceipt(receipt);
} catch (e) {
  // Doctrina B: decir POR QUÉ no se puede verificar, no devolver un "inválido" mudo.
  console.log("❌ INVALIDO — receipt no canonizable:", e.message);
  process.exit(1);
}
const digest = keccak256(toUtf8Bytes(canonical));
const digestOk = digest.toLowerCase() === String(receipt.digest).toLowerCase();
const recovered = verifyMessage(canonical, receipt.signature); // EIP-191 personal_sign
const signerOk = recovered.toLowerCase() === String(receipt.signer).toLowerCase();

console.log("canonical      :", canonical);
console.log("digest (JS)    :", digest);
console.log("digest (receipt):", receipt.digest);
console.log("digest match   :", digestOk);
console.log("signer recovered:", recovered);
console.log("signer match   :", signerOk);
console.log(digestOk && signerOk
  ? "✅ VALIDO — firmado en Python, verificado en JS (reproducible cross-lenguaje)"
  : "❌ INVALIDO");
process.exit(digestOk && signerOk ? 0 : 1);
