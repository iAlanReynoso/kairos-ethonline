#!/usr/bin/env python
"""Kairos — arnés A/B de la evidencia The Graph (track: 'do meaningful work with the data').

Mide el efecto causal de la evidencia on-chain LIVE sobre la calibración del comité:
corre la misma cosecha ForecastBench dos veces (mismas preguntas, mismo comité, misma semilla)
con KAIROS_GRAPH_EVIDENCE=1 vs 0 y compara Brier pareado. Reporta el resultado honesto:
si no hay GRAPH_API_KEY, ambos brazos son idénticos y se declara (nunca se inventa diferencia).

Uso: uv run python scripts/ethonline/graph_ab.py [--limit 12] [--concurrency 4]
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time

COMITE = "deepseek:deepseek-v4-flash,openrouter:anthropic/claude-opus-5,openrouter:openai/gpt-5.6-luna,?zai:glm-4.7-flash"


def brier(items: list[dict]) -> float | None:
    """Brier de una pool (items con 'p' y 'outcome' o similar)."""
    n = 0; total = 0.0
    for it in items:
        p = it.get("p") or it.get("p_yes")
        y = it.get("outcome") if "outcome" in it else it.get("resolved")
        if p is None or y is None:
            continue
        try:
            total += (float(p) - float(y)) ** 2; n += 1
        except (TypeError, ValueError):
            continue
    return total / n if n else None


def harvest(tag: str, limit: int, concurrency: int, graph_on: bool) -> str:
    out = f"data/fb_harvest/graph_ab_{tag}.json"
    env = dict(os.environ, KAIROS_GRAPH_EVIDENCE="1" if graph_on else "0")
    cmd = ["uv", "run", "kairos", "agent", "fb-harvest",
           "--committee", COMITE, "--news", "gdelt",
           "--limit", str(limit), "--concurrency", str(concurrency), "--out", out]
    print(f"[{tag}] cosechando {limit} preguntas (graph={'on' if graph_on else 'off'})…")
    r = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=1800)
    print(f"[{tag}] rc={r.returncode}", (r.stdout or "")[-300:].strip().replace("\n", " | "))
    return out


def load_pool(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        for key in ("items", "questions", "results", "rows"):
            if isinstance(data.get(key), list):
                return data[key]
        return []
    return data if isinstance(data, list) else []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=12)
    ap.add_argument("--concurrency", type=int, default=4)
    args = ap.parse_args()
    has_key = bool(os.environ.get("GRAPH_API_KEY"))
    print(f"GRAPH_API_KEY={'presente' if has_key else 'AUSENTE (los brazos serán idénticos — honesto)'}")
    path_on = harvest("on", args.limit, args.concurrency, True)
    path_off = harvest("off", args.limit, args.concurrency, False)
    on_items, off_items = load_pool(path_on), load_pool(path_off)
    b_on, b_off = brier(on_items), brier(off_items)
    print("=" * 60)
    print(f"Brier con The Graph : {b_on}")
    print(f"Brier sin The Graph : {b_off}")
    if b_on is not None and b_off is not None:
        print(f"Δ (menos es mejor): {b_on - b_off:+.4f}")
    print("pool:", path_on, "/", path_off)
    if not has_key:
        print("VEREDICTO: sin key no hay señal posible; re-correr al cargar GRAPH_API_KEY en .env")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
