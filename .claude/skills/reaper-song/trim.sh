#!/usr/bin/env bash
# Резы начала и конца дубля в живой сессии REAPER, одним undo-шагом, с сохранением.
#   bash trim.sh [--keep-pos] <часть имени проекта> 'ТРЕК=S0-S1[,FO]' ...
# S0, S1 - время файла дубля (как в trimfind.py, готовая строка - там же): первому аудио-айтему трека начало файла S0,
# последнему конец S1 и фейд FO с. Айтемы между ними (врезки) не трогаются. Без --keep-pos проект сдвигается так,
# чтобы самое раннее обрезанное начало встало на 0:00 (айтемы всех треков и маркеры; с автоматизацией - отказ).
# Проект с несохранёнными правками не трогается. Откат - Undo в REAPER («reaper-song trim»).
set -euo pipefail
DIR=$(cd "$(dirname "$0")" && pwd)
zero=true
while [ $# -gt 0 ]; do
  case $1 in
    --keep-pos) zero=false; shift;;
    -*) echo "неизвестная опция $1" >&2; exit 1;;
    *) break;;
  esac
done
PROJ=${1:?часть имени проекта}; shift
[ $# -gt 0 ] || { echo "нужен хотя бы один 'ТРЕК=S0-S1[,FO]'" >&2; exit 1; }
specs=""
for s in "$@"; do
  [[ $s =~ ^(.+)=([0-9.]+)-([0-9.]+)(,([0-9.]+))?$ ]] || { echo "не разобрал «$s»: нужно ТРЕК=S0-S1[,FO]" >&2; exit 1; }
  tr=${BASH_REMATCH[1]}; fo=${BASH_REMATCH[5]:-nil}
  specs+=$(printf '{track = [==[%s]==], s0 = %s, s1 = %s, fo = %s}, ' "$tr" "${BASH_REMATCH[2]}" "${BASH_REMATCH[3]}" "$fo")
done
lua=$(mktemp); trap 'rm -f "$lua"' EXIT
{
  printf 'local A = {proj = [==[%s]==], zero = %s, specs = {%s}}\n' "$PROJ" "$zero" "$specs"
  cat "$DIR/bridge/trim.lua"
} > "$lua"
bash "$DIR/bridge/bridge.sh" -t 120 "$lua"
