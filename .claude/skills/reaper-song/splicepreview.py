# /// script
# dependencies = ["numpy", "scipy", "soundfile", "pyloudnorm", "numba"]
# ///
"""Превью врезки до правки: сырая сумма guitar + mic, --len с оригинала до атаки и столько же повтора с атаки.
   uv run splicepreview.py <папка> <атака оригинала> <атака повтора> -o out.wav [--rpp файл] [--len 12] [--xf 0.004] [--guard 0.001]
Точки - таймлайн проекта, как в splicefind.py и splice.sh. Стык как в splice.sh: оригинал гаснет линейным фейдом xf,
кончается за guard до атаки, повтор вступает с атаки. Голос моно (L+R)/2, без цепочек: слушать стык, не баланс.
Пока поддержан один айтем на guitar и mic."""
import argparse, os, sys
import numpy as np, soundfile as sf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze import parse_rpp
from splicefind import latest_rpp, load


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('folder'); ap.add_argument('ta', type=float); ap.add_argument('tb', type=float)
    ap.add_argument('-o', '--out', required=True); ap.add_argument('--rpp')
    ap.add_argument('--len', type=float, default=12); ap.add_argument('--xf', type=float, default=0.004)
    ap.add_argument('--guard', type=float, default=0.001)
    a = ap.parse_args()
    rpp = a.rpp or latest_rpp(a.folder)
    _, tracks = parse_rpp(open(rpp, encoding='utf-8', errors='replace').read())
    g, sr, base = load(a.folder, tracks, 'guitar')
    m, _, _ = load(a.folder, tracks, 'mic')
    n = min(len(g), len(m)); x = g[:n] + m[:n]
    fa, fb = a.ta - base, a.tb - base          # таймлайн -> время файла
    end_a = int((fa - a.guard) * sr); xf = int(a.xf * sr)
    A = x[max(0, int((fa - a.len) * sr)):end_a].copy()
    A[-xf:] *= np.linspace(1, 0, xf)
    A = np.concatenate([A, np.zeros(int(a.guard * sr))])
    B = x[int(fb * sr):min(n, int((fb + a.len) * sr))]
    y = np.concatenate([A, B])
    y *= 10 ** (-1 / 20) / max(1e-9, np.abs(y).max())   # пик -1 dBFS: громкость превью не сравнивать
    sf.write(a.out, y, sr, subtype='PCM_24')
    print(f"{a.out}: стык на {len(A) / sr:.2f} с, вырезается {fb - fa:.2f} с")


if __name__ == '__main__':
    main()
