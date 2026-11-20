# Заморозка VST и подбор вариантов моделью - план реализации

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Сократить сведение песни с VST до 3-4 минут работы инструментов. Для этого выход VST один раз замораживается в wav, а варианты, поправка по стемам и порог лимитера считаются моделью.

**Architecture:**
- Новый `freezelib.py` (только stdlib) разбирает цепочки, находит точку заморозки, считает отпечатки и ведёт `freeze.json`/`calib.json`.
- `analyze.py` подставляет заморозку, применяет поправки и подбирает порог.
- `variants.py` отказывает на правках до точки заморозки и гоняет варианты параллельно.
- В REAPER временные правки вынесены в `bridge/temp.lua`. Новый `bridge/stems.lua` рендерит стемы за один проход: для заморозки (`freeze.sh`) и для рендера «до» (`render.sh --stems`).

**Tech Stack:**
- Python 3.10+ через `uv run`: numpy, scipy, soundfile, pyloudnorm, numba; тесты - pytest.
- Lua внутри REAPER 7.85 через мост.
- bash, ssh/scp до nb.

**Spec:** `docs/superpowers/specs/2026-11-21-freeze-model-design.md`

## Global Constraints

- Все пути ниже - от `.claude/skills/reaper-song/`. Тесты: `uv run --with pytest --with numpy --with scipy --with soundfile --with pyloudnorm --with numba pytest tests -q` из этой папки.
- Частота 48 кГц, сигналы модели стерео `(n, 2)` float64.
- Классы FX:
  - моделируемые - ключи `FX` в `analyze.py`;
  - мелкие - подстроки `ReaVerb` и `Liteon/deesser`;
  - остальные запускают заморозку: VST, VSTi, CLAP, незнакомый JSFX.
- Точка заморозки - выход последнего активного (BYPASS 0) запускающего FX.
- Всё, что скачивается с nb, - под латинскими именами. Файл заморозки: `freeze/NN.wav`, NN - номер трека с 1, две цифры.
- Заморозка: WAV 32 bit float, 48 кГц, от начала проекта, на nb в `C:\rec\2026\reaper-song\`, после скачивания удаляется.
- Рендер «до»: мастер остаётся на nb как `C:\rec\2026\<имя>_before.mp3`, стемы скачиваются, меряются и удаляются с nb.
- Перед каждым рендером `Main_OnCommand(40101, 0)`. Рендер - `Main_OnCommand(42230, 0)`.
- После любого рендера проект с прежним `dirty`. `RENDER_SETTINGS`, `RENDER_FORMAT`, `RENDER_FILE`, `RENDER_PATTERN`, `RENDER_BOUNDSFLAG`, выделение треков, фейдеры, паны, байпасы - как до рендера, в том числе при ошибке.
- `--target`: прогноз рендера = цель ± 0.1 LU. Без `calib.json` поправка мастера +0.5, это пишется в строке.
- Параллельно идут до `min(число вариантов, os.cpu_count() - 2)` вариантов, у каждого своя копия `zz-variant-<n>.rpp`.
- Приёмка: поправка трека ≤ 1 LU по модулю. Прогноз чужого состояния против рендера - в пределах 0.3 LU.
- В командах только скрипты скилла, без разового inline-кода (правило `SKILL.md`).

## Review Focus

1. **Трек переименовали или переставили после заморозки.** Ожидается строка «заморозка устарела», а не чужой wav. `freeze.json` хранит имя и номер, совпадать должны оба. Тест `test_status_renamed_track` в Task 1.
2. **Wav заморозки короче или длиннее проекта** (хвост реверба, сдвинутый айтем). Ожидается, что сигнал обрезан или добит нулями до длины модели, без падения. Тест `test_freeze_length_mismatch` в Task 2.
3. **`freeze.sh` на `dirty` проекте или не на той вкладке.** Ожидается отказ до рендера с причиной. Проверка - шаг Task 6 с несуществующей `--proj`; проверка `dirty` в коде `stems.lua`.
4. **Ошибка посреди рендера стемов.** Ожидается, что всё временное возвращено. Проверка - шаг Task 6 с несуществующим треком в плане, затем `bridge/renderstate.lua` совпадает с замером до.
5. **Недостижимая `--target`.** Цель громче, чем даёт порог −30, или тише, чем при пороге 0. Ожидается строка «цель недостижима: при пороге −30 прогноз X», без исключения. Тест `test_target_unreachable` в Task 3.

---

### Task 1: freezelib.py - разбор цепочек, точка заморозки, отпечатки, кэш

**Files:**
- Create: `freezelib.py`
- Test: `tests/test_freezelib.py`, `tests/conftest.py`: фикстура `rpp_text`, минимальный `.rpp` с треками `guitar` (gate, hpflpf, rbj4eq, VST Blue Cat с двумя base64-строками, 1175, ReaVerb), `drums` (VSTi MT-PowerDrumKit, MIDI-айтем без FILE, ReaVerb BYPASS 1), `mic` (hpflpf, 1175, deesser, ReaVerb) и мастером с 1175 BYPASS 1 и MGA_JSLimiterST; CRLF.

**Interfaces:**
- Produces:
  - `MODELED: frozenset[str]` - `{'sstillwell/hpflpf', 'sstillwell/rbj4eq', 'sstillwell/1175', 'Liteon/presenceeq', 'popstas/guitar_noise_gate.jsfx', 'loser/MGA_JSLimiterST'}`
  - `MINOR: tuple[str, ...]` - `('ReaVerb', 'Liteon/deesser')`
  - `fx_blocks(chain_text: str) -> list[dict]` - ключи `bypass: bool`, `kind: str` (JS/VST/VST3/VSTi/CLAP), `name: str`, `p: list[str]` (параметры JSFX, у VST пусто), `text: str` (блок от строки BYPASS до закрывающей `>` включительно)
  - `kind_of(fx: dict) -> str` - `'model' | 'minor' | 'trigger'`
  - `freeze_point(fxs: list[dict]) -> int | None` - индекс в `fxs`
  - `split_tracks(rpp_text: str) -> list[dict]` - `index: int` (с 0), `name: str`, `text: str` (без `\r`)
  - `master_fx(rpp_text: str) -> list[dict]`
  - `track_fx(track_text: str) -> list[dict]`
  - `track_key(track_text: str, fxs: list[dict], point: int) -> str` (sha1 hex)
  - `plan(rpp_text: str) -> list[dict]` - `index`, `name`, `point`, `after` (имя FX в точке), `key`, `file` (`freeze/NN.wav`)
  - `freeze_status(folder: str, entry: dict) -> str` - `'ok' | 'stale' | 'missing'`
  - `calib_key(rpp_text: str) -> str`
  - `load_json(folder: str, name: str) -> dict` (`{}` если нет файла), `save_json(folder: str, name: str, data: dict) -> None`
  - CLI `python3 freezelib.py plan <папка> [--rpp F]` - JSON-список плана с полем `cached: bool`; `python3 freezelib.py save <папка> [--rpp F] INDEX...` - записать эти треки в `freeze/freeze.json` с текущим временем.

- [ ] **Step 1: Write the failing tests**

```python
def test_fx_blocks_keep_vst_state(rpp_text):
    g = track_fx(split_tracks(rpp_text)[0]['text'])
    assert [f['kind'] for f in g] == ['JS', 'JS', 'JS', 'VST3', 'JS', 'VST']
    assert g[3]['p'] == [] and g[3]['text'].count('\n') >= 3   # base64 состояние внутри
    assert g[1]['name'] == 'sstillwell/hpflpf' and g[1]['p'][0] == '80'

def test_kind_and_point(rpp_text):
    t = split_tracks(rpp_text)
    assert [kind_of(f) for f in track_fx(t[0]['text'])] == ['model', 'model', 'model', 'trigger', 'model', 'minor']
    assert freeze_point(track_fx(t[0]['text'])) == 3          # после Blue Cat
    assert freeze_point(track_fx(t[1]['text'])) == 0          # MT-PowerDrumKit, дальше ничего моделируемого
    assert freeze_point(track_fx(t[2]['text'])) is None       # mic

def test_bypassed_trigger_ignored(rpp_text):
    txt = split_tracks(rpp_text)[0]['text'].replace('BYPASS 0 0 0\n      <VST3', 'BYPASS 1 0 0\n      <VST3')
    assert freeze_point(track_fx(txt)) is None

def test_key_ignores_after_point_and_volatile(rpp_text):
    t = split_tracks(rpp_text)[0]; fx = track_fx(t['text']); k = track_key(t['text'], fx, 3)
    after = t['text'].replace('-14 5 0 20 250 100', '-10 5 0 20 250 100')     # 1175 после точки
    vol = t['text'].replace('VOLPAN 0.70794578', 'VOLPAN 0.5')                # фейдер трека
    sel = t['text'].replace('SEL 0', 'SEL 1')
    for txt in (after, vol, sel):
        assert track_key(txt, track_fx(txt), 3) == k

def test_key_changes_before_point(rpp_text):
    t = split_tracks(rpp_text)[0]; fx = track_fx(t['text']); k = track_key(t['text'], fx, 3)
    for old, new in [('80 10000 -2', '80 10000 -5'), ('SOFFS 7.5', 'SOFFS 8'), ('AAAA', 'AAAB')]:  # hpflpf, айтем, состояние VST
        txt = t['text'].replace(old, new)
        assert track_key(txt, track_fx(txt), 3) != k

def test_plan_and_file_names(rpp_text):
    p = plan(rpp_text)
    assert [(e['index'], e['name'], e['point'], e['file']) for e in p] == [(0, 'guitar', 3, 'freeze/01.wav'), (1, 'drums', 0, 'freeze/02.wav')]
    assert 'Blue Cat' in p[0]['after']

def test_status_renamed_track(tmp_path, rpp_text):
    e = plan(rpp_text)[0]; (tmp_path / 'freeze').mkdir(); (tmp_path / e['file']).write_bytes(b'x')
    save_json(str(tmp_path / 'freeze'), 'freeze.json', {'tracks': {'0': dict(e, name='gtr')}})
    assert freeze_status(str(tmp_path), e) == 'stale'
    assert freeze_status(str(tmp_path), dict(e, index=5)) == 'missing'

def test_calib_key_minor_fx_only(rpp_text):
    k = calib_key(rpp_text)
    assert calib_key(rpp_text.replace('-14 5 0 20 250 100', '-10 5 0 20 250 100')) == k     # JSFX
    assert calib_key(rpp_text.replace('VOLPAN 1 0 -1 -1 1', 'VOLPAN 0.5 0 -1 -1 1')) == k  # фейдер
    assert calib_key(rpp_text.replace('BYPASS 1 0 0\n      <VST "VST: ReaVerb', 'BYPASS 0 0 0\n      <VST "VST: ReaVerb')) != k
    assert calib_key(rpp_text.replace('AAAA', 'AAAB')) != k                                  # заморозка
```

Фикстура должна содержать подстроки, на которые опираются замены: `80 10000 -2`, `SOFFS 7.5`, `AAAA` в base64 Blue Cat, `-14 5 0 20 250 100` у 1175 гитары, `SEL 0` в айтеме гитары, `VOLPAN 0.70794578` у трека гитары, `VOLPAN 1 0 -1 -1 1` у трека mic, ReaVerb барабанов с `BYPASS 1 0 0`.

- [ ] **Step 2: Run tests - FAIL (`ModuleNotFoundError: freezelib`)**

- [ ] **Step 3: Implement `freezelib.py`**
  - Блок FX: строка `BYPASS` и следующий блок `<JS`/`<VST…`/`<CLAP` до парной `>` по глубине вложенности.
  - Изменчивые строки, которые не входят ни в один отпечаток: `SEL`, `FLOATPOS`, `FLOAT`, `WAK`, `SHOW`, `LASTSEL`, `FXID`, `IID`, `GUID`, `IGUID`.
  - `track_key` - sha1 от: всех блоков `<ITEM` трека, `text` FX `[0..point]` и строки `FX <n>` трека.
  - `calib_key` - sha1 от: ключей `plan()` и `text` всех мелких FX на треках и мастере.
  - `freeze_status`:
    - `'ok'` - запись по `str(index)` есть, имя и ключ совпали, файл есть;
    - `'stale'` - запись есть, но не совпала;
    - `'missing'` - записи нет.

- [ ] **Step 4: Run tests - PASS**

- [ ] **Step 5: Commit** `git add freezelib.py tests/ && git commit -m "reaper-song: freezelib - точка заморозки и отпечатки"`

---

### Task 2: analyze.py - заморозка вместо айтемов, MIDI-треки, --json

**Files:**
- Modify: `analyze.py` (`parse_rpp`, цикл треков в `main`, аргументы)
- Test: `tests/test_analyze_freeze.py`; в `conftest.py`:
  - фикстура `project(tmp_path) -> str`: папка с `.rpp` из `rpp_text` (FILE айтемов указывают на `Media/g.wav`, `Media/m.wav`), 6 с розового шума: гитара −20 dBFS RMS моно, голос −18 dBFS RMS стерео;
  - помощники, которыми пользуются Task 2-4:
    - `pink(rms_db, seconds=6, ch=2) -> np.ndarray`;
    - `write_freeze(folder, index, signal)` - wav в `freeze/NN.wav` и запись в `freeze/freeze.json` по `freezelib.plan`;
    - `rpp(folder) -> str` - текст `.rpp`;
    - `edit_rpp(folder, old, new)`;
    - `edit_rpp_master_threshold(folder, thr)` - первый токен строки параметров `MGA_JSLimiterST` мастера;
    - `copy_project(folder) -> str` - копия папки без `freeze/` и `calib.json`;
    - `save_calib(folder, tracks, master, key=None)` - `calib.json`, `key` по умолчанию `freezelib.calib_key(rpp(folder))`;
    - `run(folder, *args) -> (stdout, dict)` - `uv run analyze.py <folder> --json <tmp> *args`.

**Interfaces:**
- Consumes: `freezelib.split_tracks`, `track_fx`, `master_fx`, `plan`, `freeze_status`, `load_json`, `MODELED`.
- Produces:
  - `parse_rpp(text) -> (mfx, tracks)`. У трека добавлены ключи `index`, `text`, `fx` (из `freezelib.track_fx`, тот же формат `bypass/kind/name/p/text`).
  - `track_signal(t: dict, folder: str, freeze_entry: dict | None, length: int | None) -> tuple[np.ndarray | None, list[dict], str]` - сигнал, цепочка к прогону, строка отчёта о заморозке (`''`, если трек не замораживается).
  - `--json PATH`: `{"tracks": {имя: {"lufs": float}}, "master_in": float, "master_out": float, "pred": float | null}`. `pred` заполняется в Task 3, здесь `null`.

- [ ] **Step 1: Write the failing tests**

```python
def test_modeled_set_matches():
    assert set(analyze.FX) == freezelib.MODELED

def test_frozen_guitar_uses_wav(project):
    write_freeze(project, 0, pink(-14))            # «выход Blue Cat» на 6 dB громче сырого
    out, js = run(project)
    assert 'заморожено после' in out and 'Blue Cat' in out
    assert 'не моделируется: VST3' not in out.split('## mic')[0]
    # 1175 гитары с порогом −14 жмёт сигнал −14 dBFS RMS: строка 1175 есть, LUFS трека выше, чем без заморозки
    out0, js0 = run(copy_project(project))
    assert js['tracks']['guitar']['lufs'] > js0['tracks']['guitar']['lufs'] + 3
    assert 'нет заморозки - freeze.sh' in out0

def test_stale_freeze_reported(project):
    write_freeze(project, 0, pink(-14)); edit_rpp(project, '80 10000 -2', '80 10000 -5')
    out, js = run(project)
    assert 'заморозка устарела' in out and 'freeze.sh' in out

def test_midi_drums_enter_model(project):
    write_freeze(project, 1, pink(-16))
    out, js = run(project)
    assert 'drums' in js['tracks']

def test_freeze_length_mismatch(project):
    write_freeze(project, 0, pink(-14, seconds=4))   # проект 6 с
    write_freeze(project, 1, pink(-16, seconds=9))
    out, js = run(project)
    assert js['master_out'] > -70
```

- [ ] **Step 2: Run tests - FAIL**

- [ ] **Step 3: Implement**
  - `parse_rpp` строит треки и цепочки через `freezelib`, мастер - через `freezelib.master_fx`. Разбор айтемов прежний.
  - `track_signal`:
    - `freeze_status == 'ok'`: wav с позиции 0, моно размножить в стерео, обрезать или добить нулями до `length`; цепочка `fx[point+1:]`; строка `заморожено после <after> (freeze <dd.mm HH:MM>)`.
    - `'stale'`: строка `заморозка устарела - freeze.sh`.
    - Запускающий FX есть, а записи нет (`'missing'`): `нет заморозки - freeze.sh`.
    - В обоих последних случаях - прежний путь через `build()` и полную цепочку.
  - Длина модели = максимум из концов айтемов и длин актуальных wav заморозки.
  - Секции «сырой», «стык» и пролаз печатаются, только если у трека есть аудио-айтемы. Сырой сигнал для пролаза - по-прежнему `build()`.
  - `--json` пишется в конце `main`.

- [ ] **Step 4: Run tests - PASS**; затем `uv run analyze.py "<скретчпад>/reaper-song/Янка Дягилева - Домой"`: отчёт как раньше, плюс строки «нет заморозки - freeze.sh» у guitar и drums.

- [ ] **Step 5: Commit** `git commit -m "reaper-song: analyze - заморозка VST, MIDI-треки, --json"`

---

### Task 3: analyze.py - поправки из calib.json, прогноз рендера, --target

**Files:**
- Modify: `analyze.py`
- Test: `tests/test_analyze_calib.py`

**Interfaces:**
- Consumes: `freezelib.calib_key`, `load_json`; `parse_rpp`, `track_signal` из Task 2.
- Produces:
  - `calib.json` = `{"key": str, "time": str, "tracks": {имя: float dB}, "master": float | null}`
  - `load_calib(folder: str, rpp_text: str) -> tuple[dict, str]` - поправки (`{}`, если устарели или нет) и строка отчёта.
  - `solve_threshold(mix: np.ndarray, mfx: list[dict], target: float, offset: float) -> dict` - ключи `ok: bool`, `thr: float`, `model: float`, `pred: float`, `note: str`
  - Флаги: `--target LUFS`, `--no-calib`.
  - В JSON `pred = master_out + поправка мастера`.

- [ ] **Step 1: Write the failing tests**

```python
def test_track_offsets_applied(project):
    _, js0 = run(project, '--no-calib')
    save_calib(project, tracks={'mic': 1.0}, master=0.4)        # key = freezelib.calib_key(текущий .rpp)
    out, js = run(project)
    assert abs(js['tracks']['mic']['lufs'] - js0['tracks']['mic']['lufs'] - 1.0) < 0.05
    assert abs(js['pred'] - js['master_out'] - 0.4) < 1e-6
    assert 'поправка' in out

def test_calib_stale(project):
    save_calib(project, tracks={'mic': 1.0}, master=0.4, key='old')
    out, js = run(project)
    assert 'поправка устарела' in out and abs(js['pred'] - js['master_out'] - 0.5) < 1e-6

def test_no_calib_flag(project):
    save_calib(project, tracks={'mic': 1.0}, master=0.4)
    _, js = run(project, '--no-calib'); _, js0 = run(project, '--no-calib')
    assert js['tracks']['mic'] == js0['tracks']['mic']

def test_target_hits(project):
    out, js = run(project, '--target', '-14')
    m = re.search(r'порог лимитера под -14.0 LUFS: (-?[\d.]+)', out); assert m
    edit_rpp_master_threshold(project, float(m[1]))
    _, js2 = run(project)
    assert abs(js2['pred'] - (-14)) <= 0.1

def test_target_unreachable(project):
    out, _ = run(project, '--target', '0')
    assert 'цель недостижима' in out
```

- [ ] **Step 2: Run tests - FAIL**

- [ ] **Step 3: Implement**
  - Поправка трека - усиление `10**(dB/20)` после фейдера, до суммы.
  - Поправка мастера: из `calib.json`; если её нет, `null` или ключ не совпал - +0.5.
  - Рядом со строкой мастера печатается `рендер ≈ X (поправка ±Y по рендеру до | по умолчанию)`.
  - `solve_threshold` берёт первый активный `loser/MGA_JSLimiterST` в `mfx` и прогоняет мастер-цепочку целиком с заменённым `p[0]`.
    - Бисекция по порогу в [−30, 0]: ниже порог - громче. До 12 шагов, стоп при |pred − target| ≤ 0.1.
    - Печать: `порог лимитера под {target:.1f} LUFS: {thr:.1f} (модель {model:.1f}, поправка {offset:+.1f})`.
    - Лимитера нет: `нет MGA_JSLimiterST на мастере`.
    - Цель вне диапазона: `цель недостижима: при пороге -30 прогноз X` (или `при пороге 0`).

- [ ] **Step 4: Run tests - PASS**

- [ ] **Step 5: Commit** `git commit -m "reaper-song: analyze - поправки по стемам и --target"`

---

### Task 4: variants.py - отказ до точки заморозки, параллельный прогон, --target

**Files:**
- Modify: `variants.py`
- Test: `tests/test_variants.py`

**Interfaces:**
- Consumes: `freezelib.plan`, `freeze_status`, `split_tracks`, `track_fx`; флаги `analyze.py --target`, `--json` (Task 2-3).
- Produces:
  - `check_edit(rpp_text: str, folder: str, edit: str) -> str | None` - текст отказа или `None`.
  - Вывод по-прежнему блоками `=== <вариант>` в порядке аргументов.
  - В `KEY` добавить: `заморожено|устарела|нет заморозки|поправк|рендер ≈|порог лимитера под|недостижима`.

- [ ] **Step 1: Write the failing tests**

```python
def test_refuse_before_point(project):
    write_freeze(project, 0, pink(-14))
    assert 'до заморозки' in check_edit(rpp(project), project, 'guitar/hpflpf:3=-5')
    assert 'render.sh --set' in check_edit(rpp(project), project, 'guitar/hpflpf:3=-5')
    assert check_edit(rpp(project), project, 'guitar/itemvol=-3') is not None
    assert check_edit(rpp(project), project, 'guitar/1175:1=-10') is None      # после точки
    assert check_edit(rpp(project), project, 'guitar/vol=-3') is None

def test_no_refuse_without_freeze(project):
    assert check_edit(rpp(project), project, 'guitar/hpflpf:3=-5') is None

def test_parallel_order_and_cleanup(project):
    r = subprocess.run([sys.executable, 'variants.py', project, 'base', 'guitar/vol=-3', 'mic/vol=-2', '--target', '-14'], capture_output=True, text=True)
    heads = [l for l in r.stdout.splitlines() if l.startswith('=== ')]
    assert heads == ['=== base', '=== guitar/vol=-3', '=== mic/vol=-2']
    assert 'порог лимитера под' in r.stdout
    assert not glob.glob(os.path.join(project, 'zz-variant*'))

def test_refused_variant_does_not_stop_others(project):
    write_freeze(project, 0, pink(-14))
    r = subprocess.run([sys.executable, 'variants.py', project, 'guitar/hpflpf:3=-5', 'base'], capture_output=True, text=True)
    assert 'до заморозки' in r.stdout and r.stdout.count('=== ') == 2 and 'мастер' in r.stdout
```

- [ ] **Step 2: Run tests - FAIL**

- [ ] **Step 3: Implement**
  - `check_edit`:
    - разбирает правку по тем же регэкспам, что `apply`;
    - находит трек и номер FX в `track_fx` (n-е совпадение подстроки, как в `apply`);
    - отказывает, если `freeze_status == 'ok'` и номер ≤ `point`, или если правка `itemvol` на таком треке.
  - Текст отказа: `<правка>: до заморозки (<after>), проверять render.sh --set`.
  - Отказавший вариант печатает отказ и не запускается.
  - Пул `concurrent.futures.ThreadPoolExecutor(max_workers=min(len(variants), max(1, os.cpu_count() - 2)))` с `subprocess.run`. Копия `zz-variant-<n>.rpp` удаляется в `finally`.
  - `--target` передаётся в каждый `analyze.py`.

- [ ] **Step 4: Run tests - PASS**

- [ ] **Step 5: Commit** `git commit -m "reaper-song: variants - отказ до заморозки, параллельно, --target"`

---

### Task 5: bridge/temp.lua - временные правки одной реализацией

**Files:**
- Create: `bridge/temp.lua`, `bridge/renderstate.lua`, `renderstate.sh`
- Modify: `bridge/render.lua` (оставить только рендер, правки - через temp.lua), `render.sh` (подключать `temp.lua` перед `render.lua`)

**Interfaces:**
- Produces (глобальные функции в сцепленном скрипте мост-вызова):
  - `temp_push(fn)`, `temp_restore()` - откат в обратном порядке;
  - `temp_trackinfo(tr, key, v)`, `temp_fx_enabled(tr, idx, on)`;
  - `temp_apply(A)` - все прежние правки render.lua: `addfx`, `solo`, `mute`, `nomaster`, `bypass`, `set`, `vol`, `itemvol`; печать прежняя;
  - `temp_render_settings()` - запоминает и ставит на откат `RENDER_SETTINGS`, `RENDER_BOUNDSFLAG` (`GetSetProjectInfo`), `RENDER_FORMAT`, `RENDER_FILE`, `RENDER_PATTERN` (`GetSetProjectInfo_String`) и выделение всех треков;
  - `temp_finish(dirty0)` - `temp_restore()`, затем пересохранить, если `dirty0 == 0` и проект стал `dirty`; печать `dirty`.
- `bridge/renderstate.lua` печатает по строке на каждое из: `dirty`, 5 настроек рендера, выделение, `D_VOL`/`D_PAN` треков, включённость каждого FX.
- `renderstate.sh [--proj ЧАСТЬ_ИМЕНИ]` - сцепляет `select.lua` (при `--proj`) и `renderstate.lua`, вызывает мост, печатает ответ.

- [ ] **Step 1: Снять состояние «до»:** `bash renderstate.sh --proj "каннибализм.rpp" > <скретчпад>/state0.txt`.
- [ ] **Step 2: Implement** `temp.lua` и переписать `render.lua` на него без изменения поведения.
- [ ] **Step 3: Verify** `bash render.sh --proj "каннибализм.rpp" --vol guitar=-3 chk_temp <скретчпад>/render`
  - Ожидается: печать `vol guitar -3`, файл −11.4 ± 0.1 LUFS (как рендер «до» 20.11), `dirty 0`.
  - Затем `renderstate.sh --proj "каннибализм.rpp"` побайтно совпадает со `state0.txt` (`cmp`).
- [ ] **Step 4: Commit** `git commit -m "reaper-song: temp.lua - временные правки рендера одной реализацией"`

---

### Task 6: stems.lua + freeze.sh - заморозка за один рендер

**Files:**
- Create: `bridge/stems.lua`, `freeze.sh`
- Modify: `SKILL.md` (таблица скриптов: `freeze.sh`)

**Interfaces:**
- Consumes:
  - `temp.lua` (Task 5);
  - CLI `freezelib.py plan` и `save` (Task 1);
  - `select.lua`.
- Produces:
  - `stems.lua` ждёт таблицу `A`:
    - `A.mode = 'freeze' | 'before'`;
    - `A.dir` - папка на nb;
    - `A.tracks = {{index=0, point=3}, ...}` (с 0; для `before` - пусто, берутся все немые);
    - `A.name` - для `before`.
  - Перед рендером: `error`, если `IsProjectDirty(0) == 1`.
  - Печатает `STEM\t<index>\t<путь на nb>` на каждый стем и для `before` ещё `MASTER\t<путь>`.
  - `freeze.sh <папка> [--proj ЧАСТЬ_ИМЕНИ] [--force] [--lua-only]`:
    - `--lua-only` печатает собранный lua-скрипт и выходит, ничего не запуская: для проверки отказов;
    - план;
    - треки, у которых `cached` и нет `--force`, пропускаются; печать `заморозка актуальна: guitar, drums`;
    - рендер, scp в `<папка>/freeze/NN.wav`, `freezelib.py save`, удаление файлов на nb;
    - печать `заморожено: guitar после Blue Cat's Free Amp, 3:40, NN с`.

- [ ] **Step 1: Implement `stems.lua`** (режим `freeze`). На выбранных треках:
  - выключить активные FX с индексом > `point`;
  - `D_VOL` 1, `D_PAN` 0;
  - FX мастера выключить;
  - выделить только эти треки;
  - `RENDER_SETTINGS` 2 (стемы выделенных треков);
  - `RENDER_BOUNDSFLAG` 1 (весь проект);
  - `RENDER_FORMAT` - WAV 32 bit float;
  - `RENDER_FILE` = `A.dir`, `RENDER_PATTERN` = `$tracknumber`.

  Затем 40101 и 42230. Файлы найти через `EnumerateFiles(A.dir)`. Всё - через `temp_*`, откат в `pcall`, как в render.lua. Строку `RENDER_FORMAT` для WAV 32f подобрать: кандидат base64 `ZXZhdyAAAQ==`. Принять, только если шаг 3 показывает `FLOAT`. Найденное значение записать комментарием в `stems.lua`.
- [ ] **Step 2: Implement `freeze.sh`** по образцу `render.sh`:
  - `env.sh`;
  - lua-файл из `A`, `select.lua`, `temp.lua`, `stems.lua`;
  - `bridge.sh -t 900`;
  - scp каждого `STEM` в `freeze/NN.wav`;
  - `freezelib.py save`;
  - `os.remove` файлов на nb через мост.
- [ ] **Step 3: Verify на «Домой»** `bash freeze.sh "<скретчпад>/reaper-song/Янка Дягилева - Домой" --proj "Домой.rpp"`
  - Ожидается: `заморожено: guitar …`, `drums …`.
  - `uv run analyze.py` на этой папке печатает `заморожено после Blue Cat's Free Amp` и `заморожено после MT-PowerDrumKit`.
  - `uv run rawcheck.py freeze/*.wav` показывает `FLOAT, 48000 Гц`.
  - `renderstate.sh --proj "Домой.rpp"` до и после совпадает (`cmp`).
- [ ] **Step 4: Verify кэш** - повторный `freeze.sh` той же строкой печатает `заморозка актуальна: guitar, drums` и не рендерит. Время меньше 10 с.
- [ ] **Step 5: Verify отказы** (Review Focus 3, 4):
  - `freeze.sh … --proj "нет такого.rpp"` - ошибка `нет открытой вкладки`, рендера нет.
  - Сбой посреди рендера. `stems.lua` при отсутствии трека делает `error("нет трека <index>")` уже после того, как поставлены временные правки первого трека.
    - Собрать скрипт: `freeze.sh … --proj "Домой.rpp" --force --lua-only > <скретчпад>/fail.lua`.
    - В этом файле в таблицу `A.tracks` дописать `{index=99, point=0}` через Edit.
    - Запустить `bash bridge/bridge.sh -t 900 <скретчпад>/fail.lua`.
    - Ожидается `ERR … нет трека 99`, затем `renderstate.sh --proj "Домой.rpp"` совпадает с замером до.
- [ ] **Step 6: Заморозить «Адаптацию»** тем же вызовом с `--proj "каннибализм.rpp"`.
- [ ] **Step 7: Commit** `git commit -m "reaper-song: freeze.sh - заморозка VST одним рендером стемов"`

---

### Task 7: рендер «до» со стемами и поправка - measure(), calib.py, render.sh --stems

**Files:**
- Modify: `measure.py` (функция + прежний CLI), `render.sh` (`--stems`, `--calib`), `bridge/stems.lua` (режим `before`)
- Create: `calib.py`
- Test: `tests/test_measure_calib.py`

**Interfaces:**
- Consumes: `analyze.py --json --no-calib` (Task 2-3), `freezelib.calib_key`, `save_json`; `stems.lua` (Task 6).
- Produces:
  - `measure.measure(path: str) -> dict` - `I: float | None`, `lra: float | None`, `tp: float | None`. CLI печатает как раньше.
  - `calib.py <папка> --master FILE --stem ИМЯ=FILE ...`:
    - прогон 1 `analyze.py --no-calib --json` → поправки треков = LUFS стема − LUFS модели;
    - запись `calib.json` с `master: null`;
    - прогон 2 `analyze.py --json` (поправки треков применены) → поправка мастера = LUFS мастера − `master_out`;
    - запись;
    - печать `поправки: guitar +0.3, mic +0.6, drums -0.2; мастер +0.1`.
  - `render.sh --stems [--calib ПАПКА] [--proj …] <имя> <локальная папка>`:
    - режим `before` в `stems.lua`: `RENDER_SETTINGS` 1 (мастер + стемы), все немые треки выделены, формат проекта, папка `C:\rec\2026\reaper-song\<имя>\`;
    - мастер переносится в `C:\rec\2026\<имя>.mp3` и остаётся;
    - стемы скачиваются в `<локальная папка>/<имя>_<трек>.mp3`, меряются и удаляются с nb;
    - при `--calib` - `calib.py` с этими файлами.

- [ ] **Step 1: Write the failing tests**

```python
def test_measure_pink(tmp_path):            # wav розового шума −20 dBFS RMS
    r = measure.measure(str(write_pink(tmp_path, -20)))
    assert -24 < r['I'] < -16 and r['tp'] is not None

def test_calib_roundtrip(project, tmp_path):
    stems = model_stems(project, tmp_path, gain={'mic': 0.5})   # модельные выходы треков, mic громче на 0.5 dB
    master = model_master(project, tmp_path)                    # analyze.py --no-calib --wav
    run_calib(project, master, stems)                           # calib.py <project> --master … --stem guitar=… --stem mic=…
    calib = load_json(project, 'calib.json')
    assert abs(calib['tracks']['mic'] - 0.5) < 0.1 and abs(calib['tracks']['guitar']) < 0.1
    assert calib['key'] == freezelib.calib_key(rpp(project))
    assert calib['master'] is not None
```

Помощник `model_stems` вызывает `analyze.py --no-calib --stems-dir DIR`, затем домножает wav нужного трека. Флаг `--stems-dir DIR` добавляется в `analyze.py` в этой задаче: модельные выходы треков после цепочки, фейдера и поправки пишутся в `DIR/<имя>.wav`. Мастер в тесте не сдвинут, поэтому поправка мастера должна только посчитаться, точное значение не проверяется: поправка mic поднимает модель.

- [ ] **Step 2: Run tests - FAIL**
- [ ] **Step 3: Implement** `measure()`, `calib.py`, `--stems-dir` в `analyze.py`, режим `before` в `stems.lua`, `--stems`/`--calib` в `render.sh`.
- [ ] **Step 4: Run tests - PASS**
- [ ] **Step 5: Verify вживую** `bash render.sh --stems --calib "<скретчпад>/reaper-song/Янка Дягилева - Домой" --proj "Домой.rpp" domoy_before2 <скретчпад>/render`
  - Мастер −13.1 ± 0.1 LUFS (итоговый рендер 20.11).
  - Напечатаны стемы guitar, mic, drums.
  - Поправки треков по модулю ≤ 1 LU.
  - `C:\rec\2026\domoy_before2.mp3` существует.
  - `renderstate.lua` совпадает с замером до вызова.
  - То же для «Адаптации» (`adaptaciya_before2`, мастер −12.9 ± 0.1).
- [ ] **Step 6: Commit** `git commit -m "reaper-song: рендер «до» со стемами за проход и calib.py"`

---

### Task 8: приёмка по рендерам 20.11, скилл, журнал

**Files:**
- Modify: `SKILL.md` (процедура шаги 2, 4, 5, 8; строка «Перегруз и барабаны»; таблица скриптов: `freezelib.py`, `calib.py`, `render.sh --stems`, `analyze.py --target`), `README.md` (таблица скриптов, если там есть)
- Create: `log/2026-11-21.md`

- [ ] **Step 1: Прогноз чужих состояний** (спека, «Проверка» п. 2). На папках, где уже есть `freeze/` и `calib.json`, вызвать:

```
python3 variants.py "<…>/Адаптация - Любовь и каннибализм" "guitar/vol=-3"
python3 variants.py "<…>/Янка Дягилева - Домой" "drums/vol=3.2 master/MGA_JSLimiterST:1=-6.4" \
  "guitar/vol=-3 drums/vol=6.45 master/MGA_JSLimiterST:1=-8 master/MGA_JSLimiterST:4=-1.4 drums/MGA_JSLimiterST:1=0 drums/MGA_JSLimiterST:4=0"
```

  Ожидается `рендер ≈` в пределах 0.3 LU от −11.4 / −13.8 / −11.7. Не попало - разобрать по стемам, порог не подгонять.
- [ ] **Step 2: Новая пара модель-рендер.**
  - `variants.py … "guitar/vol=-5"` на «Домой» против `render.sh --proj "Домой.rpp" --vol guitar=-5 chk_pair`.
  - Разница прогноза и замера ≤ 0.3 LU.
- [ ] **Step 3: --target.**
  - `variants.py "<…>/Янка Дягилева - Домой" base --target -13.0` → порог P.
  - `render.sh --proj "Домой.rpp" --set master:MGA_JSLimiterST:0=P chk_target` - −13.0 ± 0.3.
- [ ] **Step 4: Время.** Полный цикл на «Адаптации» по новой процедуре, с удалённой `freeze/`, от `fetch.sh` до проверочного рендера, по `date +%s` до и после. Цель - не больше 4 минут.
- [ ] **Step 5: SKILL.md.** Процедура для песни с VST: fetch → `freeze.sh` → `render.sh --stems --calib --keep` (рендер «до») → `analyze.py` → `variants.py --target` → один проверочный рендер `--keep` → `apply.sh` → `--final`. В шаге 2 «VST не моделируется» заменить на «до заморозки; после `freeze.sh` модель считает всё после VST».
- [ ] **Step 6: Журнал** `log/2026-11-21.md`:
  - что сделано и зачем;
  - цифры шагов 1-4: прогнозы против рендеров, время цикла до и после (20.11: около 10 минут на песню, около 15 из 20 - рендеры).
- [ ] **Step 7: Полный прогон тестов - PASS. Commit и push в main**: `git commit -m "reaper-song: процедура с заморозкой, приёмка, журнал" && git push`
