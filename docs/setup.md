# Установка: macOS и Reaper MCP

Первая версия сетапа - на Mac с агрегатным устройством и мостом Reaper MCP. Сейчас песни пишутся на Windows-ноутбуке через собственный мост скилла `reaper-song` (см. README); этот документ - установка исходного варианта и общие для обеих платформ шаги.

Установка сетапа «запись голоса с гитарой в REAPER + агент с замерами» с нуля - на macOS и на Windows. Рабочие инструкции по самому сведению - в `CLAUDE.md` и в скилле `.claude/skills/guitar-vocal-mix/`; здесь только установка и то, что на платформах делается по-разному.

Рабочая машина - macOS, всё описанное для неё проверено на живом сетапе. Windows-ветка собрана по документации и **на этом железе не проверялась**; места, где это критично, отмечены отдельно.

## Что одинаково на обеих платформах

- **Скиллы и `CLAUDE.md`** - обычные markdown-файлы, правок не требуют.
- **Формат `.RPP`** - одинаковый на всех платформах, включая CRLF в переводах строк и ровно 64 токена в строке параметров JSFX.
- **Все плагины, которыми сводится микс, штатные.** `sstillwell/hpflpf`, `sstillwell/rbj4eq`, `sstillwell/1175`, `sstillwell/expander`, `Liteon/presenceeq`, `Liteon/deesser`, `loser/MGA_JSLimiterST` лежат в поставке REAPER. Ни ReaPack, ни ручная установка не нужны.
- **Проектный шаблон** - `.RPP` копируется как есть, но входы придётся переназначить: номера каналов зависят от звукового устройства.
- **Команды `uv`, `phantom`, `ffmpeg`** - одни и те же, различаются только способ их установки и пути.

## Пути: таблица соответствий

Дальше по тексту пути даны для обеих систем, здесь сводка.

| Что | macOS | Windows |
|---|---|---|
| Ресурсы REAPER | `~/Library/Application Support/REAPER/` | `%APPDATA%\REAPER\` |
| Бинарник REAPER | `/Applications/REAPER.app/Contents/MacOS/REAPER` | `C:\Program Files\REAPER (x64)\reaper.exe` |
| Штатные JSFX (исходники) | `/Applications/REAPER.app/Contents/InstallFiles/Effects/` | `C:\Program Files\REAPER (x64)\InstallFiles\Effects\` |
| Конфиг MCP | `~/.mcp.json` | `%USERPROFILE%\.mcp.json` |
| Клон `reaper-mcp` | `~/.phantom/reaper-mcp` | `%USERPROFILE%\.phantom\reaper-mcp` |
| Каталог обмена моста | `~/Library/Application Support/REAPER/Scripts/mcp_bridge_data` | `%APPDATA%\REAPER\Scripts\mcp_bridge_data` |

Portable-установка REAPER на Windows ломает эту таблицу: она кладёт настройки рядом с exe и `%APPDATA%\REAPER\` не использует. Ставить обычным инсталлятором.

## Звуковой тракт - главное различие

Два USB-устройства (микрофон ATR2100x и гитарный NUX Mighty Air) надо отдать REAPER одновременно, как один вход на 4 канала.

### macOS - агрегатное устройство

Штатный механизм системы. Собирается в Audio MIDI Setup:

1. Создать Aggregate Device, включить в него ATR2100x и NUX Mighty Air.
2. Порядок подустройств задаёт нумерацию каналов: входы 1-2 - ATR (микрофон моно, продублирован на оба канала), 3-4 - NUX (стерео).
3. Мастер-клок - **выход ATR**, то есть то устройство, в которое идёт мониторинг (наушники воткнуты в мини-джек микрофона).
4. Drift compensation - **включить** на входе ATR и на NUX, у мастера **выключить**. Без этого два независимых USB-клока разъезжаются.
5. Частота - 48 кГц на всех подустройствах.

Конфигурация оседает в `/Library/Preferences/Audio/com.apple.audio.SystemSettings.plist` и переживает перезагрузку.

**UID USB-устройства содержит номер порта.** Микрофон, переткнутый в другой разъём, становится для агрегата другим устройством, его подустройства мертвеют, и агрегат отдаёт 2 входа вместо 4. Держать ATR в одном порту; если агрегат развалился, пересобрать его состав в Audio MIDI Setup.

**Доступ к микрофону.** При первом запуске REAPER macOS спросит разрешение; если промахнуться мимо диалога, входы будут молчать и это выглядит как мёртвое устройство. Чинится в System Settings → Privacy & Security → Microphone.

### Windows - агрегата нет

Такого механизма в системе нет, и это главная работа при переносе. Варианты, все со своими минусами, ни один на этом железе не проверен:

| Способ | Суть | Риски |
|---|---|---|
| **FlexASIO** | ASIO-обёртка поверх WASAPI, умеет разные устройства на вход и выход | Настраивается текстовым конфигом, латентность выше нативного ASIO |
| **ASIO4ALL** | ASIO-обёртка поверх WDM, в панели можно включить несколько устройств сразу | Со связкой двух USB-устройств работает нестабильно, это её известное слабое место |
| **VoiceMeeter (Banana/Potato)** | Виртуальный микшер, сводит устройства и отдаёт в REAPER одним ASIO-устройством | Асинхронный ресемплинг, лишнее звено в тракте |
| **Два прохода** | Писать гитару и голос по очереди, каждое своим устройством | Теряется живое исполнение целиком, для этого сетапа не годится |

Проблема расхождения клоков никуда не денется: два USB-устройства тактируются независимо. Аналог drift compensation в обёртках выше называется по-разному или отсутствует - это первое, что надо проверить длинным тестовым дублем: записать 10 минут и посмотреть, не уехали ли дорожки друг относительно друга к концу.

## Установка

### 0. Предварительно

Нужен `git` (для клона моста) и терминал.

- **macOS**: `git --version` вызовет установку Command Line Tools, если их нет. Homebrew - <https://brew.sh>.
- **Windows**: `winget install --id=Git.Git -e`. После каждой установки через winget **открывать новый терминал**, иначе PATH не обновится и `uv`/`ffmpeg` «не найдены».

### 1. REAPER

Ставится как обычно, с сайта. Настройки живут в ресурсах REAPER (см. таблицу путей): `reaper.ini`, `Effects\`, `Scripts\`, `ProjectTemplates\`.

Целевые значения устройства одинаковы: **48 кГц, буфер около 128 сэмплов** (~2.7 мс). Если трещит - поднимать до 256, латентность вырастет до ~5.3 мс.

**macOS** - можно прописать прямо в `~/Library/Application Support/REAPER/reaper.ini` при закрытом REAPER:

```ini
coreaudioindevnew=guitar and mic
coreaudiooutdevnew=guitar and mic
coreaudiosrate=48000
coreaudiosrateuse=1
coreaudioignprojsr=1
coreaudiobs=128
newprojdo=1
newprojtmpl=…/ProjectTemplates/guitar and mic.RPP
```

**Windows** - этих ключей нет, они CoreAudio-специфичные. Устройство, частоту и буфер настраивать через Preferences → Audio → Device, шаблон по умолчанию - через Preferences → Project → Default project settings.

Шаблон проекта `guitar and mic.RPP` положить в `ProjectTemplates/` внутри ресурсов REAPER. Он создаёт два трека: `guitar` (стерео-вход 3/4) и `mic` (моно-вход 1), 48 кГц, запись в `Media/`, готовые цепочки JSFX. Номера входов после смены звукового устройства переназначить.

**Обязательно проверить в шаблоне `TIMELOCKMODE 0`.** Это временная привязка айтемов. При значении `1` смена темпа необратимо растягивает записанные дубли - этим уже испорчены два проекта, разбор в `CLAUDE.md`, раздел REAPER.

### 2. uv

Phantom ставится как инструмент uv. Нужен python 3.10-3.13, 3.14 пока не поддерживается - uv при необходимости скачает подходящий сам.

```bash
# macOS
brew install uv
# либо без Homebrew:
curl -LsSf https://astral.sh/uv/install.sh | sh
```

```powershell
# Windows
winget install --id=astral-sh.uv -e
```

На macOS после установки: `uv tool update-shell`, иначе `~/.local/bin` не окажется в PATH и поставленные инструменты не запустятся. Проверка на обеих системах - `uv --version`.

### 3. Phantom - замеры

Команда одна и та же, кавычки вокруг квадратных скобок нужны и в zsh, и в PowerShell:

```bash
uv tool install "phantom-audio[matching,processing]"
```

Экстры важны: без `matching` и `processing` не будет части инструментов. Исходники и документация - <https://github.com/fadelabs/phantom>.

Проверка: `phantom --help` и `phantom-mcp --help` должны отработать.

### 4. Reaper MCP - мост в живую сессию

```bash
# macOS
git clone https://github.com/fadelabs/reaper-mcp ~/.phantom/reaper-mcp
```

```powershell
# Windows
git clone https://github.com/fadelabs/reaper-mcp "$env:USERPROFILE\.phantom\reaper-mcp"
```

Зависимости ставить не надо: в репозитории есть `pyproject.toml` и `uv.lock`, `uv run` поднимет окружение сам при первом запуске сервера.

Дальше - мост внутри REAPER:

1. Скопировать `reaper_mcp_bridge.lua` из клона в `Scripts/` внутри ресурсов REAPER.
2. Проверить разово: в REAPER Actions → Show action list → Load ReaScript → выбрать скрипт → Run. В консоли должно появиться `REAPER MCP Bridge started`.
3. **Автозапуск.** Готового `__startup.lua` в репозитории нет, его надо создать самому в том же `Scripts/` - REAPER выполняет этот файл при старте. Внутри - вызов `dofile` на путь к `reaper_mcp_bridge.lua`. Без автозапуска мост придётся поднимать руками после каждого открытия REAPER.
4. Зависимостей у самого моста нет - используется стоковый Lua внутри REAPER. LuaSocket нужен только для HTTP-режима, который здесь не используется: файловый режим работает из коробки.

**Мост живёт только пока REAPER запущен.** При закрытом REAPER все `mcp__reaper__*` отвечают таймаутом. На macOS замечено: запуск REAPER с файлом проекта в аргументах (`open -a REAPER file.RPP`) не поднимает `__startup.lua` и мост не стартует - открывать REAPER обычным способом, а проект уже изнутри.

### 5. Конфиг MCP

**macOS** - `~/.mcp.json`. `REAPER_BRIDGE_DIR` можно не задавать: дефолт моста уже совпадает с реальным путём.

```json
{
  "mcpServers": {
    "phantom": { "command": "phantom-mcp", "args": [] },
    "reaper": {
      "command": "uv",
      "args": ["run", "--directory", "/Users/<user>/.phantom/reaper-mcp",
               "python", "reaper_mcp_server.py"],
      "cwd": "/Users/<user>/.phantom/reaper-mcp"
    }
  }
}
```

**Windows** - `%USERPROFILE%\.mcp.json`, путь к каталогу обмена задать явно:

```json
{
  "mcpServers": {
    "phantom": { "command": "phantom-mcp", "args": [] },
    "reaper": {
      "command": "uv",
      "args": ["run", "--directory", "C:\\Users\\<user>\\.phantom\\reaper-mcp",
               "python", "reaper_mcp_server.py"],
      "cwd": "C:\\Users\\<user>\\.phantom\\reaper-mcp",
      "env": { "REAPER_BRIDGE_DIR": "C:\\Users\\<user>\\AppData\\Roaming\\REAPER\\Scripts\\mcp_bridge_data" }
    }
  }
}
```

Включить серверы для проекта - в `.claude/settings.local.json` (в git не хранится): `{"enabledMcpjsonServers": ["phantom", "reaper"]}`.

### 6. ffmpeg

Нужен для вырезания рабочих участков, склейки айтемов и конвертации перед замером.

```bash
# macOS
brew install ffmpeg
```

```powershell
# Windows
winget install --id=Gyan.FFmpeg -e
```

## Рендер

Мост `mcp__reaper__render_project` использовать можно, но с двумя оговорками, добытыми дорого:

- формат берётся из **последних настроек рендера в REAPER**, а не из расширения в переданном пути - просишь `.wav`, получаешь `.mp3`, мост ждёт несуществующий `.wav` и репортит «File request timed out», хотя рендер прошёл;
- не-ASCII в пути ломается: мост экранирует символы в `\uXXXX`, а REAPER создаёт по каталогу на каждый escape - однажды выросло дерево на 53 уровня с рендером на дне.

Надёжнее рендерить из командной строки, на **копии** проекта, при **закрытом** REAPER (второй инстанс полезет за тем же аудиоустройством):

```bash
# macOS
/Applications/REAPER.app/Contents/MacOS/REAPER -renderproject /path/to/copy.rpp
```

```powershell
# Windows
& "C:\Program Files\REAPER (x64)\reaper.exe" -renderproject C:\path\to\copy.rpp
```

REAPER отрендерит и выйдет сам. В копии проекта прописать `RENDER_FILE` полным путём, `SAMPLERATE 48000 1 1` (иначе офлайн-инстанс возьмёт частоту устройства, обычно 44.1) и абсолютные пути в `FILE`, если копия лежит вне папки песни. Формат берётся из `<RENDER_CFG>` копии. Тем же способом снимаются стемы: заглушить трек через `MUTESOLO 1 0 0` и отключить мастер-цепочку через `MASTER_FX 0`.

## Отдельно про имена файлов

Папки песен на macOS названы кириллицей (`Ольга Арефьева - Мотенька`). Это уже стоило одного мусорного дерева на 53 уровня из-за экранирования в мосте. На Windows к этому добавляются кодировки консоли, так что для нового материала лучше держать пути ASCII, а исполнителя и название писать внутри проекта.

Ещё: **phantom не читает mp3** - перед замером конвертировать в wav.

## Порядок проверки после установки

1. `uv --version`, `phantom --help` и `phantom-mcp --help` отвечают.
2. `ffmpeg -version` отвечает.
3. REAPER видит нужное устройство, 48 кГц, вход микрофона моно, вход гитары стерео.
4. Мост поднимается: при запущенном REAPER `mcp__reaper__get_project_name` возвращает имя проекта, а не таймаут.
5. Тестовый дубль на 10 минут: дорожки не разъехались к концу. На Windows это главная проверка выбранной ASIO-обёртки.
6. Пробный рендер из CLI: длина совпадает с проектом, частота 48 кГц.
7. `mcp__phantom__full_diagnostic` по этому рендеру отрабатывает.
