#!/usr/bin/env bash
# Чужой мастер поверх нашего микса прямо в проекте - то же, что blend.py по файлам, но рендерится REAPER-ом.
#   bash refblend.sh [--name "мастер L.R."] [--bus "наш микс"] <часть имени проекта> <файл> <SOFFS, с> <ref dB> <mix dB>
# Файл - путь от папки проекта на nb (или абсолютный), положить туда заранее.
# SOFFS: на сколько чужой мастер опаздывает от нашего рендера: blend.py печатает сдвиг d (наш[t + d] ≈ чужой[t]),
# SOFFS = −d (на «ЖЩ» d = −13.94 мс → SOFFS 0.01394). ref dB / mix dB - фейдеры чужого трека и папки нашего микса:
# blend.py ОСНОВА=чужой+G1, вторая −N, усиление суммы G → ref = G1 + G, mix = −N + G.
# Все треки уходят в папку --bus, цепочка мастера переезжает на неё; мастер остаётся без FX. Одним undo-шагом, с сохранением.
set -euo pipefail
DIR=$(cd "$(dirname "$0")" && pwd)
name='мастер L.R.' bus='наш микс'
while [ $# -gt 0 ]; do
  case $1 in
    --name) name=$2; shift 2;;
    --bus) bus=$2; shift 2;;
    -*) echo "неизвестная опция $1" >&2; exit 1;;
    *) break;;
  esac
done
PROJ=${1:?часть имени проекта}; FILE=${2:?файл}; SOFFS=${3:?SOFFS}; REF=${4:?ref dB}; MIX=${5:?mix dB}
lua=$(mktemp); trap 'rm -f "$lua"' EXIT
{
  printf 'local A = {proj = [==[%s]==], file = [==[%s]==], soffs = %s, ref_db = %s, mix_db = %s, name = [==[%s]==], bus = [==[%s]==]}\n' \
    "$PROJ" "$FILE" "$SOFFS" "$REF" "$MIX" "$name" "$bus"
  cat "$DIR/bridge/refblend.lua"
} > "$lua"
bash "$DIR/bridge/bridge.sh" -t 120 "$lua"
