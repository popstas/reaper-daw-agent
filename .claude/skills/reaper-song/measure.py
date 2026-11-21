# /// script
# dependencies = ["numpy", "scipy", "soundfile"]
# ///
"""Замер файлов (mp3/wav): integrated LUFS, LRA, true peak и доля полос от суммы.
   uv run measure.py файл [файл ...]
Тишина (-70 LUFS) у рендера - медиа были офлайн (REAPER не в фокусе), а не ошибка цепочки."""
import io, re, subprocess, sys
import numpy as np, scipy.signal as ss, soundfile as sf

BANDS = [(40, 100), (100, 250), (250, 500), (500, 1000), (1000, 2000), (2000, 4000), (4000, 8000), (8000, 16000)]


def measure(path):
    """ffmpeg ebur128: I (LUFS), lra (LU), tp (dBTP); None - не удалось прочитать."""
    log = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af", "ebur128=peak=true", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    summ = log[log.rfind("Summary:"):]
    def g(k):
        m = re.search(k + r":\s+(-?[\d.]+|-inf)", summ)
        return None if not m else (-float("inf") if m[1] == "-inf" else float(m[1]))
    return dict(I=g("I"), lra=g("LRA"), tp=g("Peak"))


def fmt(v):
    return "?" if v is None else f"{v:.1f}"


def main():
    for f in sys.argv[1:]:
        r = measure(f)
        name = f.rsplit("/", 1)[-1]
        print(f"{name}: I {fmt(r['I'])} LUFS, LRA {fmt(r['lra'])} LU, true peak {fmt(r['tp'])} dBTP")
        if r["I"] is not None and r["I"] <= -60:
            print("  ТИШИНА: медиа офлайн? REAPER на nb не в фокусе - вернуть окно и повторить")
            continue
        raw = subprocess.run(["ffmpeg", "-v", "quiet", "-i", f, "-ac", "1", "-f", "wav", "-"], capture_output=True).stdout
        x, sr = sf.read(io.BytesIO(raw))
        fr, p = ss.welch(x, sr, nperseg=8192)
        tot = p.sum()
        print("  полосы:", " ".join(f"{a}-{b}:{10 * np.log10(p[(fr >= a) & (fr < b)].sum() / tot):+.0f}" for a, b in BANDS))


if __name__ == "__main__":
    main()
