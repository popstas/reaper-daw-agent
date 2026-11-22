# /// script
# dependencies = ["numpy", "scipy", "soundfile"]
# ///
"""Проект REAPER для слепого по порядку A/B: версии одной песни сменяют друг друга каждые N тактов в той же точке песни.
   uv run abproj.py OUT.rpp [--bars 4] [--tempo 120] [--beats 4] [--xfade 0.02] 'ИМЯ=файл' 'ИМЯ=файл' ...
Первый файл - опорный: таймлайн проекта = его время. Остальные выравниваются по взаимной корреляции (моно 8 кГц),
сдвиг уходит в SOFFS. Отрезок k играет версия k mod N, на стыке кроссфейд XFADE с; маркер на каждом стыке - имя версии.
Каждая версия - свой трек (солировать/глушить можно). FILE пишется относительно папки OUT: файлы положить рядом.
Печатает сдвиг, корреляцию и разброс сдвига по трём окнам (25/50/75 %). Разные миксы коррелируют слабо (0.2-0.4) - это\nнорма; сомнительно, если окна разошлись больше чем на 1 мс."""
import argparse, io, os, subprocess, sys
import numpy as np, scipy.signal as ss, soundfile as sf

SR = 8000


def load(path):
    raw = subprocess.run(["ffmpeg", "-v", "quiet", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "wav", "-"],
                         capture_output=True).stdout
    x, _ = sf.read(io.BytesIO(raw))
    return x


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                         capture_output=True, text=True).stdout
    return float(out.strip())


def lag_at(x, ref, centre):
    """d, corr: x(t + d) ≈ ref(t) по окну 30 с вокруг centre (доля длины опорного), поиск ±10 с."""
    a = max(0, int(len(ref) * centre) - 15 * SR); b = min(len(ref), a + 30 * SR)
    seg = ref[a:b]
    lo = max(0, a - 10 * SR); hi = min(len(x), b + 10 * SR)
    win = x[lo:hi]
    c = ss.correlate(win, seg, mode="valid", method="fft")
    k = int(np.argmax(c))
    s = win[k:k + len(seg)]
    corr = float(np.dot(s, seg) / (np.linalg.norm(s) * np.linalg.norm(seg) + 1e-12))
    return (lo + k - a) / SR, corr


def lag(x, ref):
    """Медиана сдвига по трём окнам (25/50/75 %), минимальная корреляция и разброс сдвигов, с.
    Разные миксы одной песни коррелируют слабо (0.2-0.4), верить сдвигу можно, если окна сошлись до 1 мс."""
    r = [lag_at(x, ref, c) for c in (0.25, 0.5, 0.75)]
    ds = [d for d, _ in r]
    return float(np.median(ds)), min(c for _, c in r), max(ds) - min(ds)


def item(pos, length, soffs, fade_in, fade_out, name, fname):
    return [
        "    <ITEM",
        f"      POSITION {pos:.6f}",
        "      SNAPOFFS 0",
        f"      LENGTH {length:.6f}",
        "      LOOP 0",
        "      ALLTAKES 0",
        f"      FADEIN 1 {fade_in:.6f} 0 1 0 0 0",
        f"      FADEOUT 1 {fade_out:.6f} 0 1 0 0 0",
        "      MUTE 0 0",
        "      SEL 0",
        f'      NAME "{name}"',
        "      VOLPAN 1 0 1 -1",
        f"      SOFFS {soffs:.6f}",
        "      PLAYRATE 1 1 0 -1 0 0.0025",
        "      CHANMODE 0",
        f"      <SOURCE {'MP3' if fname.lower().endswith('.mp3') else 'WAVE'}",
        f'        FILE "{fname}"',
        "      >",
        "    >",
    ]


def build(out, versions, bars=4, tempo=120.0, beats=4, xfade=0.02):
    """versions: [(имя, путь)]. Возвращает [(имя, сдвиг, корр, разброс)], число и длину отрезков, длину; пишет OUT (CRLF)."""
    seg = bars * beats * 60.0 / tempo
    ref = load(versions[0][1])
    shifts = [(versions[0][0], 0.0, 1.0, 0.0)]
    for name, path in versions[1:]:
        shifts.append((name, *lag(load(path), ref)))
    total = min(duration(p) - d for (_, p), (_, d, *_) in zip(versions, shifts))
    nseg = int(np.ceil(total / seg))
    h = xfade / 2
    lines = ['<REAPER_PROJECT 0.1 "7.0/x64" 0', "  TIMELOCKMODE 0", f"  TEMPO {tempo:g} {beats} 4",
             "  SAMPLERATE 48000 0 0", "  LOOP 0"]
    for k in range(nseg):
        lines.append(f'  MARKER {k + 1} {k * seg:.6f} "{versions[k % len(versions)][0]}" 0 0 1 R')
    odir = os.path.dirname(os.path.abspath(out))
    for i, ((name, path), (_, d, *_)) in enumerate(zip(versions, shifts)):
        lines += ["  <TRACK", f'    NAME "{name}"', "    VOLPAN 1 0 -1 -1 1", "    MUTESOLO 0 0 0", "    NCHAN 2"]
        for k in range(i, nseg, len(versions)):
            a = max(0.0, k * seg - h); b = min(total, (k + 1) * seg + h)
            fi = 0.0 if k == 0 else xfade
            fo = 0.0 if (k + 1) * seg >= total else xfade
            lines += item(a, b - a, a + d, fi, fo, name, os.path.relpath(os.path.abspath(path), odir))
        lines.append("  >")
    lines.append(">")
    with open(out, "wb") as f:
        f.write(("\r\n".join(lines) + "\r\n").encode("utf-8"))
    return shifts, nseg, seg, total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("versions", nargs="+", help="ИМЯ=файл")
    ap.add_argument("--bars", type=int, default=4)
    ap.add_argument("--tempo", type=float, default=120.0)
    ap.add_argument("--beats", type=int, default=4)
    ap.add_argument("--xfade", type=float, default=0.02)
    a = ap.parse_args()
    vs = []
    for v in a.versions:
        if "=" not in v: sys.exit(f"нужно ИМЯ=файл: {v}")
        n, p = v.split("=", 1); vs.append((n, p))
    if len(vs) < 2: sys.exit("нужно хотя бы две версии")
    shifts, nseg, seg, total = build(a.out, vs, a.bars, a.tempo, a.beats, a.xfade)
    for n, d, c, spread in shifts:
        warn = "  СОМНИТЕЛЬНО - окна разошлись, проверить на слух" if spread > 0.001 else ""
        print(f"{n}: сдвиг {d * 1000:+.1f} мс, корреляция {c:.2f}, разброс по окнам {spread * 1000:.1f} мс{warn}")
    print(f"отрезков {nseg} по {seg:g} с, длина {int(total // 60)}:{total % 60:04.1f}; {a.out}")


if __name__ == "__main__":
    main()
