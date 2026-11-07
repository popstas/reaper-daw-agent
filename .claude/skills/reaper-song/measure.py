# /// script
# dependencies = ["numpy", "scipy", "soundfile"]
# ///
"""Замер файлов (mp3/wav): integrated LUFS, LRA, true peak и доля полос от суммы.
   uv run measure.py файл [файл ...]
Тишина (-70 LUFS) у рендера - медиа были офлайн (REAPER не в фокусе), а не ошибка цепочки."""
import io, re, subprocess, sys
import numpy as np, scipy.signal as ss, soundfile as sf

BANDS = [(40, 100), (100, 250), (250, 500), (500, 1000), (1000, 2000), (2000, 4000), (4000, 8000), (8000, 16000)]

for f in sys.argv[1:]:
    log = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", f, "-af", "ebur128=peak=true", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    summ = log[log.rfind("Summary:"):]
    g = lambda k: (re.search(k + r":\s+(-?[\d.]+|-inf)", summ) or [None, "?"])[1]
    I, lra, tp = g("I"), g("LRA"), g("Peak")
    name = f.rsplit("/", 1)[-1]
    print(f"{name}: I {I} LUFS, LRA {lra} LU, true peak {tp} dBTP")
    if I != "?" and float(I) <= -60:
        print("  ТИШИНА: медиа офлайн? REAPER на nb не в фокусе - вернуть окно и повторить")
        continue
    raw = subprocess.run(["ffmpeg", "-v", "quiet", "-i", f, "-ac", "1", "-f", "wav", "-"], capture_output=True).stdout
    x, sr = sf.read(io.BytesIO(raw))
    fr, p = ss.welch(x, sr, nperseg=8192)
    tot = p.sum()
    print("  полосы:", " ".join(f"{a}-{b}:{10 * np.log10(p[(fr >= a) & (fr < b)].sum() / tot):+.0f}" for a, b in BANDS))
