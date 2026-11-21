#!/usr/bin/env bash
# Заморозка VST: один рендер стемов в точке заморозки (выход последнего VST/VSTi трека) в <папка>/freeze/NN.wav.
# Дальше analyze.py берёт wav вместо айтемов и цепочки до этой точки и считает моделью всё после.
#   bash freeze.sh <локальная папка проекта> [--proj ЧАСТЬ_ИМЕНИ] [--force] [--lua-only]
#   --proj      вкладка REAPER по части пути (иначе - текущая)
#   --force     рендерить и треки с актуальной заморозкой
#   --lua-only  напечатать собранный lua рендера и выйти, ничего не запуская
# Отказывает, если проект на nb не сохранён или его треки с VST расходятся с локальной копией (тогда fetch.sh).
# Треки с актуальной заморозкой (отпечаток совпал) пропускаются. Всё временное в проекте возвращается.
set -euo pipefail
DIR=$(cd "$(dirname "$0")" && pwd)
. "$DIR/env.sh"
proj=''; force=false; luaonly=false; LOCAL=''
while [ $# -gt 0 ]; do
  case $1 in
    --proj) proj=$2; shift 2;;
    --force) force=true; shift;;
    --lua-only) luaonly=true; shift;;
    -*) echo "неизвестная опция $1" >&2; exit 1;;
    *) LOCAL=$1; shift;;
  esac
done
[ -n "$LOCAL" ] || { echo "нужна локальная папка проекта" >&2; exit 1; }
NB='C:\rec\2026\reaper-song\'
t0=$(date +%s)

todo=() names=() cached=()
while IFS=$'\t' read -r idx point isc name after key; do
  if [ "$isc" = 1 ] && ! $force; then cached+=("$name"); else todo+=("$idx:$point"); names+=("$name"); fi
done < <(python3 "$DIR/freezelib.py" todo "$LOCAL")
join() { local IFS=,; echo "$*" | sed 's/,/, /g'; }
if [ ${#todo[@]} -eq 0 ]; then
  if [ ${#cached[@]} -gt 0 ]; then echo "заморозка актуальна: $(join "${cached[@]}")"; else echo "нечего замораживать: нет VST/VSTi на треках"; fi
  exit 0
fi
[ ${#cached[@]} -gt 0 ] && echo "заморозка актуальна: $(join "${cached[@]}")"

q() { printf '[==[%s]==]' "$1"; }
head_lua() {
  echo "local A = {mode = 'freeze', dir = $(q "$NB"), proj = $(q "$proj"), tracks = {}}"
  for t in "${todo[@]}"; do echo "table.insert(A.tracks, {index = ${t%%:*}, point = ${t##*:}})"; done
  [ -n "$proj" ] && cat "$DIR/bridge/select.lua"
  return 0
}
lua=$(mktemp); chk=$(mktemp); got=$(mktemp); trap 'rm -f "$lua" "$chk" "$got"' EXIT
{ head_lua; cat "$DIR/bridge/temp.lua" "$DIR/bridge/stems.lua"; } > "$lua"
if $luaonly; then cat "$lua"; exit 0; fi

# проект на nb = локальная копия, иначе отпечатки посчитаны не по тому, что рендерится
{ head_lua; cat "$DIR/bridge/rppcopy.lua"; } > "$chk"
res=$(bash "$DIR/bridge/bridge.sh" "$chk") || { echo "$res"; exit 1; }
RPPNB=$(echo "$res" | grep '^RPP' | cut -f2)
scp -q "$HOST:${RPPNB//\\//}" "$got"
printf 'out(os.remove(%s))\n' "$(q "$RPPNB")" | bash "$DIR/bridge/bridge.sh" >/dev/null
if echo "$res" | grep -q $'^dirty\t1'; then echo "проект на nb не сохранён (dirty): сохранить или спросить пользователя" >&2; exit 1; fi
# сверка по отпечаткам, не побайтно: выделение и время сохранения в .rpp меняются без правок
cp "$got" "$got.rpp"
if [ "$(python3 "$DIR/freezelib.py" todo "$LOCAL" | cut -f1,2,4,6)" != "$(python3 "$DIR/freezelib.py" todo "$LOCAL" --rpp "$got.rpp" | cut -f1,2,4,6)" ]; then
  rm -f "$got.rpp"; echo "локальная копия проекта расходится с проектом на nb в треках с VST: скачать заново fetch.sh" >&2; exit 1
fi
rm -f "$got.rpp"
echo "замораживаю: $(join "${names[@]}")"
res=$(bash "$DIR/bridge/bridge.sh" -t 900 "$lua") || { echo "$res"; exit 1; }
echo "$res" | grep -v '^STEM\|^OK' || true
mkdir -p "$LOCAL/freeze"
idxs=() rm=()
while IFS=$'\t' read -r _ idx path; do
  scp -q "$HOST:${path//\\//}" "$LOCAL/freeze/$(printf '%02d' $((idx + 1))).wav"
  idxs+=("$idx"); rm+=("$path")
done < <(echo "$res" | grep '^STEM')
python3 "$DIR/freezelib.py" save "$LOCAL" "${idxs[@]}"
{ for p in "${rm[@]}"; do printf 'os.remove(%s)\n' "$(q "$p")"; done; echo 'out("removed")'; } | bash "$DIR/bridge/bridge.sh" >/dev/null
echo "время: $(( $(date +%s) - t0 )) с"
