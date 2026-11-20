#!/usr/bin/env bash
# Снимок состояния проекта, которое рендер обязан вернуть (bridge/renderstate.lua): dirty, настройки рендера,
# выделение, фейдеры, паны, mute/solo, включённость FX. Сравнивать снимки до и после рендера: cmp.
#   bash renderstate.sh [--proj ЧАСТЬ_ИМЕНИ]
set -euo pipefail
DIR=$(cd "$(dirname "$0")" && pwd)
proj=''
[ "${1:-}" = "--proj" ] && { proj=$2; shift 2; }
q() { printf '[==[%s]==]' "$1"; }
lua=$(mktemp); trap 'rm -f "$lua"' EXIT
{
  echo "local A = {proj = $(q "$proj")}"
  [ -n "$proj" ] && cat "$DIR/bridge/select.lua"
  cat "$DIR/bridge/renderstate.lua"
} > "$lua"
bash "$DIR/bridge/bridge.sh" "$lua"
