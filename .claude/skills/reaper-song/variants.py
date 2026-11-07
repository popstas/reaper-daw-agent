"""Прогон вариантов правок через модель (analyze.py) на временной копии .rpp.
   python3 variants.py <папка> [--rpp файл] [--full] "ПРАВКИ" ["ПРАВКИ" ...]
ПРАВКИ - через пробел, вариант "base" - без правок:
   mic/1175:1=-14       трек/FX:токен=значение, токен с 1 (позиция в строке параметров JSFX)
   mic/1175#2:1=-14     второе совпадение FX на треке
   guitar/vol=-4        фейдер, dB
   mic/itemvol=-8       громкость всех айтемов трека, dB (до цепочки)
   master/MGA_JSLimiterST:1=-4.5
FX - подстрока строки <JS ...>/<VST ...>. Копия zz-variant.rpp удаляется сразу после прогона.
Без --full печатает только ключевые строки отчёта."""
import argparse, glob, os, re, subprocess, sys

DIR = os.path.dirname(os.path.abspath(__file__))
KEY = re.compile(r"^(#|## )|после цепочки|^1175|гейт|лимитер|баланс|мастер")


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
                    if lines[j].strip()[5:].strip('"') == name:
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


ap = argparse.ArgumentParser()
ap.add_argument("dir"); ap.add_argument("--rpp"); ap.add_argument("--full", action="store_true")
ap.add_argument("variants", nargs="+")
a = ap.parse_args()
d = os.path.abspath(a.dir)
src = a.rpp or max(glob.glob(os.path.join(d, "*.rpp")) + glob.glob(os.path.join(d, "*.RPP")), key=os.path.getmtime)
copy = os.path.join(d, "zz-variant.rpp")
for v in a.variants:
    with open(src, encoding="utf-8", newline="") as f:
        lines = f.readlines()
    if v != "base":
        for e in v.split():
            apply(lines, e)
    print(f"=== {v}", flush=True)
    try:
        with open(copy, "w", encoding="utf-8", newline="") as f:
            f.writelines(lines)
        r = subprocess.run(["uv", "run", "-q", os.path.join(DIR, "analyze.py"), "--rpp", copy, d],
                           capture_output=True, text=True)
    finally:
        os.remove(copy)
    out = r.stdout + r.stderr
    print(out if a.full else "\n".join(l for l in out.splitlines() if KEY.search(l)), flush=True)
