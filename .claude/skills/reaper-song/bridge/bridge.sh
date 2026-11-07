#!/usr/bin/env bash
# Выполнить Lua в живой сессии REAPER на nb через мост (bridge.lua).
#   bash bridge.sh [-t секунд] файл.lua      или      echo 'info()' | bash bridge.sh
# Печатает ответ моста: первая строка OK/ERR. Код выхода: 0 OK, 1 ERR, 2 мост не запущен, 3 занят, 4 таймаут.
set -euo pipefail
. "$(dirname "$0")/../env.sh"; RD='AppData/Roaming/REAPER/bridge'; T=60
[ "${1:-}" = "-t" ] && { T=$2; shift 2; }
SSHO=(-o ControlMaster=auto -o "ControlPath=/tmp/.rb-ssh-%r@%h" -o ControlPersist=120)
tmp=$(mktemp); trap 'rm -f "$tmp" "$tmp.res"' EXIT
if [ $# -gt 0 ]; then cat "$1" > "$tmp"; else cat > "$tmp"; fi
scp -q "${SSHO[@]}" "$tmp" "$HOST:$RD/cmd.lua.tmp"
st=$(ssh "${SSHO[@]}" "$HOST" "powershell -NoProfile -ExecutionPolicy Bypass -File $RD/call.ps1 -Timeout $T" | tr -d '\r' | tail -1) || true
[ "$st" = BRIDGE_DONE ] || { echo "$st" >&2; case $st in BRIDGE_DOWN*) exit 2;; BRIDGE_BUSY) exit 3;; *) exit 4;; esac; }
scp -q "${SSHO[@]}" "$HOST:$RD/result.done" "$tmp.res"
tr -d '\r' < "$tmp.res"; echo
head -1 "$tmp.res" | grep -q '^OK' || exit 1
