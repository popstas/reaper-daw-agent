#!/usr/bin/env bash
# Применить правки в живой сессии REAPER и сохранить проект (одним undo-шагом).
#   bash apply.sh [опции] <часть имени проекта>
# Опции - как у render.sh, но правки остаются:
#   --set ТРЕК:FX:ПАРАМ=ЗНАЧ    параметр FX: номер (позиция токена в .rpp минус 1) или подстрока имени; JSFX - родные единицы
#   --vol ТРЕК=dB               фейдер
#   --itemvol ТРЕК=dB           громкость всех айтемов трека
# Вкладка выбирается по части пути проекта. Проект с несохранёнными правками не трогается.
# Печатает было -> стало по каждой правке.
set -euo pipefail
DIR=$(cd "$(dirname "$0")" && pwd)
set=() vol=() itemvol=()
while [ $# -gt 0 ]; do
  case $1 in
    --set) set+=("$2"); shift 2;;
    --vol) vol+=("$2"); shift 2;;
    --itemvol) itemvol+=("$2"); shift 2;;
    -*) echo "неизвестная опция $1" >&2; exit 1;;
    *) break;;
  esac
done
PROJ=${1:?часть имени проекта}
q() { printf '[==[%s]==]' "$1"; }
lua=$(mktemp); trap 'rm -f "$lua"' EXIT
{
  echo "local A = {proj = $(q "$PROJ"), set = {}, vol = {}, itemvol = {}}"
  for s in "${set[@]+"${set[@]}"}"; do
    t=${s%%:*}; r=${s#*:}; f=${r%:*}; pv=${r##*:}
    echo "table.insert(A.set, {$(q "$t"), $(q "$f"), $(q "${pv%%=*}"), ${pv#*=}})"
  done
  for s in "${vol[@]+"${vol[@]}"}"; do echo "table.insert(A.vol, {$(q "${s%%=*}"), ${s#*=}})"; done
  for s in "${itemvol[@]+"${itemvol[@]}"}"; do echo "table.insert(A.itemvol, {$(q "${s%%=*}"), ${s#*=}})"; done
  cat "$DIR/bridge/apply.lua"
} > "$lua"
bash "$DIR/bridge/bridge.sh" -t 120 "$lua"
