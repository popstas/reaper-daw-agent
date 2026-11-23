#!/usr/bin/env python3
"""Перенести звенья цепочек из шаблона в старый проект и привести его к шаблону. Правит .rpp-файл (CRLF сохраняется).

  python3 chain.py <проект.rpp> <шаблон.rpp> [-o OUT] [правки...]

  --copy 'ТРЕК=ИСТ:FX1,FX2[@ПОСЛЕ]'  звенья из трека ИСТ шаблона (подстроки строки <JS/<VST, в порядке шаблона) - в трек ТРЕК
                                    проекта: без @ - в начало цепочки, с @ - после звена с подстрокой ПОСЛЕ. Звенья - как в
                                    шаблоне, со всеми параметрами, FXID новые. ТРЕК/ИСТ - имя трека целиком или master.
                                    У трека включается цепочка (FX 1 / MASTER_FX 1)
  --bypass 'ТРЕК:FX'                выключить звено (BYPASS 1), не удаляя
  --drop 'ТРЕК'                     удалить трек; глубина папки переходит предыдущему треку (ISBUS). Папку с детьми не удаляет
  --header KEY[,KEY...]             строки шапки проекта (TIMELOCKMODE, SAMPLERATE, RENDER_PATTERN, ...) - из шаблона
  --name 'СТАРОЕ=НОВОЕ'             переименовать трек
  --item 'ТРЕК=ФАЙЛ@SOFFS+LENGTH[,FI,FO]'  айтем WAVE с позиции 0: кусок файла (путь от папки проекта) с SOFFS длиной
                                    LENGTH секунд, фейды FI/FO (по умолчанию 0.01)
  --addjs 'ТРЕК=JS:П1 П2 ...[@ПОСЛЕ]'  новое звено JSFX (JS - путь в Effects, popstas/ms_decode.jsfx) с параметрами,
                                    добитыми '-' до 64; без @ - в начало цепочки
  --untrim                          снять обрезку: айтемы WAVE трека - по одному на файл, весь файл с позиции 0, фейды 10 мс
                                    (громкость айтема та же; MIDI не трогается). Пути FILE - от папки проекта
  --marker 'СЕК=ИМЯ'                маркер на позиции СЕК (номера - по порядку времени)
  --trim 'ТРЕК=S0-S1[,FO]'          границы трека во времени файла: первому айтему SOFFS S0 (звук на том же месте таймлайна),
                                    последнему конец на S1 и фейд FO с; айтемы между ними (врезки) не трогаются

Без -o файл проекта перезаписывается. Печатает каждую правку.
"""
import argparse, os, re, shlex, sys, uuid


def read(path):
    with open(path, 'rb') as f: data = f.read()
    return data.decode('utf-8').split('\r\n')


def indent(s): return len(s) - len(s.lstrip(' '))


def block_end(lines, i):
    """Индекс строки '>' блока, открытого в lines[i]."""
    ind = indent(lines[i])
    for j in range(i + 1, len(lines)):
        if indent(lines[j]) == ind and lines[j].strip() == '>': return j
    raise ValueError(f'блок без конца: {lines[i].strip()}')


def unquote(s):
    s = s.strip()
    return s[1:-1] if len(s) >= 2 and s[0] == s[-1] and s[0] in '"\'`' else s


def tracks(lines):
    """[(имя, начало, конец)] треков верхнего уровня."""
    out, i = [], 0
    while i < len(lines):
        if indent(lines[i]) == 2 and lines[i].lstrip().startswith('<TRACK'):
            e = block_end(lines, i)
            name = next((unquote(l.strip()[5:]) for l in lines[i + 1:e] if indent(l) == 4 and l.strip().startswith('NAME ')), '')
            out.append((name, i, e)); i = e + 1
        else: i += 1
    return out


def find_track(lines, name):
    hits = [t for t in tracks(lines) if t[0] == name]
    if len(hits) != 1: raise ValueError(f'трек {name!r}: найдено {len(hits)}, есть {[t[0] for t in tracks(lines)]}')
    return hits[0]


def chain(lines, track):
    """(начало, конец) блока FXCHAIN трека или MASTERFXLIST."""
    if track == 'master':
        i = next((i for i, l in enumerate(lines) if indent(l) == 2 and l.strip() == '<MASTERFXLIST'), None)
        if i is None: raise ValueError('нет MASTERFXLIST')
        return i, block_end(lines, i)
    _, s, e = find_track(lines, track)
    i = next((i for i in range(s, e) if indent(lines[i]) == indent(lines[s]) + 2 and lines[i].strip() == '<FXCHAIN'), None)
    if i is None: raise ValueError(f'у трека {track!r} нет FXCHAIN')
    return i, block_end(lines, i)


def entries(lines, cs, ce):
    """[(начало, конец_исключая, заголовок звена)] звеньев цепочки."""
    ind = indent(lines[cs]) + 2
    starts = [i for i in range(cs + 1, ce) if indent(lines[i]) == ind and lines[i].strip().startswith('BYPASS ')]
    out = []
    for k, s in enumerate(starts):
        e = starts[k + 1] if k + 1 < len(starts) else ce
        head = next((lines[j].strip() for j in range(s + 1, e) if indent(lines[j]) == ind and lines[j].strip().startswith('<')), '')
        out.append((s, e, head))
    return out


def pick(ents, sub, where):
    hits = [x for x in ents if sub.lower() in x[2].lower()]
    if len(hits) != 1: raise ValueError(f'{where}: звено {sub!r} найдено {len(hits)} раз, есть {[x[2] for x in ents]}')
    return hits[0]


def short(head):
    m = re.match(r'<(JS|VST)\s+("([^"]*)"|\S+)', head)
    return (m.group(3) or m.group(2)) if m else head


def copy(lines, tpl, spec):
    dst, rest = spec.split('=', 1)
    src, fxs = rest.split(':', 1)
    after = None
    if '@' in fxs: fxs, after = fxs.split('@', 1)
    ts, te = chain(tpl, src); tents = entries(tpl, ts, te)
    picked = sorted((pick(tents, f, f'шаблон {src}') for f in fxs.split(',') if f), key=lambda x: x[0])
    cs, ce = chain(lines, dst); dents = entries(lines, cs, ce)
    if after: pos = pick(dents, after, dst)[1]
    else: pos = dents[0][0] if dents else ce
    shift = (indent(lines[cs]) - indent(tpl[ts]))
    new = []
    for s, e, head in picked:
        for l in tpl[s:e]:
            l = ' ' * (indent(l) + shift) + l.lstrip(' ') if l.strip() else l
            if l.strip().startswith('FXID '): l = l[:indent(l)] + 'FXID {' + str(uuid.uuid4()).upper() + '}'
            new.append(l)
        print(f'copy\t{dst}\t{short(head)}\tиз {src}{" после " + after if after else ""}')
    lines[pos:pos] = new
    # цепочка трека включена
    if dst == 'master':
        k = next((i for i, l in enumerate(lines) if indent(l) == 2 and l.strip().startswith('MASTER_FX ')), None)
        key, ind = 'MASTER_FX', 2
    else:
        _, s, e = find_track(lines, dst)
        k = next((i for i in range(s, e) if indent(lines[i]) == indent(lines[s]) + 2 and lines[i].strip().startswith('FX ')), None)
        key, ind = 'FX', indent(lines[s]) + 2
    if k is not None and lines[k].split()[1] != '1':
        print(f'fx_on\t{dst}\t{lines[k].strip()} -> {key} 1')
        lines[k] = ' ' * ind + f'{key} 1'


def bypass(lines, spec):
    tr, sub = spec.split(':', 1)
    cs, ce = chain(lines, tr)
    s, _, head = pick(entries(lines, cs, ce), sub, tr)
    tok = lines[s].split(); tok[1] = '1'
    print(f'bypass\t{tr}\t{short(head)}')
    lines[s] = ' ' * indent(lines[s]) + ' '.join(tok)


def isbus(lines, s, e):
    k = next(i for i in range(s, e) if indent(lines[i]) == indent(lines[s]) + 2 and lines[i].strip().startswith('ISBUS '))
    return k, int(lines[k].split()[2])


def drop(lines, name):
    _, s, e = find_track(lines, name)
    _, d = isbus(lines, s, e)
    if d > 0: raise ValueError(f'{name!r} - папка с треками внутри, не удаляю')
    if d:
        prev = [t for t in tracks(lines) if t[2] < s]
        if not prev: raise ValueError(f'{name!r} закрывает папку, а трека перед ним нет')
        k, pd = isbus(lines, prev[-1][1], prev[-1][2])
        nd = pd + d
        lines[k] = ' ' * indent(lines[k]) + f'ISBUS {1 if nd > 0 else 2 if nd < 0 else 0} {nd}'
        print(f'isbus\t{prev[-1][0]}\t{pd} -> {nd}')
    del lines[s:e + 1]
    print(f'drop\t{name}')


def header(lines, tpl, keys):
    for key in keys.split(','):
        def find(ls):
            return next((i for i, l in enumerate(ls) if indent(l) == 2 and l.strip().split(' ', 1)[0] == key), None)
        i, j = find(lines), find(tpl)
        if j is None: raise ValueError(f'в шаблоне нет {key}')
        if i is None: raise ValueError(f'в проекте нет {key}')
        if lines[i] != tpl[j]: print(f'header\t{lines[i].strip()} -> {tpl[j].strip()}')
        lines[i] = tpl[j]


def rename(lines, spec):
    old, new = spec.split('=', 1)
    _, s, e = find_track(lines, old)
    k = next(i for i in range(s, e) if indent(lines[i]) == indent(lines[s]) + 2 and lines[i].strip().startswith('NAME '))
    lines[k] = ' ' * indent(lines[k]) + 'NAME ' + (f'"{new}"' if ' ' in new else new)
    print(f'name\t{old} -> {new}')


def new_id(): return '{' + str(uuid.uuid4()).upper() + '}'


def item(lines, spec):
    tr, rest = spec.split('=', 1)
    f, rng = rest.rsplit('@', 1)
    parts = rng.split(',')
    soffs, length = (float(v) for v in parts[0].split('+'))
    fi, fo = (float(parts[1]) if len(parts) > 1 else 0.01), (float(parts[2]) if len(parts) > 2 else 0.01)
    iid = max([int(l.split()[1]) for l in lines if l.strip().startswith('IID ')] + [0]) + 1
    _, s, e = find_track(lines, tr)
    ind = ' ' * (indent(lines[s]) + 2)
    name = f.replace('\\', '/').split('/')[-1]
    block = ['<ITEM', '  POSITION 0', '  SNAPOFFS 0', f'  LENGTH {length:g}', '  LOOP 0', '  ALLTAKES 0',
             f'  FADEIN 1 {fi:g} 0 1 0 0 0', f'  FADEOUT 1 {fo:g} 0 1 0 0 0', '  MUTE 0 0', '  SEL 0', f'  IGUID {new_id()}',
             f'  IID {iid}', f'  NAME "{name}"', '  VOLPAN 1 0 1 -1', f'  SOFFS {soffs:g}', '  PLAYRATE 1 1 0 -1 0 0.0025',
             '  CHANMODE 0', f'  GUID {new_id()}', '  <SOURCE WAVE', f'    FILE "{f}"', '  >', '>']
    lines[e:e] = [ind + l for l in block]
    print(f'item\t{tr}\t{f}\tSOFFS {soffs:g} LENGTH {length:g}')


def wav_seconds(path):
    """Длина WAV по заголовку (fmt и data), в том числе 32 bit float - модуль wave его не читает."""
    import struct
    with open(path, 'rb') as f:
        if f.read(12)[8:12] != b'WAVE': raise ValueError(f'{path}: не WAV')
        rate = align = None
        while True:
            h = f.read(8)
            if len(h) < 8: raise ValueError(f'{path}: нет data')
            cid, size = h[:4], struct.unpack('<I', h[4:])[0]
            if cid == b'fmt ':
                fmt = f.read(size); rate, align = struct.unpack('<I', fmt[4:8])[0], struct.unpack('<H', fmt[12:14])[0]
            elif cid == b'data':
                return size / (rate * align)
            else:
                f.seek(size + (size & 1), 1)


def untrim(lines, root):
    """Айтемы WAVE каждого трека - по одному на файл, на весь файл с позиции 0, фейды 10 мс; громкость айтема остаётся.
    MIDI и прочие айтемы не трогаются. Дубли одного прохода выравниваются друг с другом, таймлайн сдвигается на SOFFS."""
    for name, s, e in reversed(tracks(lines)):
        seen, i = set(), s
        while i <= e:
            if lines[i].strip() != '<ITEM' or indent(lines[i]) != indent(lines[s]) + 2: i += 1; continue
            ie = block_end(lines, i)
            f = next((unquote(l.strip()[5:]) for l in lines[i:ie] if l.strip().startswith('FILE ')), None)
            wave = any(l.strip() == '<SOURCE WAVE' for l in lines[i:ie])
            if not (f and wave): i = ie + 1; continue
            if f in seen:
                del lines[i:ie + 1]; e -= ie + 1 - i; continue
            seen.add(f)
            dur = wav_seconds(os.path.join(root, f.replace('\\', '/')))
            ind = ' ' * (indent(lines[i]) + 2)
            for j in range(i + 1, ie):
                k = lines[j].strip().split(' ', 1)[0]
                if indent(lines[j]) != len(ind): continue
                if k in ('POSITION', 'SOFFS', 'SNAPOFFS'): lines[j] = f'{ind}{k} 0'
                elif k == 'LENGTH': lines[j] = f'{ind}LENGTH {dur:g}'
                elif k in ('FADEIN', 'FADEOUT'):
                    p = lines[j].split(); p[2] = '0.01'; lines[j] = ind + ' '.join(p)
            print(f'untrim\t{name}\t{f}\t{dur:g} с')
            i = ie + 1


def wave_items(lines, s, e):
    """[(начало, конец блока)] айтемов WAVE трека."""
    out, i = [], s
    while i <= e:
        if lines[i].strip() == '<ITEM' and indent(lines[i]) == indent(lines[s]) + 2:
            ie = block_end(lines, i)
            if any(l.strip() == '<SOURCE WAVE' for l in lines[i:ie]): out.append((i, ie))
            i = ie + 1
        else: i += 1
    return out


def field(lines, i, ie, key):
    """Индекс строки поля айтема и его значения (токены после ключа)."""
    ind = indent(lines[i]) + 2
    for j in range(i + 1, ie):
        p = lines[j].split()
        if indent(lines[j]) == ind and p and p[0] == key: return j, p[1:]
    return None, None


def trim(lines, spec):
    """Границы трека во времени файла: 'ТРЕК=S0-S1[,FO]'. Первому айтему SOFFS = S0 (POSITION и LENGTH сдвигаются - звук
    остаётся на том же месте таймлайна), последнему LENGTH до S1 и фейд FO. Середина (врезки) не трогается."""
    tr, rest = spec.split('=', 1)
    rng, *fo = rest.split(',')
    s0, s1 = (float(v) for v in rng.split('-'))
    _, s, e = find_track(lines, tr)
    its = wave_items(lines, s, e)
    if not its: raise ValueError(f'{tr}: нет айтемов WAVE')
    def num(i, ie, k): return float(field(lines, i, ie, k)[1][0])
    first = min(its, key=lambda b: num(*b, 'SOFFS') if field(lines, *b, 'SOFFS')[0] else 0)
    last = max(its, key=lambda b: (num(*b, 'SOFFS') if field(lines, *b, 'SOFFS')[0] else 0) + num(*b, 'LENGTH'))
    def put(i, ie, k, v):
        j, p = field(lines, i, ie, k)
        if j is None: raise ValueError(f'{tr}: у айтема нет {k}')
        lines[j] = ' ' * indent(lines[j]) + ' '.join([k, v] + p[1:])
    so = num(*first, 'SOFFS'); d = s0 - so
    pos, ln = num(*first, 'POSITION') + d, num(*first, 'LENGTH') - d
    if pos < 0 or ln <= 0: raise ValueError(f'{tr}: начало {s0:g} - айтем вышел бы за 0 таймлайна или в ноль длины')
    put(*first, 'POSITION', f'{pos:.6f}'); put(*first, 'LENGTH', f'{ln:.6f}'); put(*first, 'SOFFS', f'{s0:.6f}')
    ln_last = s1 - num(*last, 'SOFFS')
    if ln_last <= 0: raise ValueError(f'{tr}: конец {s1:g} раньше начала последнего айтема')
    put(*last, 'LENGTH', f'{ln_last:.6f}')
    if fo:
        j, p = field(lines, *last, 'FADEOUT')
        if j is None:   # строки нет - вставить после LENGTH
            jl, _ = field(lines, *last, 'LENGTH')
            lines.insert(jl + 1, ' ' * indent(lines[jl]) + f'FADEOUT 1 {float(fo[0]):g} 0 1 0 0 0')
        else:
            p[1] = f'{float(fo[0]):g}'; lines[j] = ' ' * indent(lines[j]) + ' '.join(['FADEOUT'] + p)
    print(f'trim\t{tr}\t{s0:g}-{s1:g}' + (f'\tfade out {float(fo[0]):g}' if fo else ''))


def marker(lines, spec):
    """Маркер в шапке проекта, перед первым треком; номера по порядку времени."""
    pos, name = spec.split('=', 1)
    ms = [(float(l.split()[2]), l) for l in lines if l.startswith('  MARKER ')]
    first = next(i for i, l in enumerate(lines) if l.startswith('  <TRACK') or l.startswith('  MARKER '))
    rest = [i for i, l in enumerate(lines) if l.startswith('  MARKER ')]
    for i in reversed(rest): del lines[i]
    ms.append((float(pos), f'  MARKER 0 {float(pos):g} "{name}" 0 0 1 R'))   # как в abproj.py, проверено в REAPER
    ms.sort(key=lambda m: m[0])
    out = []
    for n, (_, l) in enumerate(ms):
        tok = l.strip().split(' '); tok[1] = str(n + 1)   # MARKER <номер> <позиция> "имя" ...
        out.append('  ' + ' '.join(tok))
    lines[first:first] = out
    print(f'marker\t{float(pos):g}\t{name}')


def addjs(lines, spec):
    tr, rest = spec.split('=', 1)
    after = None
    if '@' in rest: rest, after = rest.rsplit('@', 1)
    js, params = rest.split(':', 1)
    tok = params.split()
    if len(tok) > 64: raise ValueError(f'{js}: параметров больше 64')
    cs, ce = chain(lines, tr); ents = entries(lines, cs, ce)
    pos = pick(ents, after, tr)[1] if after else (ents[0][0] if ents else ce)
    ind = ' ' * (indent(lines[cs]) + 2)
    block = ['BYPASS 0 0 0', f'<JS {js} ""', '  ' + ' '.join(tok + ['-'] * (64 - len(tok))), '>', 'FLOATPOS 0 0 0 0',
             f'FXID {new_id()}', 'WAK 0 0']
    lines[pos:pos] = [ind + l for l in block]
    print(f'addjs\t{tr}\t{js}\t{" ".join(tok)}{" после " + after if after else ""}')


def check(lines):
    """Блоки сходятся, параметры JSFX - 64 токена."""
    depth = 0
    for i, l in enumerate(lines):
        t = l.strip()
        if t.startswith('<'): depth += 1
        elif t == '>': depth -= 1
        if t.startswith('<JS '):
            n = len(shlex.split(lines[i + 1]))   # строковый слайдер в кавычках с пробелами - один токен (amp-model)
            if n != 64: raise ValueError(f'{t}: {n} токенов вместо 64')
    if depth: raise ValueError(f'блоки не сходятся: {depth:+d}')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('rpp'); ap.add_argument('template'); ap.add_argument('-o', '--out')
    ap.add_argument('--copy', action='append', default=[]); ap.add_argument('--bypass', action='append', default=[])
    ap.add_argument('--drop', action='append', default=[]); ap.add_argument('--header', action='append', default=[])
    ap.add_argument('--name', action='append', default=[]); ap.add_argument('--item', action='append', default=[])
    ap.add_argument('--addjs', action='append', default=[])
    ap.add_argument('--untrim', action='store_true'); ap.add_argument('--marker', action='append', default=[])
    ap.add_argument('--trim', action='append', default=[])
    a = ap.parse_args(argv)
    lines, tpl = read(a.rpp), read(a.template)
    try:
        for h in a.header: header(lines, tpl, h)
        for d in a.drop: drop(lines, d)
        for n in a.name: rename(lines, n)
        for it in a.item: item(lines, it)
        for c in a.copy: copy(lines, tpl, c)
        for j in a.addjs: addjs(lines, j)
        for b in a.bypass: bypass(lines, b)
        if a.untrim: untrim(lines, os.path.dirname(os.path.abspath(a.rpp)))
        for t in a.trim: trim(lines, t)
        for mk in a.marker: marker(lines, mk)
        check(lines)
    except ValueError as e:
        print(f'ошибка: {e}', file=sys.stderr); return 1
    with open(a.out or a.rpp, 'wb') as f: f.write('\r\n'.join(lines).encode('utf-8'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
