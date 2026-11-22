# /// script
# dependencies = ["numpy", "scipy", "soundfile", "pyloudnorm"]
# ///
"""Баланс стемов по времени - для проектов, которые модель не считает (папки, посылы, amp-model, pitchdown).
   uv run stembal.py [--win 10] [--ref ФАЙЛ] файл [файл ...]
Печатает по окнам WIN секунд громкость каждого файла (LUFS по окну, K-взвешенно; '·' - окно тише -50) и, если задан
--ref, разницу «файл минус ref» по окнам, где оба звучат. В конце - integrated и разница integrated с ref.
Файлы - рендеры одного проекта (стемы render.sh --stems), позиции совпадают. mp3/wav."""
import argparse, io, subprocess
import numpy as np, pyloudnorm as pyln, soundfile as sf

SILENT = -50.0


def load(path):
    raw = subprocess.run(["ffmpeg", "-v", "quiet", "-i", path, "-f", "wav", "-"], capture_output=True).stdout
    x, sr = sf.read(io.BytesIO(raw), always_2d=True)
    return x, sr


def windows(x, sr, win):
    meter = pyln.Meter(sr, block_size=0.4)
    n = int(win * sr)
    out = []
    for i in range(0, len(x), n):
        seg = x[i:i + n]
        if len(seg) < sr: break
        with np.errstate(divide="ignore"):
            v = meter.integrated_loudness(seg)
        out.append(v if np.isfinite(v) else -99.0)
    return out, pyln.Meter(sr).integrated_loudness(x)


def mmss(t):
    return f"{int(t // 60)}:{int(t % 60):02d}"


def short(p):
    return p.rsplit("/", 1)[-1].rsplit(".", 1)[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--win", type=float, default=10.0)
    ap.add_argument("--ref")
    ap.add_argument("files", nargs="+")
    a = ap.parse_args()
    paths = ([a.ref] if a.ref else []) + [f for f in a.files if f != a.ref]
    data = {}
    for p in paths:
        x, sr = load(p)
        data[p] = windows(x, sr, a.win)
    n = max(len(w) for w, _ in data.values())
    names = [short(p) for p in paths]
    w0 = max(len(s) for s in names) + 2
    print(" " * w0 + " ".join(f"{mmss(i * a.win):>5}" for i in range(n)) + "      I")
    for p, s in zip(paths, names):
        w, I = data[p]
        print(f"{s:<{w0}}" + " ".join(f"{v:5.0f}" if v > SILENT else "    ·" for v in w) + f"  {I:5.1f}")
    if a.ref:
        wr, Ir = data[a.ref]
        print(f"\nминус {short(a.ref)} (только окна, где оба громче {SILENT:.0f}):")
        for p, s in zip(paths[1:], names[1:]):
            w, I = data[p]
            cells = []
            for i in range(n):
                v = w[i] if i < len(w) else -99
                r = wr[i] if i < len(wr) else -99
                cells.append(f"{v - r:+5.0f}" if v > SILENT and r > SILENT else "    ·")
            print(f"{s:<{w0}}" + " ".join(cells) + f"  {I - Ir:+5.1f}")


if __name__ == "__main__":
    main()
