#!/usr/bin/env bash
# Проверка перед рендером стемов (freeze.sh, render.sh --stems): вкладка REAPER (--proj или текущая) сохранена
# и её .rpp совпадает с локальной копией во всём, что читает модель (кроме времени сохранения и выделения).
#   bash nbcheck.sh <локальная папка проекта> [--proj ЧАСТЬ_ИМЕНИ]
# Код 0 - можно рендерить; иначе печатает причину в stderr.
set -euo pipefail
DIR=$(cd "$(dirname "$0")" && pwd)
. "$DIR/env.sh"
LOCAL=$1; shift; proj=''
[ "${1:-}" = "--proj" ] && { proj=$2; shift 2; }
NB='C:\rec\2026\reaper-song\'
q() { printf '[==[%s]==]' "$1"; }
chk=$(mktemp); got=$(mktemp --suffix=.rpp); trap 'rm -f "$chk" "$got"' EXIT
{
  echo "local A = {dir = $(q "$NB"), proj = $(q "$proj")}"
  [ -n "$proj" ] && cat "$DIR/bridge/select.lua"
  cat "$DIR/bridge/temp.lua" "$DIR/bridge/rppcopy.lua"
} > "$chk"
res=$(bash "$DIR/bridge/bridge.sh" "$chk") || { echo "$res" >&2; exit 1; }
echo "$res" | grep -v '^OK\|^RPP\|^dirty' || true
RPPNB=$(echo "$res" | grep '^RPP' | cut -f2)
scp -q "$HOST:${RPPNB//\\//}" "$got"
printf 'out(os.remove(%s))\n' "$(q "$RPPNB")" | bash "$DIR/bridge/bridge.sh" >/dev/null
if echo "$res" | grep -q $'^dirty\t1'; then echo "проект на nb не сохранён (dirty): сохранить или спросить пользователя" >&2; exit 1; fi
shopt -s nullglob; RPPL=$(ls -t "$LOCAL"/*.rpp "$LOCAL"/*.RPP | grep -v '/zz-variant' | head -1 || true); shopt -u nullglob
[ -n "$RPPL" ] || { echo "нет .rpp в $LOCAL" >&2; exit 1; }
if ! d=$(python3 "$DIR/freezelib.py" same "$RPPL" "$got"); then
  echo "локальная копия $RPPL расходится с проектом на nb (вкладка не та или проект менялся) - скачать заново fetch.sh:" >&2
  echo "$d" | head -10 >&2; exit 1
fi
