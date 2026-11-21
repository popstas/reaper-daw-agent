#!/usr/bin/env bash
# Врезка повтора из того же дубля в живой сессии REAPER, одним undo-шагом, с сохранением.
#   bash splice.sh [--xf 0.004] [--guard 0.001] <часть имени проекта> <атака оригинала, с> <атака повтора, с>
# Точки - из splicefind.py: начало атаки одного и того же удара гитары в оригинале и в повторе (таймлайн до правки).
# На всех треках, где айтем покрывает обе точки: оригинал до атаки, повтор с атаки до конца, середина выкинута,
# айтемы и маркеры после повтора сдвигаются влево. Фейд xf линейный, кончается за guard до атаки - удар закрывает стык.
# Проект с несохранёнными правками не трогается. Откат - Undo в REAPER («reaper-song splice»).
set -euo pipefail
DIR=$(cd "$(dirname "$0")" && pwd)
xf=0.004 guard=0.001
while [ $# -gt 0 ]; do
  case $1 in
    --xf) xf=$2; shift 2;;
    --guard) guard=$2; shift 2;;
    -*) echo "неизвестная опция $1" >&2; exit 1;;
    *) break;;
  esac
done
PROJ=${1:?часть имени проекта}; TA=${2:?атака оригинала}; TB=${3:?атака повтора}
lua=$(mktemp); trap 'rm -f "$lua"' EXIT
{
  printf 'local A = {proj = [==[%s]==], ta = %s, tb = %s, xf = %s, guard = %s}\n' "$PROJ" "$TA" "$TB" "$xf" "$guard"
  cat "$DIR/bridge/splice.lua"
} > "$lua"
bash "$DIR/bridge/bridge.sh" -t 120 "$lua"
