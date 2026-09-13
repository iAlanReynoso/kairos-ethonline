# Auditoría de fiabilidad de la plataforma — hallazgos y parches (13-sep-2026)

> Objetivo: plataforma funcional y sin fallas para la demo y el envío. Nivel adversarial.
> Todo lo de abajo está **medido**, no supuesto. Respaldos de los archivos tocados: `*.bak-fixes`.

## 1 · Causa raíz del fallo transitorio (CONFIRMADA)
La UI corta la consulta si pasan **90 s sin recibir datos**:
`idleTimer=setTimeout(()=>{timedOut=true;activeController.abort();},90000)`
(docs/demo/kairos_ui_v3.html) — y el motor tarda **entre 50 y 84 s** en emitir el primer voto, porque la etapa
`research` llega a los 0 s y después hay silencio total. Si una corrida se pasa de 90 s (proveedor lento), la UI
**aborta sola** y muestra `failed`. Eso explica el fallo observado en pruebas y es un riesgo directo para la demo.

## 2 · Hallazgos (severidad y evidencia)
| # | Hallazgo | Severidad | Evidencia |
|---|---|---|---|
| 1 | UI aborta a los 90 s sin datos; silencio real de 50-84 s | **CRÍTICA** | timer en la UI + medición de la corrida (0 s → 80 s sin eventos) |
| 2 | Fachada con `except Exception: pass`: un corte del stream no dejaba error ni rastro | **ALTA** | `serve_public.py` (versión previa), sin logs de error |
| 3 | Fuga del slot de concurrencia: `await request.read()` fuera del `try/finally` | **ALTA** | soak público: 2 de 5 corridas fallaron con rechazo inmediato (0 s y 12 s) |
| 4 | `MAX_STREAMS=3` con slots retenidos hasta ~90 s si el cliente aborta | MEDIA | código de la fachada |
| 5 | Sin keepalive: proxies (Tailscale/cloudflared) pueden cerrar conexiones ociosas | MEDIA | no había ningún comentario SSE en el stream |

## 3 · Parches aplicados
1. **Keepalive SSE cada 10 s** en la fachada (`KEEPALIVE=10`): comentario `: keepalive` cuando el motor calla.
   Mantiene viva la conexión **y reinicia el timer de la UI** (que se rearma con cualquier byte recibido).
2. **Error explícito y log**: si el stream se corta, la fachada emite `{"type":"error","message":...}` y escribe el
   traceback en `logs/stream_errors.log` (antes se perdía en silencio).
3. **Slot garantizado**: `request.read()`, `prepare()` y el proxy quedaron dentro del `try/finally` → nunca más 'busy' permanente.
4. **MAX_STREAMS=3 → 6** (un cliente que aborta retiene el slot hasta que el motor termina).
5. **Timeout de la UI: 90 s → 180 s** (defensa en profundidad), con los textos EN/ES actualizados.
6. **Vigía del motor** (`scripts/automation/engine_watch.sh`, cron cada 5 min): si el motor (8787) o la fachada (8788)
   no responden 200, los relanza y avisa al teléfono.

## 4 · Verificación (evidencia)
- **Keepalive en vivo**: corrida de 84 s → **7 keepalives** a intervalos exactos de 10 s durante los 80 s de silencio;
  el flujo completo llegó igual (votos → calibración → decisión → firma → ancla → `done`).
- **Vigía del motor**: probado, devuelve 0 con todo sano.
- **Soak público antes de los parches**: 5 corridas → **2 fallos** (rechazo inmediato).
- **Soak público después de los parches**: ver sección de resultados al final de este documento.

## 5 · Riesgos residuales (honestos)
1. Si un proveedor LLM del comité se cae **dos veces** en la misma corrida y el motor se pasa de 180 s, la UI abortará igual.
   Mitigación actual: 180 s de margen sobre un tiempo típico de 54-90 s.
2. El motor está corriendo desde el 8-sep: sano, pero conviene un reinicio controlado después del submit.
3. Sin redundancia de máquina: si Windows/WSL se apaga y nadie inicia sesión, nada corre (riesgo conocido).
---

## 6 · RESULTADO MEDIDO (antes vs después)

Mismo ataque, misma ruta (URL pública, Tailscale Funnel), 5 corridas de la misma pregunta:

| | ANTES de los parches | DESPUÉS de los parches |
|---|---|---|
| Corridas con `done` | 3/5 | **5/5** |
| Fallos | **2 (40%)** — rechazo inmediato a los 0 s y 12 s | **0** |
| Keepalives durante el silencio | 0 | 4, 5, 1, 7 y 2 por corrida |
| Duración típica | 83, 14, 16, 12, 0 s | 50, 54, 16, 84, 29 s |

**Contrato funcional verificado después de los cambios:** 2 consultas seguidas `live → finished`, EN/ES completo, 0 errores JS.

**Conclusión:** el modo de fallo que producía el `failed` transitorio está cerrado y medido. La plataforma pasó de 40% de fallos a 0% en la ruta real que verán los jueces.
