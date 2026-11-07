#!/usr/bin/env bash
# Рендер в живой сессии REAPER с временными правками, скачивание и замер.
#   bash render.sh [опции] <имя> [локальная папка]
# Опции (любое число, всё возвращается после рендера):
#   --solo ТРЕК                 соло трека
#   --nomaster                  выключить FX мастера (стемы без лимитера)
#   --bypass ТРЕК:FX            выключить FX (подстрока имени или fx_ident)
#   --set ТРЕК:FX:ПАРАМ=ЗНАЧ    параметр FX: номер или подстрока имени; JSFX - родные единицы, VST - 0..1
#   --vol ТРЕК=dB               фейдер
#   --keep                      оставить файл на nb рядом с целью рендера
# ТРЕК: guitar | mic | master. Имя - латиница/цифры/_-. (файл <имя>.<формат проекта>).
# Рендер по настройкам проекта (42230); файл с именем цели рендера, если есть, не трогается.
# Если проект был сохранён (dirty 0), после возврата правок сохраняется снова; несохранённые правки пользователя не сохраняются.
# Печатает время рендера, изменённые параметры и замер (measure.py). Тишина = медиа офлайн (REAPER не в фокусе).
set -euo pipefail
DIR=$(cd "$(dirname "$0")" && pwd)
. "$DIR/env.sh"
solo=() bypass=() set=() vol=(); nomaster=false; keep=false
while [ $# -gt 0 ]; do
  case $1 in
    --solo) solo+=("$2"); shift 2;;
    --bypass) bypass+=("$2"); shift 2;;
    --set) set+=("$2"); shift 2;;
    --vol) vol+=("$2"); shift 2;;
    --nomaster) nomaster=true; shift;;
    --keep) keep=true; shift;;
    -*) echo "неизвестная опция $1" >&2; exit 1;;
    *) break;;
  esac
done
NAME=${1:?имя рендера}; LOCAL=${2:-${TMPDIR:-/tmp}/reaper-song/render}
[[ $NAME =~ ^[A-Za-z0-9_.-]+$ ]] || { echo "имя только латиницей: $NAME" >&2; exit 1; }
mkdir -p "$LOCAL"

q() { printf '[==[%s]==]' "$1"; }
lua=$(mktemp); trap 'rm -f "$lua"' EXIT
{
  echo "local A = {name = $(q "$NAME"), nomaster = $nomaster, solo = {}, bypass = {}, set = {}, vol = {}}"
  for s in "${solo[@]+"${solo[@]}"}"; do echo "table.insert(A.solo, $(q "$s"))"; done
  for s in "${bypass[@]+"${bypass[@]}"}"; do echo "table.insert(A.bypass, {$(q "${s%%:*}"), $(q "${s#*:}")})"; done
  for s in "${set[@]+"${set[@]}"}"; do
    t=${s%%:*}; r=${s#*:}; f=${r%:*}; pv=${r##*:}
    echo "table.insert(A.set, {$(q "$t"), $(q "$f"), $(q "${pv%%=*}"), ${pv#*=}})"
  done
  for s in "${vol[@]+"${vol[@]}"}"; do echo "table.insert(A.vol, {$(q "${s%%=*}"), ${s#*=}})"; done
  cat "$DIR/bridge/render.lua"
} > "$lua"

res=$(bash "$DIR/bridge/bridge.sh" -t 900 "$lua") || { echo "$res"; exit 1; }
echo "$res" | grep -v '^DEST' | tail -n +2
DEST=$(echo "$res" | grep '^DEST' | cut -f2)
scp -q "$HOST:${DEST//\\//}" "$LOCAL/"
if ! $keep; then printf 'out(os.remove(%s))\n' "$(q "$DEST")" | bash "$DIR/bridge/bridge.sh" >/dev/null; fi
uv run -q "$DIR/measure.py" "$LOCAL/${DEST##*\\}"
