"""Заморозка VST: разбор цепочек .rpp, точка заморозки, отпечатки, кэш freeze/ и calib.json. Только stdlib.

Точка заморозки трека - выход последнего активного FX, который модель не считает (VST, VSTi, CLAP, незнакомый JSFX).
Отпечаток - sha1 от айтемов трека, FX от начала цепочки до точки включительно (с BYPASS и состоянием VST) и флага FX:
совпал - wav заморозки годится, фейдер и всё после точки модель считает сама.

    python3 freezelib.py plan <папка> [--rpp F]          JSON-план: какие треки, точка, отпечаток, cached
    python3 freezelib.py save <папка> [--rpp F] INDEX...  записать треки в freeze/freeze.json (wav уже скачаны)
"""
import argparse, datetime, glob, hashlib, json, os, re, sys

MODELED = frozenset({'sstillwell/hpflpf', 'sstillwell/rbj4eq', 'sstillwell/1175', 'Liteon/presenceeq',
                     'popstas/guitar_noise_gate.jsfx', 'loser/MGA_JSLimiterST'})
MINOR = ('ReaVerb', 'Liteon/deesser')
VOLATILE = {'SEL', 'FLOATPOS', 'FLOAT', 'WAK', 'SHOW', 'LASTSEL', 'FXID', 'IID', 'GUID', 'IGUID'}
FX_START = re.compile(r'\s*<(JS|VST|CLAP)\b')


def _end(lines, i):
    """Индекс строки '>', закрывающей блок, открытый в строке i."""
    depth = 0
    for j in range(i, len(lines)):
        s = lines[j].strip()
        if s.startswith('<'): depth += 1
        elif s == '>':
            depth -= 1
            if depth == 0: return j
    return len(lines) - 1


def _children(lines, start, end, tag):
    """(начало, конец) прямых дочерних блоков <tag внутри блока [start, end]."""
    out, j = [], start + 1
    while j < end:
        s = lines[j].strip()
        if s.startswith('<'):
            e = _end(lines, j)
            if s == tag or s.startswith(tag + ' '): out.append((j, e))
            j = e + 1
        else:
            j += 1
    return out


def _stable(text):
    return '\n'.join(l for l in text.split('\n') if (l.split() or [''])[0] not in VOLATILE)


def _sha(parts):
    h = hashlib.sha1()
    for p in parts: h.update(p.encode('utf-8')); h.update(b'\0')
    return h.hexdigest()


def fx_blocks(chain_text):
    """FX блока <FXCHAIN/<MASTERFXLIST: bypass, kind (JS/VST/VST3/VSTi/CLAP), name, p (параметры JSFX), text."""
    lines = chain_text.replace('\r', '').split('\n')
    out, j = [], 0
    while j < len(lines) - 1:
        if lines[j].strip().startswith('BYPASS ') and FX_START.match(lines[j + 1]):
            e = _end(lines, j + 1)
            head = lines[j + 1].strip()
            m = re.match(r'<(JS|VST|CLAP)\s+("[^"]*"|\S+)', head)
            tag, name = m.group(1), m.group(2).strip('"')
            kind = tag
            if tag == 'VST':
                k = re.match(r'(VST3i|VST3|VSTi|VST):', name)
                kind = k.group(1) if k else 'VST'
            p = lines[j + 2].split() if tag == 'JS' and j + 2 < e else []
            out.append(dict(bypass=lines[j].split()[1] == '1', kind=kind, name=name, p=p,
                            text='\n'.join(lines[j:e + 1])))
            j = e + 1
        else:
            j += 1
    return out


def kind_of(fx):
    if fx['kind'] == 'JS' and fx['name'] in MODELED: return 'model'
    if any(s in fx['name'] for s in MINOR): return 'minor'
    return 'trigger'


def freeze_point(fxs):
    pts = [i for i, f in enumerate(fxs) if not f['bypass'] and kind_of(f) == 'trigger']
    return pts[-1] if pts else None


def split_tracks(rpp_text):
    """Треки проекта по порядку: index (с 0), name, text (без \\r)."""
    lines = rpp_text.replace('\r', '').split('\n')
    root = next(i for i, l in enumerate(lines) if l.strip().startswith('<REAPER_PROJECT'))
    out = []
    for n, (s, e) in enumerate(_children(lines, root, _end(lines, root), '<TRACK')):
        text = '\n'.join(lines[s:e + 1])
        m = re.search(r'\n\s*NAME ("?)(.*?)\1\n', text)
        out.append(dict(index=n, name=m.group(2) if m else '', text=text))
    return out


def _chain(text, tag):
    lines = text.replace('\r', '').split('\n')
    for i, l in enumerate(lines):
        if l.strip() == tag:
            return '\n'.join(lines[i:_end(lines, i) + 1])
    return ''


def master_fx(rpp_text):
    return fx_blocks(_chain(rpp_text, '<MASTERFXLIST'))


def track_fx(track_text):
    lines = track_text.replace('\r', '').split('\n')
    for s, e in _children(lines, 0, _end(lines, 0), '<FXCHAIN'):
        return fx_blocks('\n'.join(lines[s:e + 1]))
    return []


def _items(track_text):
    lines = track_text.replace('\r', '').split('\n')
    return ['\n'.join(lines[s:e + 1]) for s, e in _children(lines, 0, _end(lines, 0), '<ITEM')]


def _fx_flag(track_text):
    m = re.search(r'\n\s*FX (\d)', track_text)
    return m.group(0).strip() if m else 'FX 1'


def _muted(track_text):
    m = re.search(r'\n\s*MUTESOLO (\d)', track_text)
    return bool(m and m.group(1) == '1')


def track_key(track_text, fxs, point):
    return _sha([_stable(t) for t in _items(track_text)] + [_stable(f['text']) for f in fxs[:point + 1]]
                + [_fx_flag(track_text)])


def plan(rpp_text):
    """Треки к заморозке: index, name, point, after (FX в точке), key, file. Заглушенные и с FX 0 - нет."""
    out = []
    for t in split_tracks(rpp_text):
        if _muted(t['text']) or _fx_flag(t['text']) == 'FX 0': continue
        fxs = track_fx(t['text']); pt = freeze_point(fxs)
        if pt is None: continue
        out.append(dict(index=t['index'], name=t['name'], point=pt, after=re.sub(r'^\w+: ', '', fxs[pt]['name']),
                        key=track_key(t['text'], fxs, pt), file=f"freeze/{t['index'] + 1:02d}.wav"))
    return out


def load_json(folder, name):
    try:
        with open(os.path.join(folder, name), encoding='utf-8') as f: return json.load(f)
    except FileNotFoundError:
        return {}


def save_json(folder, name, data):
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, name), 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=1)


def freeze_record(folder, entry):
    return load_json(os.path.join(folder, 'freeze'), 'freeze.json').get('tracks', {}).get(str(entry['index']))


def freeze_status(folder, entry):
    """'ok' - запись, имя и отпечаток совпали и wav есть; 'stale' - запись не совпала; 'missing' - нет записи или wav."""
    rec = freeze_record(folder, entry)
    if rec is None: return 'missing'
    if rec.get('name') != entry['name'] or rec.get('key') != entry['key']: return 'stale'
    return 'ok' if os.path.exists(os.path.join(folder, entry['file'])) else 'missing'


def calib_key(rpp_text):
    """Отпечаток поправки: отпечатки заморозки + мелкие немоделируемые FX (ReaVerb, де-эссер) треков и мастера."""
    parts = [e['key'] for e in plan(rpp_text)]
    for fxs in [track_fx(t['text']) for t in split_tracks(rpp_text)] + [master_fx(rpp_text)]:
        parts += [_stable(f['text']) for f in fxs if kind_of(f) == 'minor']
    return _sha(parts)


def find_rpp(folder, rpp=None):
    if rpp: return rpp if os.path.isabs(rpp) else os.path.join(folder, rpp)
    return max(glob.glob(os.path.join(folder, '*.rpp')) + glob.glob(os.path.join(folder, '*.RPP')), key=os.path.getmtime)


def read_rpp(path):
    with open(path, encoding='utf-8', errors='replace') as f: return f.read()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['plan', 'save']); ap.add_argument('dir'); ap.add_argument('--rpp')
    ap.add_argument('index', nargs='*', type=int)
    a = ap.parse_args()
    text = read_rpp(find_rpp(a.dir, a.rpp)); p = plan(text)
    if a.cmd == 'plan':
        print(json.dumps([dict(e, cached=freeze_status(a.dir, e) == 'ok') for e in p], ensure_ascii=False))
        return
    fz = os.path.join(a.dir, 'freeze'); data = load_json(fz, 'freeze.json'); data.setdefault('tracks', {})
    now = datetime.datetime.now().isoformat(timespec='minutes')
    for i in a.index:
        e = next((e for e in p if e['index'] == i), None)
        if e is None: sys.exit(f'трек {i} не в плане заморозки')
        if not os.path.exists(os.path.join(a.dir, e['file'])): sys.exit(f"нет {e['file']}")
        data['tracks'][str(i)] = dict(e, time=now)
    save_json(fz, 'freeze.json', data)


if __name__ == '__main__':
    main()
