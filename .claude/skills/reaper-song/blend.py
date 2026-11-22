# /// script
# dependencies = ["numpy", "scipy", "soundfile", "pyloudnorm"]
# ///
"""Наложение двух мастеров одной песни (параллельный микс версий): основа + вторая версия тише на N dB.
   uv run blend.py ОСНОВА ВТОРАЯ OUT.mp3 [--db -6] [--target -13.0] [--tp -1.0]
Вторая выравнивается по основе: грубо по корреляции (abproj.lag, 8 кГц), потом до сэмпла на 48 кГц - иначе сумма
даст гребёнку. Сумма приводится к --target LUFS простым усилением; если true peak выходит выше --tp, громкость
снижается до --tp (лимитера нет - сумма не пережимается). Печатает сдвиг, корреляцию на 48 кГц, LUFS и true peak.
Корреляция двух разных миксов 0.2-0.4 - норма; гребёнку проверять на слух."""
import argparse, os, subprocess, sys, tempfile
import numpy as np, pyloudnorm as pyln, scipy.signal as ss, soundfile as sf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import abproj

SR = 48000


def load48(path):
    raw = subprocess.run(["ffmpeg", "-v", "quiet", "-i", path, "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.float32).reshape(-1, 2).astype(np.float64)


def refine(base, other, coarse):
    """Сдвиг в сэмплах 48 кГц (other[t + d] ≈ base[t]) около грубого coarse (с), окно 30 с из середины, поиск ±2 мс."""
    b = base.mean(axis=1); o = other.mean(axis=1)
    a = len(b) // 2 - 15 * SR; seg = b[a:a + 30 * SR]
    c0 = int(round(coarse * SR)); pad = 2 * SR // 1000
    lo = a + c0 - pad
    win = o[lo:lo + len(seg) + 2 * pad]
    c = ss.correlate(win, seg, mode="valid", method="fft")
    k = int(np.argmax(c))
    s = win[k:k + len(seg)]
    corr = float(np.dot(s, seg) / (np.linalg.norm(s) * np.linalg.norm(seg) + 1e-12))
    return lo + k - a, corr


def true_peak(x):
    return 20 * np.log10(np.max(np.abs(ss.resample_poly(x, 4, 1, axis=0))) + 1e-12)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("base"); ap.add_argument("other"); ap.add_argument("out")
    ap.add_argument("--db", type=float, default=-6.0, help="вторая версия относительно основы, dB")
    ap.add_argument("--target", type=float, default=-13.0)
    ap.add_argument("--tp", type=float, default=-1.0)
    a = ap.parse_args()
    coarse, _, spread = abproj.lag(abproj.load(a.other), abproj.load(a.base))
    if spread > 0.001: print(f"ВНИМАНИЕ: сдвиг по окнам разошёлся на {spread * 1000:.1f} мс")
    base = load48(a.base); other = load48(a.other)
    d, corr = refine(base, other, coarse)
    # other[t + d] ≈ base[t]: сдвинуть other на -d
    if d >= 0: other = other[d:]
    else: other = np.concatenate([np.zeros((-d, 2)), other])
    n = min(len(base), len(other))
    mix = base[:n] + other[:n] * 10 ** (a.db / 20)
    meter = pyln.Meter(SR)
    g = a.target - meter.integrated_loudness(mix)
    tp = true_peak(mix) + g
    if tp > a.tp: g -= tp - a.tp
    mix *= 10 ** (g / 20)
    I = meter.integrated_loudness(mix)
    with tempfile.TemporaryDirectory() as t:
        w = os.path.join(t, "mix.wav")
        sf.write(w, mix.astype(np.float32), SR, subtype="FLOAT")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", w, "-c:a", "libmp3lame", "-b:a", "320k", a.out], check=True)
    print(f"сдвиг {d} сэмплов ({d / SR * 1000:+.2f} мс), корреляция {corr:.2f}; вторая {a.db:+g} dB; "
          f"усиление суммы {g:+.1f} dB; {I:.1f} LUFS, true peak {true_peak(mix):.1f} dBTP (до mp3); {a.out}")


if __name__ == "__main__":
    main()
