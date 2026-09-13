#!/usr/bin/env bash
# Kairos — VIGIA DEL MOTOR (cron cada 5 min): si el motor o la fachada no responden, los relanza.
# Motivo: un motor caido deja la plataforma 'viva' pero sin poder pronosticar (fallo duro en la demo).
set -uo pipefail
export PATH="$HOME/.local/bin:$PATH"
cd "$HOME/polymarket-bot" || exit 1
mkdir -p logs data/notify_state

exec 9>"data/engine_watch.flock"
flock -n 9 || exit 0

log() { echo "$(date '+%F %T') $*" >> logs/engine_watch.log; }

up() { curl -s -m 8 "$1" -o /dev/null -w '%{http_code}' 2>/dev/null | grep -q 200; }

ENGINE_OK=0; FACADE_OK=0
up http://127.0.0.1:8787/health && ENGINE_OK=1
up http://127.0.0.1:8788/health && FACADE_OK=1

if [ "$ENGINE_OK" = 1 ] && [ "$FACADE_OK" = 1 ]; then exit 0; fi
log "caida detectada: motor_ok=$ENGINE_OK fachada_ok=$FACADE_OK"

if [ "$ENGINE_OK" = 0 ]; then
  pkill -f 'ethonline/serve_forecas[t].py' 2>/dev/null || true
  sleep 1
  (setsid nohup .venv/bin/python3 scripts/ethonline/serve_forecast.py --port 8787 >> logs/serve_forecast.log 2>&1 < /dev/null &)
  sleep 12
  up http://127.0.0.1:8787/health && log 'motor relanzado OK' || log 'motor NO levanto'
fi

if [ "$FACADE_OK" = 0 ]; then
  pkill -f 'ethonline/serve_publi[c].py' 2>/dev/null || true
  sleep 1
  (setsid nohup .venv/bin/python3 scripts/ethonline/serve_public.py --port 8788 >> logs/serve_public.log 2>&1 < /dev/null &)
  sleep 6
  up http://127.0.0.1:8788/health && log 'fachada relanzada OK' || log 'fachada NO levanto'
fi

STAMP=data/notify_state/engine_watch.last
NOW=$(date +%s); LAST=$(cat "$STAMP" 2>/dev/null || echo 0)
if (( NOW - LAST > 1800 )); then
  echo "$NOW" > "$STAMP"
  bash scripts/automation/notify.sh -p high -t robot,warning \
    "Motor o fachada de Kairos caidos: relanzados" \
    "Vigia del motor (cada 5 min). Ultima linea: $(tail -1 logs/engine_watch.log)" >/dev/null 2>&1 || true
fi