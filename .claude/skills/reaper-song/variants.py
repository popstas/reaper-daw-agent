"""Прогон вариантов правок через модель (analyze.py) на временной копии .rpp.
   python3 variants.py <папка> [--rpp файл] [--full] "ПРАВКИ" ["ПРАВКИ" ...]
ПРАВКИ - через пробел, вариант "base" - без правок:
   mic/1175:1=-14       трек/FX:токен=значение, токен с 1 (позиция в строке параметров JSFX)
   mic/1175#2:1=-14     второе совпадение FX на треке
   guitar/vol=-4        фейдер, dB
   mic/itemvol=-8       громкость всех айтемов трека, dB (до цепочки)
   mic/mute=1           заглушить трек (0 - включить)
Пробел в имени трека писать как _: "mic_with_guitar/mute=0".
   master/MGA_JSLimiterST:1=-4.5
FX - подстрока строки <JS ...>/<VST ...>. Копии zz-variant-<n>.rpp удаляются сразу после прогона.
Варианты идут параллельно (до числа ядер - 2), вывод - в порядке аргументов.
--target LUFS - в каждом варианте подобрать порог MGA_JSLimiterST мастера под прогноз рендера.
Правка FX до точки актуальной заморозки (или itemvol такого трека) - отказ: модель её не видит, проверять рендером.
Без --full печатает только ключевые строки отчёта."""
import argparse, concurrent.futures, glob, os, re, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import freezelib

DIR = os.path.dirname(os.path.abspath(__file__))
KEY = re.compile(r"^(#|## )|после цепочки|^1175|гейт|лимитер|баланс|мастер|заморожено|устарела|нет заморозки|поправк|рендер ≈|порог лимитера под|недостижима")


def blocks(lines):
    """(start, end, depth) для каждого блока <...>."""
    out, stack = [], []
    for i, l in enumerate(lines):
        s = l.strip()
        if s.startswith("<"):
            stack.append(i)
        elif s == ">" and stack:
            st = stack.pop()
            out.append((st, i, len(stack)))
    return out


def track_range(lines, bl, name):
    if name == "master":
        for st, en, _ in bl:
            if lines[st].strip().startswith("<MASTERFXLIST"):
                return st, en
        sys.exit("нет MASTERFXLIST")
    for st, en, _ in bl:
        if lines[st].strip().startswith("<TRACK"):
            for j in range(st + 1, en):
                if lines[j].strip().startswith("NAME "):
                    if lines[j].strip()[5:].strip('"') in (name, name.replace("_", " ")):
                        return st, en
                    break
    sys.exit(f"нет трека {name}")


def set_tokens(line, idx, val):
    body = line.rstrip("\r\n"); eol = line[len(body):]
    ind = body[: len(body) - len(body.lstrip())]
    t = body.split()
    t[idx - 1] = val
    return ind + " ".join(t) + eol


def apply(lines, edit):
    bl = blocks(lines)
    m = re.fullmatch(r"([^/]+)/itemvol=(-?[\d.]+)", edit)
    if m:
        st, en = track_range(lines, bl, m[1])
        n = 0
        for ist, ien, _ in bl:
            if st < ist < en and lines[ist].strip().startswith("<ITEM"):
                for j in range(ist, ien):
                    if lines[j].strip().startswith("VOLPAN "):
                        lines[j] = set_tokens(lines[j], 2, f"{10 ** (float(m[2]) / 20):.10g}"); n += 1
                        break
        if not n:
            sys.exit(f"нет айтемов у {m[1]}")
        return
    m = re.fullmatch(r"([^/]+)/mute=([01])", edit)
    if m:
        st, en = track_range(lines, bl, m[1])
        for j in range(st, en):
            if lines[j].strip().startswith("MUTESOLO "):
                lines[j] = set_tokens(lines[j], 2, m[2])
                return
        sys.exit(f"нет MUTESOLO у {m[1]}")
    m = re.fullmatch(r"([^/]+)/vol=(-?[\d.]+)", edit)
    if m:
        st, en = track_range(lines, bl, m[1])
        if m[1] == "master":
            sys.exit("фейдер мастера не поддержан")
        for j in range(st, en):
            if lines[j].strip().startswith("VOLPAN "):
                lines[j] = set_tokens(lines[j], 2, f"{10 ** (float(m[2]) / 20):.10g}")
                return
        sys.exit(f"нет VOLPAN у {m[1]}")
    m = re.fullmatch(r"([^/]+)/(.+?)(?:#(\d+))?:(\d+)=(\S+)", edit)
    if not m:
        sys.exit(f"не разобрал правку: {edit}")
    st, en = track_range(lines, bl, m[1])
    n = int(m[3] or 1)
    for j in range(st, en):
        s = lines[j].strip()
        if (s.startswith("<JS ") or s.startswith("<VST ")) and m[2] in s:
            n -= 1
            if n == 0:
                if s.startswith("<VST "):
                    sys.exit("параметры VST в .rpp закодированы, модель их не считает")
                lines[j + 1] = set_tokens(lines[j + 1], int(m[4]), m[5])
                return
    sys.exit(f"нет FX {m[2]} на {m[1]}")


def check_edit(rpp_text, folder, edit):
    """Текст отказа, если правка стоит до точки актуальной заморозки (модель её не увидит), иначе None."""
    m = re.fullmatch(r"([^/]+)/itemvol=(-?[\d.]+)", edit)
    if m:
        tname, sub, n = m[1], None, 0
    else:
        m = re.fullmatch(r"([^/]+)/(.+?)(?:#(\d+))?:(\d+)=(\S+)", edit)
        if not m or "/vol=" in edit or "/mute=" in edit:
            return None
        tname, sub, n = m[1], m[2], int(m[3] or 1)
    t = next((t for t in freezelib.split_tracks(rpp_text) if t["name"] in (tname, tname.replace("_", " "))), None)
    if t is None:
        return None
    e = next((e for e in freezelib.plan(rpp_text) if e["index"] == t["index"]), None)
    if e is None or freezelib.freeze_status(folder, e) != "ok":
        return None
    if sub is None:
        return f"{edit}: до заморозки ({e['after']}), проверять render.sh --itemvol"
    for i, fx in enumerate(freezelib.track_fx(t["text"])):
        head = fx["text"].split("\n")[1].strip()
        if (head.startswith("<JS ") or head.startswith("<VST ")) and sub in head:
            n -= 1
            if n == 0:
                return f"{edit}: до заморозки ({e['after']}), проверять render.sh --set" if i <= e["point"] else None
    return None


def run_variant(n, v, src, d, target, full):
    """Вывод одного варианта: отказ, ошибка правки или (ключевые) строки analyze.py по копии zz-variant-<n>.rpp."""
    with open(src, encoding="utf-8", newline="") as f:
        lines = f.readlines()
    if v != "base":
        text = "".join(lines)
        refused = [r for r in (check_edit(text, d, e) for e in v.split()) if r]
        if refused:
            return "\n".join(refused)
        try:
            for e in v.split():
                apply(lines, e)
        except SystemExit as ex:
            return f"ошибка: {ex}"
    copy = os.path.join(d, f"zz-variant-{n}.rpp")
    try:
        with open(copy, "w", encoding="utf-8", newline="") as f:
            f.writelines(lines)
        cmd = ["uv", "run", "-q", os.path.join(DIR, "analyze.py"), "--rpp", copy, d]
        if target is not None:
            cmd += ["--target", str(target)]
        r = subprocess.run(cmd, capture_output=True, text=True)
    finally:
        if os.path.exists(copy):
            os.remove(copy)
    out = r.stdout + r.stderr
    return out if full else "\n".join(l for l in out.splitlines() if KEY.search(l))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir"); ap.add_argument("--rpp"); ap.add_argument("--full", action="store_true")
    ap.add_argument("--target", type=float, help="подобрать порог лимитера мастера под прогноз рендера, LUFS")
    ap.add_argument("variants", nargs="+")
    a = ap.parse_args()
    d = os.path.abspath(a.dir)
    src = freezelib.find_rpp(d, a.rpp)
    workers = min(len(a.variants), max(1, (os.cpu_count() or 1) - 2))
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futs = [pool.submit(run_variant, n, v, src, d, a.target, a.full) for n, v in enumerate(a.variants, 1)]
        for v, f in zip(a.variants, futs):
            print(f"=== {v}", flush=True)
            print(f.result(), flush=True)


if __name__ == "__main__":
    main()
