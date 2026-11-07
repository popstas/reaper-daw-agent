# reaper-daw-agent

Набор для [Claude Code](https://claude.com/claude-code): агент проверяет и сводит домашние записи «голос + гитара» в REAPER. Он скачивает проект, считает, как звучит микс после всех эффектов, сравнивает с ориентирами, предлагает правки с цифрами и после согласия применяет их в открытом REAPER.

*Claude Code skills that check and mix voice + guitar recordings in REAPER: a model of the FX chain, renders with temporary changes, loudness measurements and a live Lua bridge into the running REAPER session. Docs are in Russian.*

## Что умеет

- **Отчёт по песне.** Громкость голоса и гитары по ходу песни и их баланс, работа компрессоров и гейта, громкость и пики на выходе, свистящие, провалы на стыках дублей. Каждая проблема — с конкретным значением параметра.
- **Модель цепочки без рендера.** `analyze.py` прогоняет дубли через те же штатные JSFX, что стоят в проекте: фильтры, эквалайзер, компрессор 1175, лимитер, шумодав. Так варианты правок проверяются за секунды. От рендера модель отличается примерно на 0.5 LU.
- **Рендер с временными правками.** Соло, отключённый мастер, выключенный эффект, другой порог или фейдер — рендер, замер, и всё возвращается как было.
- **Правки в живой сессии.** Мост на Lua исполняет команды внутри запущенного REAPER: параметры меняются одним шагом отмены, проект сохраняется. Закрывать REAPER не нужно.

## Как устроено

```
Linux / macOS                          Windows
Claude Code + скиллы  ── ssh, scp ──▶  REAPER 7
  analyze.py, variants.py                bridge.lua: исполняет cmd.lua,
  render.sh, measure.py                  пишет ответ в result.txt
  копия проекта + дубли                  проекты и дубли
```

Анализ идёт на копии проекта: скачиваются `.rpp` и только используемые дубли. В живой REAPER агент ходит через мост и меняет что-то только после твоего «да».

## Скиллы

| Скилл | Что делает |
|---|---|
| [`reaper-song`](.claude/skills/reaper-song/SKILL.md) | Основной: проверка песни на Windows-машине, модель, варианты, рендер, правки через мост. Запуск — `/reaper-song [часть имени проекта]` |
| [`guitar-vocal-mix`](.claude/skills/guitar-vocal-mix/SKILL.md) | Процедура сведения, правила правки `.RPP`, порядок слайдеров штатных плагинов |
| `reaper-jsfx-core`, `reaper-jsfx-audio` | Справочник по написанию своих JSFX. Автор — Mads Thines Coello, лицензия MIT; лежат здесь как копии |

Скрипты `reaper-song`:

| Скрипт | Зачем |
|---|---|
| `fetch.sh` | скачать последний изменённый проект (или найденный по имени) и его дубли |
| `analyze.py` | модель микса по цепочкам из проекта |
| `variants.py` | прогнать варианты правок через модель: `mic/1175:1=-14`, `guitar/vol=-4`, `mic/itemvol=-8` |
| `render.sh` | рендер в живой сессии с временными правками, скачивание, замер |
| `measure.py` | громкость (LUFS), разброс (LRA), true peak, доли полос спектра |
| `rawcheck.py` | срезы в сырых дублях, уровни выше 0 dBFS, разница каналов |
| `bridge/` | мост: `bridge.lua` и `call.ps1` на Windows, `bridge.sh` — клиент |

## Что нужно

- [Claude Code](https://claude.com/claude-code), [uv](https://docs.astral.sh/uv/), `ffmpeg`, `ssh`/`scp`.
- Windows-машина с REAPER 7, на ней OpenSSH Server, вход по ключу и PowerShell 5+.
- Python-зависимости скриптов (`numpy`, `scipy`, `soundfile`) `uv run` ставит сам.

## Установка

1. Склонировать репозиторий и открыть его в Claude Code.
2. Задать хост и папку проектов:
   ```bash
   cp .env.example .env   # REAPER_NB_HOST, REAPER_NB_PROJECTS, REAPER_ARCHIVE_DIR
   ```
   Переменные из окружения важнее `.env`. Файл `.env` в git не попадает.
3. Поставить мост на Windows. В папку ресурсов REAPER (`%APPDATA%\REAPER`):
   - `bridge\bridge.lua` и `bridge\call.ps1` → `%APPDATA%\REAPER\bridge\`
   - `bridge\__startup.lua` → `%APPDATA%\REAPER\Scripts\__startup.lua` (если файл уже есть, добавить в него строку `dofile`)

   Перезапустить REAPER.
4. Проверить:
   ```bash
   echo 'info()' | bash .claude/skills/reaper-song/bridge/bridge.sh
   ```
   Ответ `OK` с путём открытого проекта значит, что всё работает. `BRIDGE_DOWN` — REAPER не запущен или мост не стартовал.

Установка первой версии сетапа на Mac (агрегатное устройство, Phantom, Reaper MCP) — в [docs/setup.md](docs/setup.md).

## Как пользоваться

В Claude Code:

```
/reaper-song               последний изменённый проект
/reaper-song Ветер         проект, в имени которого есть «Ветер»
```

Агент выдаёт отчёт: вердикт, что поправить и на сколько, что в порядке. Дальше можно попросить проверить другой вариант, отрендерить или применить правки. Скрипты запускаются и вручную, например:

```bash
python3 .claude/skills/reaper-song/variants.py "<папка проекта>" base "mic/1175:1=-14 mic/1175:3=2"
bash .claude/skills/reaper-song/render.sh --solo mic --nomaster mic_stem /tmp/render
```

## Ограничения

- Заточено под конкретный сетап: микрофон ATR2100x-USB, гитара через NUX Mighty Air, шаблон проекта `guitar and mic` с треками `guitar` и `mic`. Ориентиры в `SKILL.md` подобраны на этих записях. Шаблон и свой шумодав `guitar_noise_gate.jsfx` в репозиторий не входят, их состав описан в скилле.
- Модель не считает VST (например, усилитель Blue Cat), ReaVerb и де-эссер. Треки с VST до компрессора проверяются рендером.
- Если окно REAPER не в фокусе, он может отключить медиа, и рендер выйдет тишиной. `render.sh` включает медиа перед рендером, а `measure.py` предупреждает о тишине.

## Структура

```
CLAUDE.md                 железо, окружение, состояние песен
docs/setup.md             установка первой версии на Mac
docs/TODO.md              открытые вопросы
.env.example              образец настроек
.claude/skills/           скиллы
```

## Лицензия

MIT, см. [LICENSE](LICENSE). Скиллы `reaper-jsfx-*` — MIT, автор Mads Thines Coello.
