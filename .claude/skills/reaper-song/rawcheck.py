# /// script
# dependencies = ["numpy", "soundfile"]
# ///
"""Сырые дубли: формат, пик, сэмплы выше 0 dBFS, плоские вершины (настоящий срез) и L/R.
   uv run rawcheck.py Media/*.wav
Выше 0 dBFS во float - не срез. Срез - это плоские вершины: подряд одинаковые сэмплы у максимума."""
import sys
import numpy as np, soundfile as sf

for f in sys.argv[1:]:
    x, sr = sf.read(f, always_2d=True)
    print(f"{f.rsplit('/', 1)[-1]}: {sf.info(f).subtype}, {sr} Гц, {x.shape[1]} кан., {len(x) / sr:.1f} с")
    for c in range(x.shape[1]):
        a = np.abs(x[:, c]); m = a.max()
        flat = (np.abs(np.diff(x[:, c])) < 1e-6) & (a[:-1] > m * 0.98)
        edges = np.diff(np.concatenate([[0], flat.astype(np.int8), [0]]))
        runs = int(np.sum((np.nonzero(edges == -1)[0] - np.nonzero(edges == 1)[0]) >= 2))
        secs = len(np.unique(np.nonzero(a > 1)[0] // sr))
        print(f"  кан.{c + 1}: пик {20 * np.log10(m):+.1f} dBFS, выше 0: {int(np.sum(a > 1))} сэмплов в {secs} с,"
              f" плоских вершин {runs}{'  <- СРЕЗ' if runs else ''}")
    if x.shape[1] == 2:
        rms = lambda v: 10 * np.log10(np.mean(v ** 2) + 1e-20)
        print(f"  L-R {rms(x[:, 0]) - rms(x[:, 1]):+.2f} dB, корреляция {np.corrcoef(x[:, 0], x[:, 1])[0, 1]:.3f}")
