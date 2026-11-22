#!/usr/bin/env bash
# Рендер в живой сессии REAPER с временными правками, скачивание и замер.
#   bash render.sh [опции] <имя> [локальная папка]
# Опции (любое число, всё возвращается после рендера):
#   --solo ТРЕК                 соло трека
#   --mute ТРЕК=1|0             заглушить/включить трек (имя целиком, с пробелами - в кавычках)
#   --nomaster                  выключить FX мастера (стемы без лимитера)
#   --bypass ТРЕК:FX            выключить FX (подстрока имени или fx_ident)
#   --addfx ТРЕК:ИМЯ[@ПОСЛЕ]   вставить FX (ИМЯ как в TrackFX_AddByName: JS:guitar/chorus) после FX с подстрокой ПОСЛЕ
#                               (без @ - в конец); ставится до --set, так что --set может настроить его
#   --copyfx ТРЕК:ИСТ:FX[@ПОСЛЕ] копия FX с трека ИСТ (подстрока имени) со всем состоянием (ReaVerb с импульсом) в ТРЕК
#                               после FX с подстрокой ПОСЛЕ (без @ - в конец); ставится после --addfx и до --set
#   --set ТРЕК:FX:ПАРАМ=ЗНАЧ    параметр FX: номер или подстрока имени; JSFX - родные единицы, VST - 0..1
#   --vol ТРЕК=dB               фейдер
#   --itemvol ТРЕК=dB           громкость всех айтемов трека (до цепочки), как в variants.py
#   --keep                      оставить файл на nb рядом с целью рендера
#   --proj ЧАСТЬ_ИМЕНИ          сначала переключиться на вкладку, путь которой содержит строку (иначе - текущая вкладка)
#   --final                     итоговый рендер в цель проекта ($project.mp3) без переименования, файл остаётся;
#                               прежний файл с этим именем заменяется. Имя рендера не нужно
#   --stems                     рендер «до» за один проход: мастер + стемы всех незаглушённых треков (формат проекта).
#                               Мастер остаётся на nb как <имя>.<ext> рядом с целью рендера, скачивается в <папка>/<имя>.<ext>;
#                               стемы скачиваются в <папка>/<имя>_<трек>.<ext>, меряются и удаляются с nb. Правки (--set и т.п.) не ставятся
#   --calib ПАПКА_ПРОЕКТА       с --stems: посчитать поправку модели (calib.py) в ПАПКА_ПРОЕКТА/calib.json.
#                               Песню с VST сначала заморозить (freeze.sh), иначе поправка гитары будет на Blue Cat
# ТРЕК: guitar | mic | master. Имя - латиница/цифры/_-. (файл <имя>.<формат проекта>).
# Рендер по настройкам проекта (42230); файл с именем цели рендера, если есть, не трогается.
# Если проект был сохранён (dirty 0), после возврата правок сохраняется снова; несохранённые правки пользователя не сохраняются.
# Печатает время рендера, изменённые параметры и замер (measure.py). Тишина = медиа офлайн (REAPER не в фокусе).
set -euo pipefail
DIR=$(cd "$(dirname "$0")" && pwd)
. "$DIR/env.sh"
solo=() mute=() bypass=() addfx=() copyfx=() set=() vol=() itemvol=(); proj=''; nomaster=false; keep=false; final=false; stems=false; calib=''
while [ $# -gt 0 ]; do
  case $1 in
    --solo) solo+=("$2"); shift 2;;
    --mute) mute+=("$2"); shift 2;;
    --bypass) bypass+=("$2"); shift 2;;
    --addfx) addfx+=("$2"); shift 2;;
    --copyfx) copyfx+=("$2"); shift 2;;
    --set) set+=("$2"); shift 2;;
    --vol) vol+=("$2"); shift 2;;
    --itemvol) itemvol+=("$2"); shift 2;;
    --proj) proj=$2; shift 2;;
    --nomaster) nomaster=true; shift;;
    --keep) keep=true; shift;;
    --final) final=true; keep=true; shift;;
    --stems) stems=true; shift;;
    --calib) calib=$2; shift 2;;
    -*) echo "неизвестная опция $1" >&2; exit 1;;
    *) break;;
  esac
done
if $final; then NAME=final; LOCAL=${1:-${TMPDIR:-/tmp}/reaper-song/render}; else NAME=${1:?имя рендера}; LOCAL=${2:-${TMPDIR:-/tmp}/reaper-song/render}; fi
[[ $NAME =~ ^[A-Za-z0-9_.-]+$ ]] || { echo "имя только латиницей: $NAME" >&2; exit 1; }
mkdir -p "$LOCAL"

q() { printf '[==[%s]==]' "$1"; }
lua=$(mktemp); trap 'rm -f "$lua"' EXIT

if $stems; then
  [ -z "$calib" ] || [ -d "$calib" ] || { echo "нет папки проекта $calib" >&2; exit 1; }
  # поправка снимается с локальной копии: проект на nb должен быть тем же, иначе она вберёт чужие фейдеры и JSFX
  [ -z "$calib" ] || bash "$DIR/nbcheck.sh" "$calib" ${proj:+--proj "$proj"}
  NB="C:\\rec\\2026\\reaper-song\\$NAME\\"
  {
    echo "local A = {mode = 'before', name = $(q "$NAME"), dir = $(q "$NB"), proj = $(q "$proj")}"
    [ -n "$proj" ] && cat "$DIR/bridge/select.lua"
    cat "$DIR/bridge/temp.lua" "$DIR/bridge/stems.lua"
  } > "$lua"
  res=$(bash "$DIR/bridge/bridge.sh" -t 900 "$lua") || { echo "$res"; exit 1; }
  echo "$res" | grep -v '^STEM\|^MASTER\|^OK' || true
  M=$(echo "$res" | grep '^MASTER' | cut -f2)
  ML="$LOCAL/${M##*\\}"; scp -q "$HOST:${M//\\//}" "$ML"
  files=("$ML") cargs=() rm=()
  while IFS=$'\t' read -r _ idx path tname; do
    f="$LOCAL/${NAME}_${tname// /_}.${path##*.}"
    scp -q "$HOST:${path//\\//}" "$f"
    files+=("$f"); cargs+=(--stem "$tname=$f"); rm+=("$path")
  done < <(echo "$res" | grep '^STEM')
  { for p in "${rm[@]}"; do printf 'os.remove(%s)\n' "$(q "$p")"; done; echo 'out("removed")'; } | bash "$DIR/bridge/bridge.sh" >/dev/null
  echo "мастер на nb: $M"
  uv run -q "$DIR/measure.py" "${files[@]}"
  [ -n "$calib" ] && uv run -q "$DIR/calib.py" "$calib" --master "$ML" "${cargs[@]}"
  exit 0
fi
{
  echo "local A = {name = $(q "$NAME"), nomaster = $nomaster, final = $final, solo = {}, mute = {}, bypass = {}, addfx = {}, copyfx = {}, set = {}, vol = {}, itemvol = {}}"
  for s in "${solo[@]+"${solo[@]}"}"; do echo "table.insert(A.solo, $(q "$s"))"; done
  for s in "${mute[@]+"${mute[@]}"}"; do echo "table.insert(A.mute, {$(q "${s%%=*}"), ${s#*=}})"; done
  for s in "${bypass[@]+"${bypass[@]}"}"; do echo "table.insert(A.bypass, {$(q "${s%%:*}"), $(q "${s#*:}")})"; done
  for s in "${addfx[@]+"${addfx[@]}"}"; do
    t=${s%%:*}; r=${s#*:}
    if [[ $r == *@* ]]; then echo "table.insert(A.addfx, {$(q "$t"), $(q "${r%@*}"), $(q "${r##*@}")})"
    else echo "table.insert(A.addfx, {$(q "$t"), $(q "$r")})"; fi
  done
  for s in "${copyfx[@]+"${copyfx[@]}"}"; do
    t=${s%%:*}; r=${s#*:}; src=${r%%:*}; r=${r#*:}
    if [[ $r == *@* ]]; then echo "table.insert(A.copyfx, {$(q "$t"), $(q "$src"), $(q "${r%@*}"), $(q "${r##*@}")})"
    else echo "table.insert(A.copyfx, {$(q "$t"), $(q "$src"), $(q "$r")})"; fi
  done
  for s in "${set[@]+"${set[@]}"}"; do
    t=${s%%:*}; r=${s#*:}; f=${r%:*}; pv=${r##*:}
    echo "table.insert(A.set, {$(q "$t"), $(q "$f"), $(q "${pv%%=*}"), ${pv#*=}})"
  done
  for s in "${vol[@]+"${vol[@]}"}"; do echo "table.insert(A.vol, {$(q "${s%%=*}"), ${s#*=}})"; done
  for s in "${itemvol[@]+"${itemvol[@]}"}"; do echo "table.insert(A.itemvol, {$(q "${s%%=*}"), ${s#*=}})"; done
  if [ -n "$proj" ]; then echo "A.proj = $(q "$proj")"; cat "$DIR/bridge/select.lua"; fi
  cat "$DIR/bridge/temp.lua" "$DIR/bridge/render.lua"
} > "$lua"

res=$(bash "$DIR/bridge/bridge.sh" -t 900 "$lua") || { echo "$res"; exit 1; }
echo "$res" | grep -v '^DEST\|^FINAL' | tail -n +2
DEST=$(echo "$res" | grep '^DEST' | cut -f2)
FINAL=$(echo "$res" | grep '^FINAL' | cut -f2 || true)
LF="$LOCAL/${DEST##*\\}"; [ -n "$FINAL" ] && LF="$LOCAL/${FINAL##*\\}"
scp -q "$HOST:${DEST//\\//}" "$LF"
if ! $keep || [ -n "$FINAL" ]; then printf 'out(os.remove(%s))\n' "$(q "$DEST")" | bash "$DIR/bridge/bridge.sh" >/dev/null; fi
uv run -q "$DIR/measure.py" "$LF"
