# Настройки окружения для скриптов скилла. Подключать: . "$(dirname "$0")/env.sh"
#   REAPER_NB_HOST      ssh-хост Windows-машины с REAPER (обязательно)
#   REAPER_NB_PROJECTS  папка проектов REAPER на ней (по умолчанию C:\projects\music\reaper)
# Берутся из окружения; чего там нет - из .env в корне репозитория (образец - .env.example).
_env_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)
if [ -f "$_env_root/.env" ]; then
  while IFS='=' read -r _k _v || [ -n "$_k" ]; do
    case $_k in ''|\#*) continue;; esac
    _v=${_v%$'\r'}
    [ -z "${!_k:-}" ] && export "$_k=$_v"
  done < "$_env_root/.env"
fi
: "${REAPER_NB_HOST:?задай REAPER_NB_HOST в окружении или в .env в корне репозитория (см. .env.example)}"
REAPER_NB_PROJECTS=${REAPER_NB_PROJECTS:-'C:\projects\music\reaper'}
HOST=$REAPER_NB_HOST
