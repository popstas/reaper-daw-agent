# /// script
# dependencies = ["numpy", "scipy", "soundfile"]
# ///
"""Тракт записи по сырой паре дублей (гитара + микрофон одного прохода): то, что зависит от драйвера/усиления, а не от исполнения.
   uv run takecheck.py <guitar.wav> <mic.wav> [<guitar.wav> <mic.wav> ...]
Печатает по каждому файлу:
  пол       - самая тихая 1 с (RMS), dBFS: шум тракта; одинаковый пол у двух дублей = то же усиление
  потолок   - максимум |x| и число плоских вершин у максимума (срез; во float без среза пики бывают выше 0)
  дыры      - подряд нули >= 1 мс внутри звука (дропаут буфера)
  верх      - уровень 16-20 и 20-23.5 кГц относительно 1-4 кГц, dB (ресемплинг режет верх)
По паре: задержка mic относительно гитары по 20 с (взаимная корреляция 200-3000 Гц, мс) и дрейф за дубль.
Задержка включает акустику (гитара -> микрофон, ~1-3 мс); важен разброс и дрейф, а не ноль."""
import sys
import numpy as np, scipy.signal as ss, soundfile as sf


def db(v):
    return 20 * np.log10(max(float(v), 1e-12))


def info(path):
    x, sr = sf.read(path, always_2d=True, dtype="float32")
    m = x[:, 0].astype(np.float64)
    name = path.rsplit("/", 1)[-1]
    w = sr  # 1 с
    n = len(m) // w
    rms = np.sqrt(np.mean(m[: n * w].reshape(n, w) ** 2, axis=1))
    floor = db(rms.min()); at = int(np.argmin(rms))
    a = np.abs(m); peak = a.max()
    flat = (np.abs(np.diff(m)) < 1e-6) & (a[:-1] > peak * 0.98)
    e = np.diff(np.concatenate([[0], flat.astype(np.int8), [0]]))
    tops = int(np.sum((np.nonzero(e == -1)[0] - np.nonzero(e == 1)[0]) >= 2))
    # звук: окна 50 мс громче пола на 10 dB
    act = np.nonzero(rms > rms.min() * 3.16)[0]
    s0, s1 = (act[0] * w, (act[-1] + 1) * w) if len(act) else (0, len(m))
    z = (m[s0:s1] == 0).astype(np.int8)
    ze = np.diff(np.concatenate([[0], z, [0]]))
    runs = np.nonzero(ze == -1)[0] - np.nonzero(ze == 1)[0]
    holes = int(np.sum(runs >= sr // 1000))
    f, p = ss.welch(m[s0:s1], sr, nperseg=8192)
    band = lambda lo, hi: 10 * np.log10(p[(f >= lo) & (f < hi)].mean() + 1e-30)
    ref = band(1000, 4000)
    print(f"{name}: {x.shape[1]} кан., {len(m) / sr:.1f} с")
    print(f"  пол {floor:.1f} dBFS (на {at // 60}:{at % 60:02d}), потолок {db(peak):+.2f} dBFS, плоских вершин {tops}"
          f"{'  <- СРЕЗ' if tops else ''}")
    print(f"  дыры {holes}, верх 16-20 кГц {band(16000, 20000) - ref:+.0f} dB, 20-23.5 кГц {band(20000, 23500) - ref:+.0f} dB")
    return m, sr


def sync(g, mic, sr):
    b, a = ss.butter(4, [200, 3000], btype="band", fs=sr)
    g = ss.filtfilt(b, a, g); mic = ss.filtfilt(b, a, mic)
    L = min(len(g), len(mic)); W = 20 * sr; maxlag = int(0.05 * sr)
    out = []
    for s in range(0, L - W // 2, W):
        gs, ms = g[s:s + W], mic[s:s + W]
        if np.std(gs) < 1e-5 or np.std(ms) < 1e-5:
            continue
        c = ss.correlate(ms, gs, "full", method="fft")
        mid = len(gs) - 1
        seg = c[mid - maxlag: mid + maxlag + 1]
        k = int(np.argmax(np.abs(seg)))
        r = abs(seg[k]) / (np.linalg.norm(gs) * np.linalg.norm(ms) + 1e-12)
        # дробная часть - параболой
        if 0 < k < len(seg) - 1:
            y0, y1, y2 = np.abs(seg[k - 1:k + 2]); k = k + 0.5 * (y0 - y2) / (y0 - 2 * y1 + y2 + 1e-30)
        out.append((s // sr, (k - maxlag) / sr * 1000, r))
    good = [o for o in out if o[2] > 0.015]
    print("  задержка mic-гитара по 20 с (мс, корр.): " + "  ".join(f"{t // 60}:{t % 60:02d} {d:+.2f} ({r:.2f})" for t, d, r in out))
    # корреляция слабая (голос перекрывает пролаз), поэтому берём медиану и окна, согласные с ней в пределах 0.5 мс
    if good:
        med = float(np.median([d for _, d, _ in good]))
        agree = [o for o in good if abs(o[1] - med) <= 0.5]
        if len(agree) >= max(3, len(out) // 2):
            ds = [d for _, d, _ in agree]
            print(f"  медиана {med:+.2f} мс, согласны {len(agree)} из {len(out)} окон, разброс {max(ds) - min(ds):.2f} мс,"
                  f" дрейф {agree[-1][1] - agree[0][1]:+.2f} мс за {(agree[-1][0] - agree[0][0]) // 60}:{(agree[-1][0] - agree[0][0]) % 60:02d}")
            return
    print("  окна не сходятся на одной задержке - гитары в микрофоне мало (или клип), оценки нет")


args = sys.argv[1:]
if len(args) < 2 or len(args) % 2:
    sys.exit(__doc__)
for i in range(0, len(args), 2):
    print(f"=== пара {i // 2 + 1}")
    g, sr = info(args[i]); m, sr2 = info(args[i + 1])
    sync(g, m, sr)
