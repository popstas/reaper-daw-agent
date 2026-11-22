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
