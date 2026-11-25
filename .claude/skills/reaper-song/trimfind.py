# /// script
# dependencies = ["numpy", "scipy", "soundfile", "pyloudnorm", "numba"]
# ///
"""Обрезка начала и конца дубля (трек guitar + mic одного прохода): что срезано в проекте и где резать по правилам.
   uv run trimfind.py <папка> [--rpp файл] [--profile] [--win 0.25] [--ctx 4] [--at 2-15 205-212]
Без флагов: срез каждого трека, предложение (раздел «Обрезка начала и конца дубля» в SKILL.md) и разница с проектом.
--profile - ещё профиль по окнам --win с вокруг резов проекта; --at - профиль участков файла «с-по» в секундах.
Времена - время файла дубля (таймлайн проекта = время файла + POSITION - SOFFS первого айтема).
Голос: mic выше «гитара + связь» на 10+ dB (связь - сырой mic без голоса под гитарой, как в analyze.py)."""
import argparse, os, sys
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfiltfilt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze import parse_rpp
import freezelib

db = lambda v: 20 * np.log10(np.maximum(v, 1e-12))
GRID = 0.5        # резы начала пользователь ставит по сетке 0.5 с
TAKE_MIN = 20     # участок игры короче - фальстарт, если после него пауза
MERGE = 0.6       # разрывы игры короче - внутри одного участка


def ms(t):
    s = '-' if t < 0 else ''; t = abs(t)
    return f"{s}{int(t // 60)}:{t % 60:04.1f}"


def env(x, sr, w):
    h = int(w * sr); k = len(x) // h
    return db(np.sqrt(np.mean(x[:k * h].reshape(k, h) ** 2, 1)))


def spans(tracks):
    """{файл: [трек, первый айтем, последний айтем, айтемов]} по времени файла."""
    out = {}
    for t in tracks:
        for it in t['items']:
            if it['mute']: continue
            o = out.setdefault(it['file'], [t['name'], it, it, 0])
            if it['soffs'] < o[1]['soffs']: o[1] = it
            if it['soffs'] + it['len'] > o[2]['soffs'] + o[2]['len']: o[2] = it
            o[3] += 1
    return out


def runs(mask, w, min_len=0.0, merge=0.0):
    """[(начало, конец)] в секундах участков mask; разрывы короче merge склеиваются."""
    out, i, n = [], 0, len(mask)
    while i < n:
        if mask[i]:
            j = i
            while j < n and mask[j]: j += 1
            if out and i * w - out[-1][1] < merge: out[-1] = (out[-1][0], j * w)
            else: out.append((i * w, j * w))
            i = j
        else:
            i += 1
    return [r for r in out if r[1] - r[0] >= min_len]


class Take:
    """Огибающие пары дублей одного прохода: гитара, её верха, mic, его верха; пол, связь mic-гитара."""

    def __init__(self, gx, mx, sr):
        n = min(len(gx), len(mx)); self.g, self.m, self.sr = gx[:n], mx[:n], sr
        self.dur = n / sr
        hp = butter(4, 2000, 'highpass', fs=sr, output='sos')
        self.gh, self.mh = sosfiltfilt(hp, self.g), sosfiltfilt(hp, self.m)
        e = lambda x: env(x, sr, 0.05)
        eg, em = e(self.g), e(self.m)
        k = int(0.8 / 0.05)   # до первого удара и после стопа в файле всегда тишина; щелчки старта медиана не видит
        self.gfloor = min(np.median(eg[:k]), np.median(eg[-k:]))
        self.mfloor = min(np.median(em[:k]), np.median(em[-k:]))
        ga = eg > np.percentile(eg, 90) - 30
        self.couple = np.percentile((em - eg)[ga], 10)
        ehh, emh = e(self.gh), e(self.mh)
        self.couple_h = np.percentile((emh - ehh)[ga], 10)

    def envs(self, w):
        e = lambda x: env(x, self.sr, w)
        return e(self.g), e(self.gh), e(self.m), e(self.mh)

    def voice(self, w=0.1):
        eg, _, em, _ = self.envs(w)
        return (em > eg + self.couple + 10) & (em > self.mfloor + 12)


def onset(take, a, b):
    """Начало первой атаки гитары в [a, b): первое окно 10 мс выше пола на 15 dB, назад - пока выше пола на 6."""
    w = 0.01; eg = env(take.g, take.sr, w)
    i0, i1 = int(a / w), min(len(eg), int(b / w))
    hit = next((i for i in range(i0, i1) if eg[i] > take.gfloor + 15), None)
    if hit is None: return None
    while hit > i0 and eg[hit - 1] > take.gfloor + 6: hit -= 1
    return hit * w


def propose(take):
    """Предложение резов по правилам SKILL.md. Возвращает dict и печатает разбор."""
    w = 0.05
    eg, eh, em, _ = take.envs(w)
    play = runs(eg > take.gfloor + 15, w, merge=MERGE)
    if not play: return None
    # начало: первый участок длиннее TAKE_MIN, всё до него - фальстарты
    k = next((i for i, (s, e) in enumerate(play) if e - s >= TAKE_MIN), 0)
    false = play[:k]
    pause0 = play[k - 1][1] if k else 0.0
    at = onset(take, play[k][0] - 0.3, play[k][0] + 0.5) or play[k][0]
    cut0 = np.floor((at - 0.05) / GRID) * GRID
    if cut0 < pause0: cut0 = max(pause0, at - 0.1)   # деление сетки попало в фальстарт - ближе к атаке
    # конец: от конца последнего участка вперёд, пока гитара выше пола на 8 dB
    i = int(play[-1][1] / w) - 1
    while i + 1 < len(eg) and eg[i + 1] > take.gfloor + 8: i += 1
    cut1 = (i + 1) * w
    pre = eg[max(0, i - int(0.3 / w))]
    fade, why = 0.4, 'аккорд дозвенел'
    if pre - eg[i] >= 20: fade, why = 0.08, f'резкое глушение: за 0.3 с до реза {pre:.0f} dBFS'
    # дребезг: верха в хвосте последнего аккорда поднимаются над своим минимумом на 6+ dB, общий уровень падает
    w2 = 0.1; g2, h2, _, _ = take.envs(w2)
    j1 = int(cut1 / w2); j0 = max(0, j1 - int(4 / w2))
    buzz = None
    if j1 - j0 > 5:
        seg = h2[j0:j1]; jm = int(np.argmin(seg)); jp = jm + int(np.argmax(seg[jm:]))
        if seg[jp] - seg[jm] >= 6 and g2[j0 + jp] <= g2[j0 + jm] + 1 and (j1 - j0 - jp) * w2 <= 1.5:
            jb = jp
            while jb > jm and seg[jb - 1] >= seg[jm] + 2: jb -= 1
            buzz = ((j0 + jb) * w2, seg[jm], seg[jp])
            if (jp - jb) * w2 <= 0.3 and seg[jp] - seg[jm] >= 12:
                # всплеск на глушении под звенящим аккордом («Против»: −59 -> −36 dB за 0.1 с) - рез до пика, фейд 0.3 с
                cut1 = min(cut1, (j0 + jb + 1) * w2); fade = 0.3
                why = f'всплеск дребезга: верха {buzz[1]:.0f} -> {buzz[2]:.0f} dB с {ms(buzz[0])}, рез до пика'
            else:
                # медленный подъём под затухающим аккордом («Белая птица», 0.9 с) - фейд от начала подъёма, рез за пиком
                cut1 = min(cut1, (j0 + jp + 1) * w2)
                fade = max(0.25, cut1 - buzz[0])
                why = f'дребезг: верха {buzz[1]:.0f} -> {buzz[2]:.0f} dB с {ms(buzz[0])}, фейд через пик'
            i = int(cut1 / w) - 1
    # пауза перед последним аккордом: в последних 8 с гитара падает к полу на 0.3+ с, после - меньше 6 с звука
    tail = None
    quiet = runs(eg < take.gfloor + 10, w, min_len=0.3)
    end = play[-1][1]   # пауза длиннее MERGE сама разрывает участки - искать по времени, а не внутри последнего участка
    for s, e in quiet:
        if end - 8 < s and e < end - 1 and s > play[k][0] + TAKE_MIN:
            tail = (s, e)
    # голос
    vw = 0.1; vs = runs(take.voice(vw), vw, min_len=0.3)
    mic = None
    lead = None
    if vs:
        v0, v1 = vs[0][0], vs[-1][1]
        m0 = np.floor((v0 - 0.5) / GRID) * GRID
        if m0 < cut0 and v0 > pause0:
            # голос вступает раньше гитары (затакт, «Долгая дорога в Дублин»: голос 0:02.5, удар 0:03.4) -
            # общая точка по голосу, иначе рез по гитаре съест первый слог
            lead = v0; cut0 = max(m0, pause0)
        m1 = v1 + 0.6
        mic = (max(m0, cut0) if m0 - cut0 >= 1 else cut0, min(m1, cut1) if cut1 - m1 >= 1 else cut1, v0, v1)
    return dict(cut0=cut0, at=at, lead=lead, false=false, pause0=pause0, cut1=cut1, fade=fade, why=why, buzz=buzz,
                level=eg[i + 1] if i + 1 < len(eg) else eg[i], tail=tail, mic=mic, stop=take.dur - cut1)


def preview(a, path, gname, mname, gcut, mcut, base, spots, user0):
    """A/B спорных резов: модель микса (analyze.py --wav, с цепочками) проекта как есть (A) и копии с предложенными
    резами (B, chain.py --trim); куски вокруг каждого места - <out>/<имя>_<место>_A_user.wav и _B_auto.wav."""
    import subprocess, tempfile
    if not spots:
        print("\nспорных мест нет: резы совпали с предложением до 0.05 с, фейды до 0.1 с"); return
    here = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(a.preview, exist_ok=True)
    copy = os.path.join(a.folder, 'zz-variant-trim.rpp')   # zz-variant* find_rpp не берёт за проект
    cut0, cut1, fade = gcut
    spec = lambda name, s0, s1, fo=None: f"{name}={s0:.3f}-{s1:.3f}" + (f",{fo:.3f}" if fo else '')
    def chain_trim(g0, m0):
        return subprocess.run([sys.executable, os.path.join(here, 'chain.py'), path, path, '-o', copy,
                               '--trim', spec(gname, g0, cut1, fade), '--trim', spec(mname, m0, mcut[1])],
                              capture_output=True, text=True)
    try:
        notes = []
        r = chain_trim(cut0, mcut[0])
        if r.returncode != 0 and 'за 0 таймлайна' in r.stderr:
            # начало раньше проектного уводит первый айтем за 0 таймлайна - в B начало как в проекте
            notes.append('начало предложения раньше начала айтема в проекте - в B начало как в проекте, его не сравнить')
            spots = [s for s in spots if not s[0].endswith('start')]
            r = chain_trim(*user0)
        if r.returncode != 0: print(f"chain.py: {r.stderr.strip()}"); return
        wavs = {}
        with tempfile.TemporaryDirectory() as td:
            for tag, rpp in (('A', path), ('B', copy)):
                out = os.path.join(td, f'{tag}.wav')
                r = subprocess.run([sys.executable, os.path.join(here, 'analyze.py'), a.folder, '--rpp', rpp, '--wav', out],
                                   capture_output=True, text=True)
                if r.returncode != 0: print(f"analyze.py {tag}: {r.stderr.strip()[-300:]}"); return
                wavs[tag] = sf.read(out)
    finally:
        if os.path.exists(copy): os.remove(copy)
    print(f"\n== превью A (проект) / B (предложение), модель микса с цепочками: {a.preview}")
    for n in notes: print(n)
    for key, what, tu, tp, fu, fp in spots:
        b = base[key]   # таймлайн = время файла + POSITION - SOFFS своего айтема (у врезки первый и последний разные)
        lo, hi = min(tu, tp) + b, max(tu, tp) + b
        t0, t1 = (lo - 4, hi + 1.5) if key.endswith('end') else (lo - 1.5, hi + 4)   # кусок с обоими резами
        t0 = max(0.0, t0, t1 - 30)
        for tag, lab in (('A', 'user'), ('B', 'auto')):
            x, sr = wavs[tag]
            clip = x[int(t0 * sr):int(t1 * sr)]
            if len(clip) < int((t1 - t0) * sr): clip = np.pad(clip, ((0, int((t1 - t0) * sr) - len(clip)), (0, 0)))
            sf.write(os.path.join(a.preview, f"{a.name}_{key}_{tag}_{lab}.wav"), clip, sr, subtype='PCM_24')
        fd = f", фейд {fu:.2f} / {fp:.2f} с" if fu is not None else ''
        print(f"  {what}: проект {ms(tu)} / предложение {ms(tp)}{fd} (время файла) -> {a.name}_{key}_A_user.wav, _B_auto.wav, "
              f"кусок {ms(t0)}-{ms(t1)} таймлайна")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('folder'); ap.add_argument('--rpp')
    ap.add_argument('--profile', action='store_true', help='профиль по окнам у резов проекта')
    ap.add_argument('--win', type=float, default=0.25); ap.add_argument('--ctx', type=float, default=4)
    ap.add_argument('--at', nargs='*', help='профиль участков файла «с-по» в секундах: 12-16 205-212')
    ap.add_argument('--preview', metavar='DIR', help='A/B спорных резов моделью микса: куски wav в DIR')
    ap.add_argument('--name', default='trim', help='латинская приставка имён превью (для C:\\rec\\2026)')
    a = ap.parse_args()
    path = freezelib.find_rpp(a.folder, a.rpp)
    _, tracks = parse_rpp(freezelib.read_rpp(path))
    sp = spans(tracks)
    print(f"# {os.path.basename(path)}")
    sig = {}
    for f, (name, first, last, n) in sp.items():
        x, sr = sf.read(os.path.join(a.folder, f), always_2d=True)
        sig[name] = (x.mean(1), sr, f, first, last, n)
    for name, (x, sr, f, first, last, n) in sig.items():
        dur = len(x) / sr; s0 = first['soffs']; s1 = last['soffs'] + last['len']
        print(f"{name}: {os.path.basename(f)} {ms(dur)}, айтемов {n}; оставлено {ms(s0)}-{ms(s1)} файла "
              f"(срез начала {s0:.2f} с, конца {dur - s1:.2f} с), на таймлайне с {ms(first['pos'])}, "
              f"фейд in {first['fi'] * 1000:.0f} мс, out {last['fo'] * 1000:.0f} мс")
    gname = 'guitar' if 'guitar' in sig else next((k for k in sig if 'guit' in k.lower()), None)
    mname = 'mic' if 'mic' in sig else next((k for k in sig if 'mic' in k.lower()), None)
    if not (gname and mname):
        print("нужны треки guitar и mic одного прохода"); return
    passes = {}
    for f, (name, *_ ) in sp.items(): passes.setdefault(name, []).append(f)
    many = {n: passes[n] for n in (gname, mname) if len(passes[n]) > 1}
    if many:
        print("песня собрана из нескольких дублей (" + '; '.join(f"{n}: {len(fs)} файла" for n, fs in many.items())
              + ") - trimfind.py разбирает один проход, резы смотреть руками или --profile по каждому")
        return
    g, m = sig[gname], sig[mname]
    if g[2].rsplit('-', 1)[-1] != m[2].rsplit('-', 1)[-1]:   # 01-guitar-261123_2148.wav / 02-mic-261123_2148.wav
        print(f"предупреждение: дубли {os.path.basename(g[2])} и {os.path.basename(m[2])} похожи на разные проходы")
    take = Take(g[0], m[0], g[1])
    print(f"пол: guitar {take.gfloor:.1f}, mic {take.mfloor:.1f} dBFS; связь mic-гитара без голоса {take.couple:+.1f} dB, верха {take.couple_h:+.1f} dB")
    G, M = g[3:5], m[3:5]
    gs0, gs1 = G[0]['soffs'], G[1]['soffs'] + G[1]['len']
    ms0, ms1 = M[0]['soffs'], M[1]['soffs'] + M[1]['len']

    p = propose(take)
    if p:
        print("\n== предложение (время файла)")
        for s, e in p['false']:
            print(f"фальстарт {ms(s)}-{ms(e)} ({e - s:.1f} с), пауза после него до {ms(p['at'])}")
        lead = f", голос раньше - с {ms(p['lead'])}, рез по нему" if p['lead'] is not None else ''
        print(f"начало: рез {ms(p['cut0'])}, атака первого удара {ms(p['at'])}{lead}; гитара и голос одной точкой, фейд 10 мс")
        print(f"конец гитары: рез {ms(p['cut1'])} (гитара {p['level']:.0f} dBFS, пол {take.gfloor:.0f}), "
              f"фейд {p['fade']:.2f} с - {p['why']}; до стопа остаётся {p['stop']:.1f} с")
        if p['tail']:
            s, e = p['tail']
            print(f"пауза перед последним аккордом {ms(s)}-{ms(e)} ({e - s:.1f} с): вырезать, кроссфейд 0.2 с? - послушать")
        if p['mic']:
            m0, m1, v0, v1 = p['mic']
            print(f"голос: поёт {ms(v0)}-{ms(v1)}; рез mic {ms(m0)}-{ms(m1)}"
                  + ('' if (m0, m1) != (p['cut0'], p['cut1']) else ' (совпадает с гитарой)'))
        print("\n== разница с проектом (проект минус предложение, с)")
        d = lambda x, y: f"{x - y:+.2f}"
        print(f"  гитара: начало {ms(gs0)} ({d(gs0, p['cut0'])}), конец {ms(gs1)} ({d(gs1, p['cut1'])}), "
              f"фейд {G[1]['fo']:.2f} против {p['fade']:.2f}")
        if p['mic']:
            print(f"  голос: начало {ms(ms0)} ({d(ms0, p['mic'][0])}), конец {ms(ms1)} ({d(ms1, p['mic'][1])})")
        mb_ = p['mic'][:2] if p['mic'] else (p['cut0'], p['cut1'])
        args = (f"\"{os.path.basename(path)}\" \"{gname}={p['cut0']:.3f}-{p['cut1']:.3f},{p['fade']:.2f}\" "
                f"\"{mname}={mb_[0]:.3f}-{mb_[1]:.3f}\"")
        print(f"\nразметить: bash trim.sh --mark {args}")
        print(f"применить: bash trim.sh {args}")
        if a.preview:
            mb = mb_
            spots = [s for s in (
                ('guitar_start', 'начало гитары', gs0, p['cut0'], None, None),
                ('guitar_end', 'конец гитары', gs1, p['cut1'], G[1]['fo'], p['fade']),
                ('mic_start', 'начало голоса', ms0, mb[0], None, None),
                ('mic_end', 'конец голоса', ms1, mb[1], None, None))
                if abs(s[2] - s[3]) >= 0.05 or (s[4] is not None and abs(s[4] - s[5]) >= 0.1)]
            bases = {'guitar_start': G[0]['pos'] - G[0]['soffs'], 'guitar_end': G[1]['pos'] - G[1]['soffs'],
                     'mic_start': M[0]['pos'] - M[0]['soffs'], 'mic_end': M[1]['pos'] - M[1]['soffs']}
            preview(a, path, gname, mname, (p['cut0'], p['cut1'], p['fade']), mb, bases, spots, (gs0, ms0))

    if not (a.profile or a.at): return
    w = a.win
    eg, eh, em, emh = take.envs(w)

    def lab(i):
        if em[i] > eg[i] + take.couple + 10 and em[i] > take.mfloor + 12: return 'голос'
        if eg[i] > take.gfloor + 10: return 'гитара'
        if em[i] > take.mfloor + 10: return 'mic шум'
        return '.'

    def prof(a0, a1, cuts):
        i0, i1 = max(0, int(a0 / w)), min(len(eg), int(a1 / w) + 1)
        print("   файл   гитара  верх   mic  верх  сверх   ")
        for i in range(i0, i1):
            t = i * w
            mk = ''.join(f"  <-- {c}" for c, ct in cuts if c and t <= ct < t + w)
            print(f"  {ms(t):>6}  {eg[i]:6.1f} {eh[i]:6.1f} {em[i]:6.1f} {emh[i]:6.1f} "
                  f"{em[i] - eg[i] - take.couple:+5.0f}/{emh[i] - eh[i] - take.couple_h:+3.0f}  {lab(i):7}{mk}")

    print("\nсверх: mic выше пролаза гитары (вся полоса / выше 2 кГц), dB")
    if a.at:
        for rng in a.at:
            t0, t1 = map(float, rng.split('-'))
            print(f"\n== {ms(t0)}-{ms(t1)}"); prof(t0, t1, [])
        return
    print("\n== начало")
    prof(0, max(gs0, ms0) + a.ctx, [('рез гитары', gs0), ('рез mic', ms0)])
    print("\n== конец")
    prof(min(gs1, ms1) - a.ctx, take.dur, [('рез гитары', gs1), ('рез mic', ms1),
                                            ('фейд гитары', gs1 - G[1]['fo']) if G[1]['fo'] > 0.05 else ('', -1)])


if __name__ == '__main__':
    main()
