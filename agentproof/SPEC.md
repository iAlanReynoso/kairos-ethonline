# agentproof — SPEC del canonical (v1.1)

Un receipt es verificable **offline, en cualquier lenguaje**, sin confiar en nuestro código. Este
documento fija los bytes EXACTOS a hashear para que un escéptico reimplemente `verify` en JS/Rust/Go.

> **v1.1 (2026-08-04)** — se reescribió §1.1 (la regla numérica). `format('.8f')` y `toFixed(8)`
> NO son la misma función: divergían en `-0.0`, en `|x| ≥ 1e21` y en los empates exactos. Sobre
> 17 917 valores fuzzeados, **2 038 (11%) daban strings distintos** entre Python y JS. La regla
> nueva no usa ninguna de las dos.

## 1. canonical

JSON de un objeto con EXACTAMENTE estas claves, **ordenadas alfabéticamente**, **sin espacios**:

| clave | tipo | nota |
|---|---|---|
| `claim` | string | la afirmación |
| `confidence_bp` | **integer** | `confidence ∈ [0,1]` escalado a basis points por §1.1 |
| `meta` | object | **todos los números** (int y float) → string decimal fijo de 8 dec por §1.1; strings/bools van igual |
| `reasoning` | string | el razonamiento |
| `ts_ms` | integer | timestamp unix en ms, `|ts_ms| ≤ 2^53` |

Serialización: claves ordenadas (`sort_keys`), separadores `(",", ":")`, UTF-8, `ensure_ascii=false`.

Ejemplo (bytes exactos):
```
{"claim":"BTC>100k EOY","confidence_bp":7200,"meta":{},"reasoning":"ETF inflows","ts_ms":1784000000000}
```

### 1.1 La regla numérica (única, load-bearing)

Todo número se convierte a un **entero escalado con redondeo half-up alejándose del cero**:

```
scaled(x, scale) = floor(abs(x) * scale + 0.5)
```

Las tres operaciones (`*`, `+`, `floor` sobre doubles IEEE-754 binary64) están definidas **bit a
bit** por el estándar ⇒ Python, JS, Rust y Go producen el MISMO entero. No se usa `format`,
ni `toFixed`, ni `printf`, ni división.

- **`confidence_bp` = `scaled(confidence, 10000)`** — entero, va directo al JSON.
- **Números de `meta`** = `scaled(x, 1e8)` renderizado a decimal fijo de 8 dec **por string**:

  ```
  d    = str(scaled).rjust(9, "0")          # ≥ 1 dígito entero + 8 decimales
  out  = ("-" if x < 0 and scaled != 0 else "") + d[:-8] + "." + d[-8:]
  ```

  **Cero es cero, sin signo:** `-0.0` y todo lo que redondea a cero canonizan a `"0.00000000"`.

**Dominio (fuera de él NO se firma — la implementación levanta error):**

| condición | por qué |
|---|---|
| `x` finito (nada de NaN/±Infinity) | Python los escribía bare en el JSON y `JSON.parse` de JS ni los lee: el receipt no era JSON válido |
| `abs(x) ≤ 9.0e7` (= `2^53 / 1e8` redondeado abajo) | arriba de eso `scaled` deja de ser un entero exacto en un double y `String(scaled)` en JS cae a notación exponencial |
| `abs(ts_ms) ≤ 2^53` | `JSON.parse` de JS redondea los enteros más grandes ⇒ el canonical reconstruido deja de coincidir |
| `confidence ∈ [0,1]` y finito | es el otro número que NO pasa por la regla de `meta`: con NaN el receipt no es JSON válido, y fuera de rango `confidence_bp` canoniza `10000000000000000000000` en Python y `1e+22` en JS |

Un valor fuera del dominio se pasa **como string ya formateado** (los strings viajan intactos).

**Lo que la regla NO promete (honestidad):** el canonical commitea al valor **cuantizado a 8
decimales**, no al double exacto — dos números que difieren por debajo de `1e-8` firman idéntico,
y para valores grandes `abs(x)*1e8` ya redondea, así que el string no siempre es la expansión
decimal correctamente redondeada de `x`. Es una función determinista del double, que es lo único
que el hash necesita. Si el compromiso tiene que ser sobre más precisión: pasá el número como string.

## 2. digest
```
digest = "0x" + hex(keccak256(utf8(canonical)))     # keccak256, NO sha3-256
```

## 3. firma (EIP-191 personal_sign)
```
prefix  = "\x19Ethereum Signed Message:\n" + str(len(utf8(canonical)))   # len en BYTES, no chars
message = prefix + canonical
signature = secp256k1_sign(keccak256(message), privkey)
```
Verificar: `ecrecover(signature, keccak256(message)) == signer`.

## 4. Por qué números-como-string y no números JSON — load-bearing

Dos bugs distintos, los dos encontrados por el verificador JS de referencia, no por los tests Python:

1. **`confidence` como float.** `json.dumps(1.0)` → `"1.0"` en Python, pero `JSON.stringify(1.0)`
   → `"1"` en JS (y serde en Rust igual). Los bordes (`0.0`/`1.0`, o cualquier float de valor
   entero) producían canonicals distintos ⇒ verify cross-lenguaje FALLABA sobre receipts legítimos.
   Por eso `confidence` viaja como `confidence_bp` entero.

2. **`meta` con `format('.8f')`.** Medido el 2026-08-04 firmando en Python y verificando con
   `ethers` en JS — `Attestor.verify()` daba `True` y `verify.js` daba `digest match: false`:

   | valor | Python `format('.8f')` | JS `toFixed(8)` |
   |---|---|---|
   | `round(-1e-5, 4)` = `-0.0` (lo emite `agent/backtest.py` cuando bss≈0) | `-0.00000000` | `0.00000000` |
   | `1e21` | `1000000000000000000000.00000000` | `1e+21` |
   | `1/512` (empate exacto a 8 dec) | `0.00195312` (half-**even**) | `0.00195313` (half-**up**) |
   | `NaN` / `inf` | `nan` / `inf` (y el receipt ni es JSON válido) | `NaN` / `Infinity` |

   El receipt de PRODUCCIÓN del backtest caía en la primera fila ⇒ el claim insignia
   ("verificable en cualquier lenguaje") era falso por el camino real. §1.1 lo cierra.

## 5. Referencia ejecutable
- Python: `agentproof/core.py` → `canonical_string()` / `canonical_number()` (fuente única de verdad).
- JS: `agentproof/verify.js` (ethers) → reproduce canonical + digest + ecrecover y **prueba** que
  un receipt firmado en Python verifica en JS bit-a-bit.

Verificación cruzada REAL (el repo no lleva `package.json` ni `node_modules` a propósito):

```bash
mkdir -p /tmp/agentproof-js && cd /tmp/agentproof-js && npm i ethers
cd /ruta/al/repo
uv run python -m agentproof attest --claim "c" --confidence 0.72 --out /tmp/r.json
NODE_PATH=/tmp/agentproof-js/node_modules node agentproof/verify.js /tmp/r.json   # exit 0 = válido
```

El test `tests/test_agentproof_crosslang.py` corre exactamente eso sobre los casos límite de §1.1
cuando encuentra `node` + `ethers` (con `AGENTPROOF_NODE_PATH` apuntando a los `node_modules`), y
se saltea si no. El test-vigía que NO depende de node vive en `tests/test_agentproof.py`: fija los
strings canónicos exactos que produce la implementación JS.
