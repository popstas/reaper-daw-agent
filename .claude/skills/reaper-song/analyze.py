# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy", "scipy", "soundfile", "pyloudnorm", "numba"]
# ///
"""Модель сведения REAPER-проекта: разбирает .rpp, прогоняет дорожки через цепочки
штатных JSFX по параметрам из проекта и печатает замеры для поиска улучшений.

    uv run analyze.py <папка проекта с .rpp и Media/> [--rpp имя.rpp] [--wav out.wav]

ReaVerb, де-эссер и неизвестные плагины не моделируются - это видно в отчёте.
"""
import argparse, json, os, re, sys
import numpy as np, soundfile as sf, pyloudnorm as pyln
from scipy.signal import lfilter, butter, sosfilt, welch, resample_poly
from math import gcd
from numba import njit
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import freezelib

SR = 48000
db = lambda v: 20 * np.log10(np.maximum(v, 1e-12))
meter = None

# ---------- разбор .rpp ----------

def parse_rpp(text):
    """(мастер-FX, треки). Цепочки - freezelib.track_fx: bypass, kind, name, p, text."""
    text = text.replace('\r', '')
    mfx = freezelib.master_fx(text)
    tracks = []
    for tr in freezelib.split_tracks(text):
        tb = tr['text']
        vol = float(re.search(r'\n\s*VOLPAN ([^ \n]+)', tb).group(1))
        ms = re.search(r'\n\s*MUTESOLO (\d)', tb)
        fxon = re.search(r'\n    FX (\d)', tb)
        items, nmidi = [], 0
        for ib in tb.split('<ITEM')[1:]:
            g = lambda k, d=None: (re.search(r'\n\s*' + k + r' ([^\n]+)', ib).group(1) if re.search(r'\n\s*' + k + r' ([^\n]+)', ib) else d)
            f = re.search(r'FILE "([^"]+)"', ib)
            if not f:
                nmidi += '<SOURCE MIDI' in ib
                continue
            items.append(dict(pos=float(g('POSITION')), len=float(g('LENGTH')), soffs=float(g('SOFFS', '0').split()[0]),
                              file=f.group(1).replace('\\', '/'), fi=float(g('FADEIN', '0 0').split()[1]),
                              fo=float(g('FADEOUT', '0 0').split()[1]), vol=float(g('VOLPAN', '1').split()[0]),
                              chan=int(g('CHANMODE', '0')), mute=g('MUTE', '0 0').split()[0] == '1'))
        tracks.append(dict(index=tr['index'], name=tr['name'], text=tb, vol=vol, mute=bool(ms and ms.group(1) == '1'),
                           fx=freezelib.track_fx(tb), fxon=not fxon or fxon.group(1) == '1', items=items, nmidi=nmidi))
    return mfx, tracks

def build(track, root):
    its = [i for i in track['items'] if not i['mute']]
    if not its: return None
    end = max(i['pos'] + i['len'] for i in its)
    y = np.zeros((int(end * SR) + 1, 2))
    for it in its:
        x, sr = sf.read(os.path.join(root, it['file']), always_2d=True)
        if sr != SR:  # REAPER ресемплирует источник под проект (H2e пишет 96 кГц)
            g = gcd(SR, sr); x = resample_poly(x, SR // g, sr // g, axis=0)
        if it['chan'] == 2: x = np.repeat(x.mean(1, keepdims=True), 2, 1)
        elif it['chan'] == 3: x = np.repeat(x[:, :1], 2, 1)
        elif it['chan'] == 4: x = np.repeat(x[:, 1:2], 2, 1)
        elif x.shape[1] == 1: x = np.repeat(x, 2, 1)
        a = int(it['soffs'] * SR); seg = x[a:a + int(it['len'] * SR)].copy(); n = len(seg)
        env = np.ones(n); fi = min(int(it['fi'] * SR), n); fo = min(int(it['fo'] * SR), n)
        if fi: env[:fi] *= np.linspace(0, 1, fi)
        if fo: env[-fo:] *= np.linspace(1, 0, fo)
        p = int(it['pos'] * SR); y[p:p + n] += seg * env[:, None] * it['vol']
    return y

def fit(x, length):
    """Обрезать или добить нулями до length сэмплов."""
    if length is None or len(x) == length: return x
    return x[:length] if len(x) > length else np.pad(x, ((0, length - len(x)), (0, 0)))

def track_signal(t, folder, freeze_entry, length):
    """Сигнал трека, цепочка к прогону и строка о заморозке ('' - трек не замораживается).
    Актуальная заморозка - wav с позиции 0 и FX после точки; иначе айтемы и вся цепочка."""
    if freeze_entry is None: return build(t, folder), t['fx'], ''
    st = freezelib.freeze_status(folder, freeze_entry)
    if st == 'ok':
        x, sr = sf.read(os.path.join(folder, freeze_entry['file']), always_2d=True)
        assert sr == SR, f"{freeze_entry['file']}: {sr} Гц"
        x = np.repeat(x, 2, 1) if x.shape[1] == 1 else x[:, :2]
        when = freezelib.freeze_record(folder, freeze_entry).get('time', '')
        when = f"{when[8:10]}.{when[5:7]} {when[11:16]}" if len(when) >= 16 else when
        return fit(x.astype(np.float64), length), t['fx'][freeze_entry['point'] + 1:], f"заморожено после {freeze_entry['after']} (freeze {when})"
    note = 'заморозка устарела - freeze.sh' if st == 'stale' else 'нет заморозки - freeze.sh'
    return build(t, folder), t['fx'], f"{note} (после {freeze_entry['after']} модель не считает)"

def model_length(tracks, folder, plan):
    """Сэмплов в модели: максимум из концов айтемов и длин актуальных wav заморозки."""
    end = max([i['pos'] + i['len'] for t in tracks if not t['mute'] for i in t['items'] if not i['mute']] or [0])
    n = int(end * SR) + 1
    for t in tracks:
        e = plan.get(t['index'])
        if e and not t['mute'] and freezelib.freeze_status(folder, e) == 'ok':
            n = max(n, sf.info(os.path.join(folder, e['file'])).frames)
    return n

# ---------- DSP: порты штатных JSFX ----------

def num(p, i, d):
    try: return float(p[i])
    except (IndexError, ValueError): return d

def biquad(x, b, a): return lfilter(np.array(b) / a[0], np.array(a) / a[0], x, axis=0)

def hpflpf(x, p):
    f1, f2, g = num(p, 0, 0), num(p, 1, 22000), num(p, 2, 0)
    q = 1 / np.sqrt(2)
    if f1 > 0:
        w = 2 * np.pi * f1 / SR; c, s = np.cos(w), np.sin(w); al = s / (2 * q)
        x = biquad(x, [(1 + c) / 2, -(1 + c), (1 + c) / 2], [1 + al, -2 * c, 1 - al])
    if f2 != 22000:
        w = 2 * np.pi * f2 / SR; c, s = np.cos(w), np.sin(w); al = s / (2 * q)
        x = biquad(x, [(1 - c) / 2, 1 - c, (1 - c) / 2], [1 + al, -2 * c, 1 - al])
    return x * 10 ** (g / 20)

def peaking(x, f, g, q):
    if g == 0: return x
    A = 10 ** (g / 40); w = 2 * np.pi * f / SR; c, s = np.cos(w), np.sin(w); al = s / (2 * q)
    return biquad(x, [1 + al * A, -2 * c, 1 - al * A], [1 + al / A, -2 * c, 1 - al / A])

def rbj4eq(x, p):
    tabs = [(40, 80, 160, 315, 500), (125, 250, 500, 1000, 2000), (315, 630, 1200, 2500, 5000), (1600, 3200, 6400, 9000, 12000)]
    for b in range(4):
        idx = int(num(p, 2 * b, 3)); f = tabs[b][min(max(idx, 0), 4)]
        x = peaking(x, f, num(p, 2 * b + 1, 0), 0.8)
    return x

def presenceeq(x, p):
    # Liteon presence: колокол на Frequency с Boost и шириной Bandwidth (окт.) - приближение
    return peaking(x, num(p, 1, 7700), num(p, 2, 0), 1 / max(num(p, 3, 0.2) * 5, 0.2)) * 10 ** (num(p, 4, 0) / 20)

@njit(cache=True)
def _c1175(x, thr, ratio, makeup, att_us, rel_ms, sr):
    l2d = 8.685889638065037; cthv = np.exp(thr / l2d)
    atc = np.exp(-1 / (att_us / 1e6 * sr)); rlc = np.exp(-1 / (rel_ms / 1000 * sr))
    mk = np.exp(makeup / l2d); rundb = 0.0; y = np.empty_like(x); gr = np.empty(x.shape[0])
    for i in range(x.shape[0]):
        det = max(abs(x[i, 0]), abs(x[i, 1]))
        over = max(0.0, l2d * np.log(det / cthv)) if det > 0 else 0.0
        rundb = over + atc * (rundb - over) if over > rundb else over + rlc * (rundb - over)
        gr[i] = -rundb * (ratio - 1) / ratio; gv = np.exp(gr[i] / l2d) * mk
        y[i, 0] = x[i, 0] * gv; y[i, 1] = x[i, 1] * gv
    return y, gr

def c1175(x, p, stats):
    rpos = int(num(p, 1, 5)); rpos = rpos - 5 if rpos > 4 else rpos
    ratio = [4, 8, 12, 20, 20][rpos]
    y, gr = _c1175(x, num(p, 0, 0), ratio, num(p, 2, 0), num(p, 3, 20), num(p, 4, 250), SR)
    stats['1175'] = dict(thr=num(p, 0, 0), makeup=num(p, 2, 0), active=100 * np.mean(gr < -0.5),
                         med=float(np.median(gr)), p95=float(np.percentile(gr, 5)))
    mix = num(p, 5, 100) / 100
    return y * mix + x * (1 - mix)

@njit(cache=True)
def _gate(env, to, tc, hold, atk, rel, rng):
    op = 0; hc = 0; g = rng; out = np.empty(env.shape[0]); st = np.zeros(env.shape[0])
    for i in range(env.shape[0]):
        l = env[i]
        if l > to: op = 1
        if op:
            if l >= tc: hc = hold
            elif hc > 0: hc -= 1
            else: op = 0
        t = 1.0 if op else rng
        g = t + (atk if t > g else rel) * (g - t); out[i] = g; st[i] = op
    return out, st

def noise_gate(x, p, stats):
    """popstas/guitar_noise_gate: режекторы + основной гейт (полосы HF/Top не моделируются - они только про шипение)."""
    f0, nh, q = num(p, 6, 801.8), int(num(p, 7, 6)), num(p, 8, 20)
    y = x.copy()
    if f0 > 0:
        for k in range(1, min(nh, 12) + 1):
            if f0 * k >= 0.45 * SR: break
            w = 2 * np.pi * f0 * k / SR; a = np.sin(w) / (2 * q); c = np.cos(w)
            y = biquad(y, [1, -2 * c, 1], [1 + a, -2 * c, 1 - a])
    ec = np.exp(-1 / (0.010 * SR)); det = np.max(y * y, axis=1)
    env = np.sqrt(lfilter([1 - ec], [1, -ec], det))
    to, tc = num(p, 0, -50), min(num(p, 1, -54), num(p, 0, -50))
    g, st = _gate(env, 10 ** (to / 20), 10 ** (tc / 20), int(num(p, 2, 150) * 1e-3 * SR),
                  np.exp(-1 / (max(num(p, 3, 1), 0.1) * 1e-3 * SR)), np.exp(-1 / (num(p, 4, 250) * 1e-3 * SR)), 10 ** (num(p, 5, -90) / 20))
    ch = np.diff(st); opens = int((ch > 0).sum())
    stats['gate'] = dict(open_pct=100 * st.mean(), openings=opens, thr=f"{to:g}/{tc:g}",
                         hf=('выкл' if num(p, 10, 0) == 0 else ('экспандер' if num(p, 15, 0) else 'гейт')),
                         top=num(p, 19, 0))
    return y * g[:, None]

@njit(cache=True)
def _mga(x, thr_db, rel_ms, link_pct, ceil_db, sr):
    th = 10 ** (thr_db / 20); vol = 10 ** (ceil_db / 20) / th; r = np.exp(-3 / (sr * max(rel_ms / 1000, 0.05))); link = np.sqrt(link_pct * 0.01)
    H = sr / 128; t1 = 0.0; t2 = H / 2; t1o = 0.0; t2o = H / 2; m1 = 0.0; m2 = 0.0; m1o = 0.0; m2o = 0.0; env = 0.0; envo = 0.0
    y = np.empty_like(x); gr = np.empty(x.shape[0])
    for i in range(x.shape[0]):
        a = abs(x[i, 0]); b = abs(x[i, 1])
        t1 += 1
        if t1 > H: t1 = 0.0; m1 = 0.0
        m1 = max(m1, a); t2 += 1
        if t2 > H: t2 = 0.0; m2 = 0.0
        m2 = max(m2, a); eT = max(m1, m2)
        t1o += 1
        if t1o > H: t1o = 0.0; m1o = 0.0
        m1o = max(m1o, b); t2o += 1
        if t2o > H: t2o = 0.0; m2o = 0.0
        m2o = max(m2o, b); eTo = max(m1o, m2o)
        env = max(env, envo * link); envo = max(env * link, envo)
        env = eT if env < eT else eT + r * (env - eT)
        g = th / env * vol if env > th else vol
        envo = eTo if envo < eTo else eTo + r * (envo - eTo)
        go = th / envo * vol if envo > th else vol
        y[i, 0] = x[i, 0] * g; y[i, 1] = x[i, 1] * go; gr[i] = min(g, go) / vol
    return y, gr

def mga(x, p, stats):
    y, gr = _mga(x, num(p, 0, 0), num(p, 1, 200), num(p, 2, 75), num(p, 3, -0.1), SR)
    stats['limiter'] = dict(thr=num(p, 0, 0), ceil=num(p, 3, -0.1), gain=num(p, 3, -0.1) - num(p, 0, 0),
                            active=100 * np.mean(gr < 0.989), p99=float(db(np.percentile(gr, 1))))
    return y

FX = {'sstillwell/hpflpf': lambda x, p, s: hpflpf(x, p), 'sstillwell/rbj4eq': lambda x, p, s: rbj4eq(x, p),
      'sstillwell/1175': c1175, 'Liteon/presenceeq': lambda x, p, s: presenceeq(x, p),
      'popstas/guitar_noise_gate.jsfx': noise_gate, 'loser/MGA_JSLimiterST': mga,
      'popstas/ms_decode.jsfx': lambda x, p, s: ms_decode(x, p)}

def ms_decode(x, p):
    """popstas/ms_decode.jsfx: левый вход - mid, правый - side; L = M + w*S, R = M - w*S, затем Gain."""
    w, g = num(p, 0, 100) / 100, 10 ** (num(p, 1, 0) / 20)
    m, s = x[:, 0], x[:, 1]
    return np.stack([m + w * s, m - w * s], 1) * g

def run_chain(x, fxs, label):
    stats, skipped = {}, []
    for fx in fxs:
        if fx['bypass']: continue
        fn = FX.get(fx['name'])
        if fn: x = fn(x, fx['p'], stats)
        else: skipped.append(fx['name'].split('/')[-1].replace('VST: ', ''))
    return x, stats, skipped

# ---------- отчёт ----------

def mmss(t):
    t = max(t, 0.0); return f"{int(t // 60)}:{t % 60:04.1f}" if t % 1 >= 0.05 else f"{int(t // 60)}:{int(round(t % 60)):02d}"

KB = ([1.5351828863637502, -2.691804030199196, 1.198426263333146], [1.0, -1.6906995865986896, 0.7325047060963897],
      [0.9950442970178917, -1.9900885940357833, 0.9950442970178917], [1.0, -1.990076284018423, 0.9901009040531438])
# K-фильтр - коэффициенты pyloudnorm.Meter(48000), чтобы цифры совпадали с прежними замерами модели

def kfilter(x):
    return lfilter(KB[2], KB[3], lfilter(KB[0], KB[1], x, axis=0), axis=0)

def lufs_fast(x):
    """Integrated LUFS по BS.1770-4 с разбиением на блоки как в pyloudnorm (400 мс, шаг 100 мс, гейты -70 и -10 LU),
    но суммы блоков - через cumsum, без цикла по блокам."""
    n = int(0.4 * SR)
    if len(x) < n: return -99.0
    c = np.concatenate([[0.0], np.cumsum((kfilter(x) ** 2).sum(1))])
    j = np.arange(int(np.round((len(x) / SR - 0.4) / 0.1)) + 1)
    lo = np.minimum((0.4 * j * 0.25 * SR).astype(int), len(x)); hi = np.minimum((0.4 * (j * 0.25 + 1) * SR).astype(int), len(x))
    p = (c[hi] - c[lo]) / n
    lv = -0.691 + 10 * np.log10(np.maximum(p, 1e-20)); g = lv >= -70
    if not g.any(): return -99.0
    rel = -0.691 + 10 * np.log10(p[g].mean()) - 10
    g2 = (lv > -70) & (lv > rel)
    return float(-0.691 + 10 * np.log10(p[g2].mean())) if g2.any() else -99.0

def lufs(x):
    return lufs_fast(x)

def short_term(x, win=3.0, hop=1.0):
    """Short-term громкость BS.1770 (K-фильтр, без гейта) в окнах win с шагом hop: одна фильтрация вместо LUFS на окно."""
    c = np.concatenate([[0.0], np.cumsum((kfilter(x) ** 2).sum(1))]); n, h = int(win * SR), int(hop * SR)
    st = np.arange(0, max(len(x) - n, 1), h); e = np.minimum(st + n, len(x))
    return -0.691 + 10 * np.log10(np.maximum((c[e] - c[st]) / np.maximum(e - st, 1), 1e-20))

def frames(x, w):
    n = int(w * SR); k = len(x) // n; return db(np.sqrt((x[:k * n].reshape(k, n) ** 2).mean(1)))

DEFAULT_MASTER = 0.5   # рендер громче модели: ReaVerb, де-эссер, разница портов (14-18.11: +0.3...+0.7)

def load_calib(folder, rpp_text):
    """Поправки рендер - модель из calib.json ({} если нет или устарели) и строка отчёта."""
    c = freezelib.load_json(folder, 'calib.json')
    fix = f'мастер {DEFAULT_MASTER:+.1f} по умолчанию'
    if not c: return {}, f'поправки нет - render.sh --stems --calib (рендер «до» со стемами); {fix}'
    if c.get('key') != freezelib.calib_key(rpp_text, folder):
        return {}, f'поправка устарела - рендер «до» со стемами (render.sh --stems --calib); {fix}'
    tm = c.get('time', ''); tm = f"{tm[8:10]}.{tm[5:7]} {tm[11:16]}" if len(tm) >= 16 else tm
    parts = [f"{n} {v:+.1f}" for n, v in (c.get('tracks') or {}).items()]
    m = c.get('master')
    return c, f"поправка по рендеру до ({tm}): " + ', '.join(parts) + (f"; мастер {m:+.1f}" if m is not None else f'; {fix}')

def solve_threshold(mix, mfx, target, offset):
    """Порог первого активного MGA_JSLimiterST мастера, при котором прогноз рендера (модель + offset) = target ± 0.1.
    Ниже порог - громче. Без вилки - сначала нужный предел (-30 или 0), внутри вилки - секущая, иначе бисекция."""
    idx = next((i for i, f in enumerate(mfx) if not f['bypass'] and f['name'] == 'loser/MGA_JSLimiterST'), None)
    if idx is None: return dict(ok=False, thr=None, model=None, pred=None, note='нет MGA_JSLimiterST на мастере')
    def ev(thr):
        p = list(mfx[idx]['p']) or ['0']; p[0] = f'{thr:g}'
        fx = mfx[:idx] + [dict(mfx[idx], p=p)] + mfx[idx + 1:]
        m = lufs(run_chain(mix, fx, 'master')[0]); return m, m + offset
    # секущая внутри вилки от текущего порога (отдача лимитера почти линейна: -1 dB порога = +1 dB), иначе бисекция
    pts = {}
    def at(t):
        t = round(min(0.0, max(-30.0, t)), 3)
        if t not in pts: pts[t] = ev(t)
        return t, pts[t][0], pts[t][1]
    t, m, pr = at(num(mfx[idx]['p'], 0, -8))
    for _ in range(13):
        if abs(pr - target) <= 0.05: break
        if t == -30 and pr < target: return dict(ok=False, thr=t, model=m, pred=pr, note=f'цель недостижима: при пороге -30 прогноз {pr:.1f}')
        if t == 0 and pr > target: return dict(ok=False, thr=t, model=m, pred=pr, note=f'цель недостижима: при пороге 0 прогноз {pr:.1f}')
        loud = [k for k, v in pts.items() if v[1] > target]; quiet = [k for k, v in pts.items() if v[1] < target]
        if loud and quiet:
            a_, b_ = max(loud), min(quiet); pa, pb = pts[a_][1], pts[b_][1]
            nt = a_ + (b_ - a_) * (pa - target) / (pa - pb)
            if not a_ < nt < b_ or abs(nt - t) < 1e-3: nt = (a_ + b_) / 2
        elif not loud and -30.0 not in pts:   # все прогнозы тише цели: сначала проверить предел -30 (у плато шаги мельчают)
            nt = -30.0
        elif not quiet and 0.0 not in pts:    # все прогнозы громче цели: предел 0
            nt = 0.0
        else:
            nt = t + (pr - target)
        t, m, pr = at(nt)
    # порог печатается с десятыми: круглое значение, а если оно уводит от цели - ближайшее из соседних
    t1, m, pr = at(round(t, 1))
    if abs(pr - target) > 0.1:
        t1, m, pr = min((at(round(t, 1) + d) for d in (-0.1, 0.1)), key=lambda r: abs(r[2] - target))
    thr = round(t1, 1)
    ok = abs(pr - target) <= 0.1
    head = f"порог лимитера под {target:.1f} LUFS" if ok else f"порог лимитера не сошёлся под {target:.1f} LUFS, ближайший"
    return dict(ok=ok, thr=thr, model=m, pred=pr, note=f"{head}: {thr:.1f} (модель {m:.1f}, поправка {offset:+.1f}, прогноз {pr:.1f})")

def report_raw(t, x):
    """Сырой сигнал трека (айтемы до цепочки): уровень, где звук, стерео, стыки айтемов."""
    n0 = frames(x[:, 0], 0.05); act = np.where(n0 > np.percentile(n0, 95) - 30)[0]
    print(f"сырой: {lufs(x):.1f} LUFS, пик {db(abs(x).max()):+.1f} dBFS, выше 0 dBFS: {int((abs(x[:, 0]) > 1).sum())} сэмплов (во float это не клип)")
    if len(act): print(f"звук с {mmss(act[0] * 0.05)} по {mmss(act[-1] * 0.05)} из {mmss(len(x) / SR)}; самые тихие 5% (окна 50 мс) {np.percentile(n0, 5):.1f} dB")
    if not np.allclose(x[:, 0], x[:, 1]):
        print(f"стерео: L {db(np.sqrt(np.mean(x[:, 0] ** 2))):.1f} / R {db(np.sqrt(np.mean(x[:, 1] ** 2))):.1f} dB")
    for it_prev, it in zip(t['items'], t['items'][1:]):
        p = int(it['pos'] * SR); w = int(0.005 * SR)
        if p < 6 * w or p + 6 * w > len(x): continue
        lv = [db(np.sqrt(np.mean(x[p + o * w:p + (o + 1) * w, 0] ** 2))) for o in range(-4, 4)]
        gap = it['pos'] - (it_prev['pos'] + it_prev['len'])
        b2 = db(np.sqrt(np.mean(x[p - 2 * SR:p, 0] ** 2))); a2 = db(np.sqrt(np.mean(x[p:p + 2 * SR, 0] ** 2)))
        dip = ("рядом пауза, провал не важен" if min(lv[0], lv[-1]) < -35 else f"провал {min(lv) - max(lv[0], lv[-1]):+.0f} dB (5 мс окна)")
        print(f"стык {mmss(it['pos'])}: перекрытие {max(-gap, 0.0) * 1000 + 0.0:.0f} мс, фейды {it_prev['fo'] * 1000:.0f}/{it['fi'] * 1000:.0f} мс; "
              f"{dip}; уровень 2 с до/после {b2:.1f}/{a2:.1f}")

def main():
    global meter
    ap = argparse.ArgumentParser(); ap.add_argument('dir'); ap.add_argument('--rpp'); ap.add_argument('--wav')
    ap.add_argument('--json', help='записать уровни треков и мастера в JSON')
    ap.add_argument('--target', type=float, help='подобрать порог MGA_JSLimiterST мастера под прогноз рендера, LUFS')
    ap.add_argument('--no-calib', action='store_true', help='не применять calib.json')
    ap.add_argument('--stems-dir', help='записать модельные выходы треков (после цепочки, фейдера и поправки) в DIR/<трек>.wav')
    a = ap.parse_args(); meter = pyln.Meter(SR)
    path = freezelib.find_rpp(a.dir, a.rpp); rpp = os.path.basename(path)
    text = freezelib.read_rpp(path)
    mfx, tracks = parse_rpp(text)
    plan = {e['index']: e for e in freezelib.plan(text)}
    length = model_length(tracks, a.dir, plan)
    print(f"# {rpp}")
    calib, cnote = ({}, f'без поправки (--no-calib), мастер {DEFAULT_MASTER:+.1f} по умолчанию') if a.no_calib else load_calib(a.dir, text)
    print(cnote)
    toff = calib.get('tracks') or {}
    outs, raw = {}, {}
    for t in tracks:
        if t['mute']: print(f"## {t['name']}: заглушен, пропущен"); continue
        sig, chain, note = track_signal(t, a.dir, plan.get(t['index']), length)
        if sig is None and not note: continue
        print(f"\n## {t['name']}  (фейдер {db(t['vol']):+.1f} dB, айтемов {len(t['items'])}" + (f", MIDI {t['nmidi']}" if t['nmidi'] else '') + ")")
        if note: print(note)
        if sig is None: continue
        x = build(t, a.dir) if note.startswith('заморожено') else sig   # сырой сигнал: айтемы до цепочки
        if x is not None:
            raw[t['name']] = x
            report_raw(t, x)
        if t['fxon']:
            y, st, sk = run_chain(sig, chain, t['name'])
        else:
            y, st, sk = sig, {}, ['FX выключены']
        y = y * t['vol'] * 10 ** (toff.get(t['name'], 0) / 20); outs[t['name']] = y
        print(f"после цепочки и фейдера: {lufs(y):.1f} LUFS" + (f"; не моделируется: {', '.join(sk)}" if sk else ''))
        if 'gate' in st:
            g = st['gate']; print(f"гейт {g['thr']}: открыт {g['open_pct']:.0f}% времени, открытий {g['openings']}; HF: {g['hf']}, Top: {g['top']:g} Гц")
        if '1175' in st:
            c = st['1175']; print(f"1175 порог {c['thr']:g}, makeup {c['makeup']:+g}: сжимает {c['active']:.0f}% времени, медиана {c['med']:.1f}, p95 {c['p95']:.1f} dB")
    if not outs: sys.exit('нет айтемов')
    L = max(len(v) for v in outs.values())
    mix = sum(np.pad(v, ((0, L - len(v)), (0, 0))) for v in outs.values())
    voc = next((n for n in outs if re.search(r'mic|voc|голос', n, re.I)), None)
    if voc and len(outs) > 1:
        others = sum(np.pad(v, ((0, L - len(v)), (0, 0))) for n, v in outs.items() if n != voc)
        vo = np.pad(outs[voc], ((0, L - len(outs[voc])), (0, 0)))
        print(f"\n## баланс: {voc} громче остального на {lufs(vo) - lufs(others):.1f} LU (ориентир 4-6)")
        vr, gr_ = frames(vo[:, 0], 0.4), frames(others[:, 0], 0.4); sing = vr > np.percentile(vr, 90) - 18
        # микрофон слышит гитару из комнаты: без голоса сырой mic тише сырой гитары на постоянную величину (связь),
        # с голосом разница растёт. Пением считаем окна на 10 dB выше связи, иначе пролаз гитары идёт за «тихий голос»
        gname = next((n for n in raw if n != voc and re.search(r'guit|гитар', n, re.I)), None)
        if gname:
            L2 = min(len(raw[voc]), len(raw[gname]))
            d = frames(raw[voc][:L2, 0], 0.4) - frames(raw[gname][:L2, 0], 0.4)
            ga = frames(raw[gname][:L2, 0], 0.4) > np.percentile(frames(raw[gname][:L2, 0], 0.4), 90) - 30
            if ga.sum() > 20:
                couple = np.percentile(d[ga], 10)
                bleed = np.zeros(len(vr), bool); bleed[:len(d)] = ga & (d < couple + 10)
                sing &= ~bleed
                print(f"пролаз гитары в mic: сырой mic ниже гитары на {-couple:.0f} dB без голоса; без голоса {bleed.mean() * 100:.0f}% времени")
        parts = []
        for s in range(0, len(vr), 50):
            m = sing[s:s + 50]
            parts.append(f"{mmss(s * 0.4)} {np.mean(vr[s:s + 50][m] - gr_[s:s + 50][m]):+.1f}" if m.sum() > 5 else f"{mmss(s * 0.4)} —")
        print("по 20 с, пока поёт: " + "  ".join(parts))
        sos = butter(4, [5000, 9000], 'bandpass', fs=SR, output='sos')
        full, sib = frames(vo[:, 0], 0.02), frames(sosfilt(sos, vo[:, 0]), 0.02)
        print(f"свистящие (5-9 кГц в пределах 6 dB от всей полосы, до де-эссера): {np.sum((sib - full > -6) & (full > -40)) * 0.02:.1f} с")
    out, st, sk = run_chain(mix, mfx, 'master')
    moff = calib.get('master'); msrc = 'по рендеру до'
    if moff is None: moff, msrc = DEFAULT_MASTER, 'по умолчанию'
    pred = lufs(out) + moff
    print(f"\n## мастер: до цепочки {lufs(mix):.1f} LUFS, пик {db(abs(mix).max()):+.1f}; на выходе {lufs(out):.1f} LUFS, пик {db(abs(out).max()):+.1f} dBFS"
          + (f"; не моделируется: {', '.join(sk)}" if sk else '') + f"; рендер ≈ {pred:.1f} (поправка {moff:+.1f} {msrc})")
    if a.target is not None:
        r = solve_threshold(mix, mfx, a.target, moff); print(r['note'])
    if 'limiter' in st:
        l = st['limiter']; print(f"лимитер {l['thr']:g}/{l['ceil']:g} (подъём {l['gain']:+.1f} dB): режет пики {l['active']:.1f}% времени, p99 {l['p99']:.1f} dB")
    stl = list(short_term(out))
    print("short-term 3 с, по 10 с: " + "  ".join(f"{mmss(i * 10)} {np.mean([v for v in stl[i * 10:i * 10 + 10] if v > -90] or [-99]):.0f}" for i in range((len(stl) + 9) // 10)))
    if voc and len(outs) > 1:
        bands = [(40, 100), (100, 250), (250, 500), (500, 1000), (1000, 2000), (2000, 4000), (4000, 8000), (8000, 16000)]
        def be(v): f, P = welch(v[:, 0], SR, nperseg=8192); return [10 * np.log10(np.sum(P[(f >= lo) & (f < hi)]) + 1e-20) for lo, hi in bands]
        e1, e2 = be(vo), be(others)
        print("полосы, голос минус остальное (dB): " + " ".join(f"{lo}-{hi}:{x2 - x1:+.0f}" for (lo, hi), x1, x2 in zip(bands, e2, e1)))
    if a.wav: sf.write(a.wav, out.astype(np.float32), SR, subtype='FLOAT'); print(f"модель микса: {a.wav}")
    if a.stems_dir:
        os.makedirs(a.stems_dir, exist_ok=True)
        for n, v in outs.items(): sf.write(os.path.join(a.stems_dir, f"{n}.wav"), v.astype(np.float32), SR, subtype='FLOAT')
    if a.json:
        with open(a.json, 'w', encoding='utf-8') as f:
            json.dump(dict(tracks={n: dict(lufs=round(lufs(v), 3)) for n, v in outs.items()}, master_in=round(lufs(mix), 3),
                           master_out=round(lufs(out), 3), pred=round(pred, 3)), f, ensure_ascii=False)

if __name__ == '__main__':
    main()
