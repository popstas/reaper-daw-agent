# /// script
# dependencies = ["numpy", "scipy", "soundfile", "pyloudnorm", "numba"]
# ///
"""Разметка врезки: неудачный кусок, пауза, повтор с запасом до неудачи - в том же дубле (трек guitar + mic).
   uv run splicefind.py <папка> [--rpp файл] [--gap 1.5] [--top 5]
1. Паузы: обе дорожки у пола шума (пол + 10 dB) дольше --gap с.
2. Сдвиг повтор - оригинал: голосом (гитара одинакова в любом куплете), окна по 3 с из повтора ищутся в оригинале,
   побеждает сдвиг, за который голосовало больше окон. Одна мелодия в разных строках даёт ложный сдвиг у одного окна.
3. Проверка: сходство по 2 с вдоль перекрытия; где голос перестаёт совпадать - неудача (рез ставить раньше).
4. Точки реза: начало атаки удара гитары (верхи выше 2 кГц, огибающая 1 мс; пик спектрального потока на 10-30 мс позже
   и плавает - не годится), тот же удар в повторе, атака 10+ dB в обеих версиях, голос молчит в обеих (mic не выше пролаза гитары + 8 dB),
   хвост гитары перед ударом близок по уровню. Лучшие - строкой для splice.sh.
Времена - таймлайн проекта. Пока поддержан один айтем на guitar и mic."""
import argparse, os, sys
import numpy as np, soundfile as sf
from scipy.signal import stft, butter, sosfiltfilt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze import parse_rpp, mmss


def mm(t):
    return f"{int(t // 60)}:{t % 60:06.3f}"


def latest_rpp(folder):
    rpps = [os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith('.rpp')]
    return max(rpps, key=os.path.getmtime)


def load(folder, tracks, name):
    t = next((t for t in tracks if t['name'] == name), None)
    if not t or len(t['items']) != 1:
        sys.exit(f"{name}: нужен ровно один айтем (сейчас {len(t['items']) if t else 'нет трека'})")
    it = t['items'][0]
    x, sr = sf.read(os.path.join(folder, it['file']), always_2d=True)
    return x.mean(1), sr, it['pos'] - it['soffs']   # таймлайн = время файла + base


def bands(x, sr):
    hop = 480
    fr, _, Z = stft(x, sr, nperseg=4096, noverlap=4096 - hop)
    P = np.abs(Z)
    edges = np.geomspace(80, 4000, 49)
    B = np.stack([P[(fr >= edges[i]) & (fr < edges[i + 1])].sum(0) for i in range(48)])
    L = np.log(B + 1e-6)
    return L - L.mean(0, keepdims=True), sr / hop


def sim(L, a, b, n):
    if a < 0 or b < 0 or a + n > L.shape[1] or b + n > L.shape[1]:
        return np.nan
    A, B = L[:, a:a + n], L[:, b:b + n]
    A = (A - A.mean()) / (A.std() + 1e-9); B = (B - B.mean()) / (B.std() + 1e-9)
    return float(np.mean(A * B))


def rms_db(x, sr, a, b):
    s = x[max(0, int(a * sr)):int(b * sr)]
    return 20 * np.log10(np.sqrt(np.mean(s ** 2)) + 1e-12)


def attacks(Ed, sr, a, b):
    """Начала атак: через 3 мс огибающая на 10+ dB выше медианы предыдущих 40 мс, сам сэмпл ещё нет."""
    out, i, end, step = [], int(a * sr), int(b * sr), int(0.0005 * sr)
    d3, d5, w40 = int(0.003 * sr), int(0.005 * sr), int(0.04 * sr)
    while i < end:
        pre = np.median(Ed[i - w40:i])
        if Ed[i + d3] - pre > 10 and Ed[i] - pre < 4:
            j = i
            while Ed[j] - pre < 3:
                j += 1
            out.append((j / sr, Ed[j + d5] - pre)); i = j + int(0.1 * sr)
        else:
            i += step
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('folder'); ap.add_argument('--rpp')
    ap.add_argument('--gap', type=float, default=1.5); ap.add_argument('--top', type=int, default=5)
    a = ap.parse_args()
    rpp = a.rpp or latest_rpp(a.folder)
    _, tracks = parse_rpp(open(rpp, encoding='utf-8', errors='replace').read())
    g, sr, base = load(a.folder, tracks, 'guitar')
    m, sr2, base2 = load(a.folder, tracks, 'mic')
    if sr != sr2 or abs(base - base2) > 1e-6:
        sys.exit("guitar и mic не с одного прохода (разные частота или начало)")
    n = min(len(g), len(m)); g, m = g[:n], m[:n]
    T = lambda f: f + base   # время файла -> таймлайн

    # 1. паузы
    h = int(0.05 * sr); k = n // h
    eg = 20 * np.log10(np.sqrt(np.mean(g[:k * h].reshape(k, h) ** 2, 1)) + 1e-12)
    em = 20 * np.log10(np.sqrt(np.mean(m[:k * h].reshape(k, h) ** 2, 1)) + 1e-12)
    fg, fm = np.percentile(eg, 2), np.percentile(em, 2)
    loud = np.where((eg > fg + 10) | (em > fm + 10))[0]
    if not len(loud):
        sys.exit("тишина во всём дубле")
    first, last = loud[0], loud[-1]
    q = (eg <= fg + 10) & (em <= fm + 10)
    gaps, i = [], first
    while i < last:
        if q[i]:
            j = i
            while j < last and q[j]: j += 1
            if (j - i) * 0.05 >= a.gap: gaps.append((i * 0.05, j * 0.05))
            i = j
        else:
            i += 1
    # голос молчит = mic на уровне пролаза гитары: нижние 5 % mic, пока гитара играет (пол самого ATR на 20 dB ниже)
    bleed = np.percentile(em[eg > fg + 25], 5)
    print(f"{os.path.basename(rpp)}\nпол: guitar {fg:.1f}, mic {fm:.1f} dBFS; mic без голоса под гитарой {bleed:.1f}")
    if not gaps:
        print(f"пауз дольше {a.gap} с внутри дубля нет - врезки не видно"); return
    Lg, fps = bands(g, sr); Lm, _ = bands(m, sr)
    gh = sosfiltfilt(butter(4, 2000, 'highpass', fs=sr, output='sos'), g)
    w = int(0.001 * sr)
    Ed = 20 * np.log10(np.sqrt(np.convolve(gh ** 2, np.ones(w) / w, 'same')) + 1e-9)

    for gs, ge in gaps:
        print(f"\n== пауза {mmss(T(gs))}-{mmss(T(ge))} ({ge - gs:.1f} с)")
        # 2. сдвиг голосованием окон голоса
        qn = int(3 * fps); votes = []
        for kq in range(12):
            q0 = ge + 0.5 + kq * 1.5
            qa = int(q0 * fps)
            if qa + qn > Lm.shape[1]: break
            lo, hi = int(max(0, gs - 180) * fps), int((gs - 3) * fps)
            if hi <= lo: break
            Q = Lm[:, qa:qa + qn]; Qn = (Q - Q.mean()) / Q.std()
            best = max(((float(np.mean(Qn * ((W := Lm[:, s:s + qn]) - W.mean()) / W.std())), s) for s in range(lo, hi, 2)))
            votes.append((q0 - best[1] / fps, best[0]))
        if not votes:
            print("повтор короче 3 с - нечего сравнивать"); continue
        cl = max(votes, key=lambda v: sum(c for o, c in votes if abs(o - v[0]) < 0.15))
        good = [(o, c) for o, c in votes if abs(o - cl[0]) < 0.15]
        off = float(np.median([o for o, _ in good]))
        print(f"сдвиг {off:.3f} с: {len(good)} из {len(votes)} окон голоса, сходство {np.mean([c for _, c in good]):.2f}")
        others = sorted({round(o, 1) for o, c in votes if abs(o - off) >= 0.15 and c > 0.8})
        if others: print("  ложные кандидаты (та же мелодия в другом месте):", ", ".join(f"{o:.1f}" for o in others))
        # 3. совпадение вдоль перекрытия
        o0 = ge - off; nw = int(2 * fps); rows = []
        for t in np.arange(max(0, o0), gs - 2, 1.0):
            rows.append((t, sim(Lg, int((t + off) * fps), int(t * fps), nw), sim(Lm, int((t + off) * fps), int(t * fps), nw)))
        ok_end = None
        for t, sg, sm in rows:
            if sm >= 0.8: ok_end = t + 2
        print(f"повтор начат с места оригинала {mmss(T(o0))}")
        print("  ориг   гитара голос")
        for t, sg, sm in rows:
            print(f"  {mmss(T(t)):>5}   {sg:.2f}   {sm:.2f}{'  <- голос не совпадает' if sm < 0.8 else ''}")
        if ok_end is None:
            print("голос нигде не совпал на 0.8 - разметка нужна человеку"); continue
        print(f"голос совпадает до {mmss(T(ok_end))}, неудача после; рез ставить раньше")
        # 4. кандидаты
        A_ = attacks(Ed, sr, o0 + 1.0, ok_end - 0.3)
        B_ = attacks(Ed, sr, o0 + off + 0.7, ok_end + off)
        cands = []
        for ta, sa in A_:
            mt = [(abs(tb - ta - off), tb, sb) for tb, sb in B_ if abs(tb - ta - off) < 0.06]
            if not mt: continue
            _, tb, sb = min(mt)
            mo, mp = rms_db(m, sr, ta - 0.05, ta), rms_db(m, sr, tb - 0.05, tb)
            dt = rms_db(g, sr, ta - 0.08, ta) - rms_db(g, sr, tb - 0.08, tb)
            if min(sa, sb) < 10 or max(mo, mp) > bleed + 8: continue
            score = min(sa, sb) - 2 * abs(dt) - 0.5 * (max(mo, mp) - bleed)
            cands.append((score, ta, tb, sa, sb, mo, mp, dt))
        if not cands:
            print("нет удара, где голос молчит в обеих версиях и атака сильная - разметка нужна человеку"); continue
        cands.sort(reverse=True)
        print("точки реза (атака оригинала -> та же в повторе):")
        print("  ориг        повтор      атака о/п dB  голос до удара о/п     хвост гитары о-п")
        for sc, ta, tb, sa, sb, mo, mp, dt in cands[:a.top]:
            print(f"  {mm(T(ta))}  {mm(T(tb))}   {sa:3.0f} / {sb:<3.0f}     {mo:6.1f} / {mp:<6.1f} dBFS   {dt:+.1f} dB")
        _, ta, tb = cands[0][:3]
        print(f"лучшая: bash splice.sh \"<часть имени>.rpp\" {T(ta):.3f} {T(tb):.3f}"
              f"  (вырезается {tb - ta:.2f} с, громкость повтора о-п у реза {rms_db(g, sr, ta - 3, ta) - rms_db(g, sr, tb - 3, tb):+.1f} dB гитара)")


if __name__ == '__main__':
    main()
