import os, subprocess, sys
from conftest import SKILL, RPP

CHAIN = os.path.join(SKILL, 'chain.py')

# старый проект: папка guitar (ReaVerb) с детьми "guitar 1" (айтем, пустая цепочка, FX 0) и "guitar 2" (пустой, закрывает папку),
# мастер с ReaComp и анализатором
OLD = '''<REAPER_PROJECT 0.1 "7.81/win64" 1763700000
  RENDER_PATTERN "$project - 0 - старое"
  TIMELOCKMODE 1
  SAMPLERATE 44100 0 0
  MASTER_FX 1
  <MASTERFXLIST
    WNDRECT 0 0 1 1
    SHOW 0
    LASTSEL 0
    DOCKED 0
    BYPASS 0 0 0
    <VST "VST: ReaComp (Cockos)" reacomp.dll 0 "" 1919247213<5653547265636D726561636F6D700000> ""
      bWNlcu5e7f4AAAAAAgAAAAEAAAAAAAAAAgAAAAAAAAA=
    >
    FLOATPOS 0 0 0 0
    FXID {00000000-0000-0000-0000-00000000A001}
    WAK 0 0
    BYPASS 0 0 0
    <JS analysis/loudness_meter ""
      0 - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    >
    FLOATPOS 0 0 0 0
    FXID {00000000-0000-0000-0000-00000000A002}
    WAK 0 0
  >
  <TRACK {00000000-0000-0000-0000-00000000B000}
    NAME guitar
    ISBUS 1 1
    FX 1
    <FXCHAIN
      SHOW 0
      LASTSEL 0
      DOCKED 0
    >
  >
  <TRACK {00000000-0000-0000-0000-00000000C000}
    NAME "guitar 1"
    ISBUS 0 0
    FX 0
    <FXCHAIN
      SHOW 0
      LASTSEL 0
      DOCKED 0
    >
    <ITEM
      POSITION 0
      <SOURCE WAVE
        FILE "g.wav"
      >
    >
  >
  <TRACK {00000000-0000-0000-0000-00000000D000}
    NAME "guitar 2"
    ISBUS 2 -1
    FX 0
    <FXCHAIN
      SHOW 0
      LASTSEL 0
      DOCKED 0
    >
  >
>
'''.replace('\n', '\r\n')

TPL = RPP.replace('  SAMPLERATE 48000 0 0', '  SAMPLERATE 48000 1 1\r\n  TIMELOCKMODE 0\r\n  RENDER_PATTERN $project')


def run(tmp_path, *args):
    (tmp_path / 'old.rpp').write_bytes(OLD.encode())
    (tmp_path / 'tpl.rpp').write_bytes(TPL.encode())
    r = subprocess.run([sys.executable, CHAIN, str(tmp_path / 'old.rpp'), str(tmp_path / 'tpl.rpp'), '-o', str(tmp_path / 'new.rpp'), *args],
                       capture_output=True, text=True)
    out = (tmp_path / 'new.rpp').read_bytes().decode() if (tmp_path / 'new.rpp').exists() else ''
    return r, out


def test_copy_into_empty_chain_enables_fx(tmp_path):
    r, out = run(tmp_path, '--copy', 'guitar 1=guitar:hpflpf,1175,rbj4eq')
    assert r.returncode == 0, r.stderr
    tr = out[out.index('NAME "guitar 1"'):out.index('NAME "guitar 2"')]
    # порядок шаблона, параметры как в шаблоне, отступ трека, цепочка включена
    assert tr.index('<JS sstillwell/hpflpf') < tr.index('<JS sstillwell/rbj4eq') < tr.index('<JS sstillwell/1175')
    assert '        80 10000 -2 -' in tr and '    FX 1\r\n' in tr
    assert '{00000000-0000-0000-0000-000000001002}' not in out  # FXID новые
    assert '\r\n' in out and '\n' not in out.replace('\r\n', '')


def test_master_after_and_bypass(tmp_path):
    r, out = run(tmp_path, '--copy', 'master=master:MGA_JSLimiterST@ReaComp', '--bypass', 'master:ReaComp')
    assert r.returncode == 0, r.stderr
    m = out[out.index('<MASTERFXLIST'):out.index('<TRACK')]
    assert m.index('ReaComp') < m.index('MGA_JSLimiterST') < m.index('loudness_meter')
    assert m.split('<VST "VST: ReaComp')[0].rstrip().endswith('BYPASS 1 0 0')


def test_drop_closing_track_moves_depth(tmp_path):
    r, out = run(tmp_path, '--drop', 'guitar 2')
    assert r.returncode == 0, r.stderr
    assert 'guitar 2' not in out
    tr = out[out.index('NAME "guitar 1"'):]
    assert 'ISBUS 2 -1' in tr


def test_drop_folder_refused(tmp_path):
    r, _ = run(tmp_path, '--drop', 'guitar')
    assert r.returncode == 1 and 'папка' in r.stderr


def test_header_from_template(tmp_path):
    r, out = run(tmp_path, '--header', 'TIMELOCKMODE,SAMPLERATE,RENDER_PATTERN')
    assert r.returncode == 0, r.stderr
    assert '  TIMELOCKMODE 0\r\n' in out and '  SAMPLERATE 48000 1 1\r\n' in out and '  RENDER_PATTERN $project\r\n' in out


def test_ambiguous_fx_refused(tmp_path):
    r, _ = run(tmp_path, '--copy', 'guitar 1=guitar:sstillwell')
    assert r.returncode == 1 and 'найдено' in r.stderr


def test_rename_item_addjs(tmp_path):
    r, out = run(tmp_path, '--drop', 'guitar 2', '--drop', 'guitar 1', '--name', 'guitar=room mic',
                 '--item', 'room mic=x_RAW.WAV@154.6+173.9,0.2,0.5', '--addjs', 'room mic=popstas/ms_decode.jsfx:70 0')
    assert r.returncode == 0, r.stderr
    assert 'NAME "room mic"' in out and 'ISBUS 0 0' in out
    tr = out[out.index('NAME "room mic"'):]
    assert 'SOFFS 154.6' in tr and 'LENGTH 173.9' in tr and 'FADEIN 1 0.2 ' in tr and 'FILE "x_RAW.WAV"' in tr
    js = tr[tr.index('<JS popstas/ms_decode.jsfx'):].split('\r\n')[1].split()
    assert js[:3] == ['70', '0', '-'] and len(js) == 64


def wav_float(path, sec, sr=48000, ch=2):
    """WAV 32 bit float (format 3) нулями: длина берётся из заголовка."""
    import struct
    n = int(sec * sr); data = b'\0' * (n * ch * 4)
    fmt = struct.pack('<HHIIHH', 3, ch, sr, sr * ch * 4, ch * 4, 32)
    body = b'WAVE' + b'fmt ' + struct.pack('<I', len(fmt)) + fmt + b'data' + struct.pack('<I', len(data)) + data
    path.write_bytes(b'RIFF' + struct.pack('<I', len(body)) + body)


TRIMMED = '''<REAPER_PROJECT 0.1 "7.85/win64" 1763700000
  TIMELOCKMODE 0
  <TRACK {00000000-0000-0000-0000-00000000E000}
    NAME mic
    <ITEM
      POSITION 13.5
      LENGTH 50
      FADEIN 1 0.01 0 1 0 0 0 1 0 0 1 0 0
      FADEOUT 1 0.9 0 1 0 0 0 1 0 0 1 0 0
      VOLPAN 0.9 0 1 -1
      SOFFS 15
      <SOURCE WAVE
        FILE "Media\\m.wav"
      >
    >
    <ITEM
      POSITION 70
      LENGTH 5
      SOFFS 80
      <SOURCE WAVE
        FILE "Media\\m.wav"
      >
    >
    <ITEM
      POSITION 0
      LENGTH 4
      <SOURCE MIDI
        HASDATA 1 960 QN
      >
    >
  >
>'''.replace('\n', '\r\n')


def test_untrim_and_marker(tmp_path):
    (tmp_path / 'Media').mkdir(); wav_float(tmp_path / 'Media' / 'm.wav', 100.5)
    (tmp_path / 'old.rpp').write_bytes(TRIMMED.encode())
    r = subprocess.run([sys.executable, CHAIN, str(tmp_path / 'old.rpp'), str(tmp_path / 'old.rpp'), '-o', str(tmp_path / 'new.rpp'),
                        '--untrim', '--marker', '15=рез mic', '--marker', '1.5=рез гитары'], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    out = (tmp_path / 'new.rpp').read_bytes().decode()
    assert out.count('<SOURCE WAVE') == 1 and '<SOURCE MIDI' in out   # айтемы файла слиты в один, MIDI не тронут
    it = out[out.index('<ITEM'):out.index('<SOURCE WAVE')]
    assert '      POSITION 0\r\n' in it and '      SOFFS 0\r\n' in it and '      LENGTH 100.5\r\n' in it
    assert 'FADEIN 1 0.01 ' in it and 'FADEOUT 1 0.01 ' in it and 'VOLPAN 0.9 0 1 -1' in it
    hdr = out[:out.index('<TRACK')]
    assert hdr.index('MARKER 1 1.5 "рез гитары"') < hdr.index('MARKER 2 15 "рез mic"')
    assert '\n' not in out.replace('\r\n', '')


def test_trim_keeps_timeline(tmp_path):
    (tmp_path / 'old.rpp').write_bytes(TRIMMED.encode())
    run_ = lambda *a: subprocess.run([sys.executable, CHAIN, str(tmp_path / 'old.rpp'), str(tmp_path / 'old.rpp'),
                                      '-o', str(tmp_path / 'new.rpp'), *a], capture_output=True, text=True)
    r = run_('--trim', 'mic=14-84,0.3')
    assert r.returncode == 0, r.stderr
    out = (tmp_path / 'new.rpp').read_bytes().decode()
    first, second = out.split('<ITEM')[1:3]
    # начало раньше на 1 с: позиция и длина сдвигаются, звук файла остаётся на том же месте таймлайна (POSITION - SOFFS)
    assert 'POSITION 12.500000' in first and 'LENGTH 51.000000' in first and 'SOFFS 14.000000' in first
    assert 'LENGTH 4.000000' in second and 'FADEOUT 1 0.3 ' in second and 'POSITION 70\r\n' in second
    r = run_('--trim', 'mic=0-84')
    assert r.returncode == 1 and 'за 0 таймлайна' in r.stderr
