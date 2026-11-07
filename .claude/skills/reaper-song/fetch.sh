#!/usr/bin/env bash
# Скачать проект REAPER с nb: .rpp и только те файлы Media, на которые он ссылается.
#   bash fetch.sh [часть имени проекта] [папка назначения]
# Без имени берёт последний изменённый .rpp. Печатает локальную папку проекта последней строкой.
set -euo pipefail
DIR=$(dirname "$0")
. "$DIR/env.sh"
Q=${1:-}; DEST=${2:-${TMPDIR:-/tmp}/reaper-song}
tmp=$(mktemp -d)
{ printf '\xef\xbb\xbf'; R=${REAPER_NB_PROJECTS//\\/\\\\}; sed -e "s/__Q__/${Q//\//\\/}/" -e "s/__ROOT__/${R//\//\\/}/g" "$DIR/find-latest.ps1"; } > "$tmp/f.ps1"
scp -q "$tmp/f.ps1" "$HOST:reaper-song-find.ps1"
OUT=$(ssh "$HOST" "powershell -NoProfile -ExecutionPolicy Bypass -File reaper-song-find.ps1 & del reaper-song-find.ps1" | tr -d '\r')
echo "$OUT" | grep -v '^RPP=' >&2
RPP=$(echo "$OUT" | grep '^RPP=' | head -1 | cut -d= -f2-)
[ -n "$RPP" ] || { echo "проект не найден" >&2; exit 1; }
WIN_DIR=${RPP%\\*}; NAME=${WIN_DIR##*\\}
LOCAL="$DEST/$NAME"; mkdir -p "$LOCAL/Media"
scp -q "$HOST:${RPP//\\//}" "$LOCAL/"
RPPL="$LOCAL/${RPP##*\\}"
tr -d '\r' < "$RPPL" | grep -oP 'FILE "\K[^"]+' | sort -u | while read -r f; do
  f=${f//\\//}; mkdir -p "$LOCAL/$(dirname "$f")"
  [ -f "$LOCAL/$f" ] || scp -q "$HOST:${WIN_DIR//\\//}/$f" "$LOCAL/$f" || echo "нет файла: $f" >&2
done
echo "rpp: ${RPP}" >&2
echo "$LOCAL"
