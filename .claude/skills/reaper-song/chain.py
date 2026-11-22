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

Без -o файл проекта перезаписывается. Печатает каждую правку.
"""
import argparse, re, sys, uuid


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
            n = len(lines[i + 1].split())
            if n != 64: raise ValueError(f'{t}: {n} токенов вместо 64')
    if depth: raise ValueError(f'блоки не сходятся: {depth:+d}')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('rpp'); ap.add_argument('template'); ap.add_argument('-o', '--out')
    ap.add_argument('--copy', action='append', default=[]); ap.add_argument('--bypass', action='append', default=[])
    ap.add_argument('--drop', action='append', default=[]); ap.add_argument('--header', action='append', default=[])
    ap.add_argument('--name', action='append', default=[]); ap.add_argument('--item', action='append', default=[])
    ap.add_argument('--addjs', action='append', default=[])
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
        check(lines)
    except ValueError as e:
        print(f'ошибка: {e}', file=sys.stderr); return 1
    with open(a.out or a.rpp, 'wb') as f: f.write('\r\n'.join(lines).encode('utf-8'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
