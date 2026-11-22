# /// script
# dependencies = ["numpy", "scipy", "soundfile"]
# ///
"""Пространство микса: где реверберация. Сравнивать версии одной песни (чужой мастер, рендер «до», наш).
   uv run spacecheck.py [--win 10] файл [файл ...]
- S−M по полосам (dB): боковая составляющая относительно центра. Реверб, дабл-трекинг и панорама её поднимают;
  разница версий в полосе показывает, где добавлено пространство (кик/бас - 40-250, голос - 250-4k, тарелки - 4k+).
- корреляция L/R по полосам: реверб её снижает (1 - моно, 0 - несвязанные каналы).
- хвост ударов: медиана времени спада огибающей 2-8 кГц от пика удара на 20 dB (атаки барабанов и гитары);
  сухой микс - десятки мс, реверб на барабанах удлиняет до сотен.
- S−M по окнам WIN секунд - где по песне пространство меняется (куплет/припев, вход барабанов)."""
import argparse, io, subprocess
import numpy as np, scipy.signal as ss, soundfile as sf

BANDS = [(40, 100), (100, 250), (250, 500), (500, 1000), (1000, 2000), (2000, 4000), (4000, 8000), (8000, 16000)]


def load(path):
    raw = subprocess.run(["ffmpeg", "-v", "quiet", "-i", path, "-ac", "2", "-f", "wav", "-"], capture_output=True).stdout
    x, sr = sf.read(io.BytesIO(raw), always_2d=True)
    return x, sr


def bandpass(x, sr, lo, hi):
    sos = ss.butter(4, [lo, min(hi, sr / 2 * 0.95)], btype="band", fs=sr, output="sos")
    return ss.sosfiltfilt(sos, x, axis=0)


def db(v):
    return 10 * np.log10(max(v, 1e-20))


def hit_decay(x, sr):
    """Медиана времени спада на 20 dB после пиков огибающей 2-8 кГц (мс) и число ударов."""
    m = bandpass(x.mean(axis=1), sr, 2000, 8000)
    env = ss.sosfiltfilt(ss.butter(2, 60, fs=sr, output="sos"), np.abs(m))
    hop = sr // 1000
    e = 20 * np.log10(np.maximum(env[::hop], 0) + 1e-9)   # огибающая с шагом 1 мс (filtfilt даёт мелкие минусы)
    peaks, _ = ss.find_peaks(e, prominence=15, distance=120)
    out = []
    for p in peaks:
        seg = e[p:p + 600]
        below = np.nonzero(seg < e[p] - 20)[0]
        if len(below): out.append(below[0])
    return (float(np.median(out)) if out else float("nan")), len(peaks)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--win", type=float, default=10.0)
    ap.add_argument("files", nargs="+")
    a = ap.parse_args()
    names = [f.rsplit("/", 1)[-1].rsplit(".", 1)[0] for f in a.files]
    w0 = max(len(n) for n in names) + 2
    head = " ".join(f"{lo}-{hi}".rjust(10) for lo, hi in BANDS)
    rows_sm, rows_c, rows_t, rows_hit = [], [], [], []
    for f in a.files:
        x, sr = load(f)
        sm, cc = [], []
        for lo, hi in BANDS:
            b = bandpass(x, sr, lo, hi)
            mid = (b[:, 0] + b[:, 1]) / 2; side = (b[:, 0] - b[:, 1]) / 2
            sm.append(db(np.mean(side ** 2)) - db(np.mean(mid ** 2)))
            cc.append(float(np.corrcoef(b[:, 0], b[:, 1])[0, 1]))
        rows_sm.append(sm); rows_c.append(cc)
        mid = (x[:, 0] + x[:, 1]) / 2; side = (x[:, 0] - x[:, 1]) / 2
        n = int(a.win * sr)
        rows_t.append([db(np.mean(side[i:i + n] ** 2)) - db(np.mean(mid[i:i + n] ** 2)) if np.mean(mid[i:i + n] ** 2) > 1e-7 else None
                       for i in range(0, len(x) - sr, n)])
        rows_hit.append(hit_decay(x, sr))
    print("S−M по полосам, dB (выше - шире/больше реверба):")
    print(" " * w0 + head)
    for n, r in zip(names, rows_sm): print(f"{n:<{w0}}" + " ".join(f"{v:10.1f}" for v in r))
    print("\nкорреляция L/R по полосам (ниже - больше реверба/ширины):")
    print(" " * w0 + head)
    for n, r in zip(names, rows_c): print(f"{n:<{w0}}" + " ".join(f"{v:10.2f}" for v in r))
    print("\nхвост ударов 2-8 кГц, спад на 20 dB (медиана):")
    for n, (t, k) in zip(names, rows_hit): print(f"{n:<{w0}}{t:6.0f} мс  ({k} ударов)")
    m = max(len(r) for r in rows_t)
    print(f"\nS−M по окнам {a.win:g} с, dB:")
    print(" " * w0 + " ".join(f"{int(i * a.win // 60)}:{int(i * a.win % 60):02d}".rjust(5) for i in range(m)))
    for n, r in zip(names, rows_t): print(f"{n:<{w0}}" + " ".join("    ·" if v is None else f"{v:5.0f}" for v in r))


if __name__ == "__main__":
    main()
