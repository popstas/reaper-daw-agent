import os, sys
import pytest

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SKILL)

# Минимальный проект: guitar (gate, hpflpf, rbj4eq, Blue Cat, 1175, ReaVerb), drums (MT-PowerDrumKit, MIDI, ReaVerb выкл),
# mic (hpflpf, 1175, deesser, ReaVerb), мастер (1175 выкл, MGA_JSLimiterST). Строки - как в настоящих .rpp REAPER 7.
RPP = '''<REAPER_PROJECT 0.1 "7.85/win64" 1763700000
  RIPPLE 0
  SAMPLERATE 48000 0 0
  RENDER_FILE C:\\rec\\2026
  <MASTERFXLIST
    WNDRECT 200 200 892 540
    SHOW 0
    LASTSEL 0
    DOCKED 0
    BYPASS 1 0 0
    <JS sstillwell/1175 ""
      -14 5 0 20 250 100 - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    >
    FLOATPOS 0 0 0 0
    FXID {00000000-0000-0000-0000-000000009001}
    WAK 0 0
    BYPASS 0 0 0
    <JS loser/MGA_JSLimiterST ""
      -8 200 75 -1.4 - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    >
    FLOATPOS 0 0 0 0
    FXID {00000000-0000-0000-0000-000000009002}
    WAK 0 0
  >
  <TRACK {00000000-0000-0000-0000-000000001000}
    NAME guitar
    VOLPAN 0.70794578 0 -1 -1 1
    MUTESOLO 0 0 0
    SEL 0
    FX 1
    TRACKID {00000000-0000-0000-0000-000000001000}
    <FXCHAIN
      WNDRECT 200 200 833 318
      SHOW 0
      LASTSEL 3
      DOCKED 0
      BYPASS 0 0 0
      <JS popstas/guitar_noise_gate.jsfx ""
        -50 -54 150 1 250 -90 801.8 10 20 -120 1 1000 -54 -58 -120 1 -42 3 60 6000 -57 -120 - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      >
      FLOATPOS 0 0 0 0
      FXID {00000000-0000-0000-0000-000000001001}
      WAK 0 0
      BYPASS 0 0 0
      <JS sstillwell/hpflpf ""
        80 10000 -2 - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      >
      FLOATPOS 0 0 0 0
      FXID {00000000-0000-0000-0000-000000001002}
      WAK 0 0
      BYPASS 0 0 0
      <JS sstillwell/rbj4eq ""
        1 0 5 -3 4 -1.5 3 1.5 - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      >
      FLOATPOS 0 0 0 0
      FXID {00000000-0000-0000-0000-000000001003}
      WAK 0 0
      BYPASS 0 0 0
      <VST "VST3: Blue Cat's Free Amp (Blue Cat Audio)" "BC Free Amp VST3.vst3" 0 "" 840268532{402C399BE94649188B8D29625BC4DA0B} ""
        9HoVMu5e7f4CAAAAAQAAAAAAAAACAAAAAAAAAAIAAAABAAAAAAAAAAIAAAAAAAAA8gYAAAEAAAAAAAAA
        4gYAAAEAAADeBgAAPD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0iVVRGLTgiPz48UHJlc2V0IHZlcnNpb249IjQiIHByb2dOYW1lPSJDbGFzc2ljIERyaXZlIC0g
        L20zPjwvbWV0YT48L3N0YXRlPjwvc2tpbj48L0dVST48L1ByZXNldD4AAAAAAAAAAAA=
        AAAAAAAA
      >
      FLOATPOS 0 0 0 0
      FXID {00000000-0000-0000-0000-000000001004}
      WAK 0 0
      BYPASS 0 0 0
      <JS sstillwell/1175 ""
        -14 5 0 20 250 100 - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      >
      FLOATPOS 0 0 0 0
      FXID {00000000-0000-0000-0000-000000001005}
      WAK 0 0
      BYPASS 0 0 0
      <VST "VST: ReaVerb (Cockos)" reaverb.dll 0 "" 1919252066<56535472657662726561766572620000> ""
        YnZlcu5e7f4CAAAAAQAAAAAAAAACAAAAAAAAAAIAAAABAAAAAAAAAAIAAAAAAAAATAAAAAEAAAAAABAA
        AFNtYWxsIHZvY2FsIHJldmVyABAAAAA=
      >
      PRESETNAME "Small vocal rever"
      FLOATPOS 0 0 0 0
      FXID {00000000-0000-0000-0000-000000001006}
      WAK 0 0
    >
    <ITEM
      POSITION 0
      SNAPOFFS 0
      LENGTH 6
      LOOP 1
      FADEIN 1 0.01 0 1 0 0 0 1 0 0 1 0 0
      FADEOUT 1 0.01 0 1 0 0 0 1 0 0 1 0 0
      MUTE 0 0
      SEL 0
      IGUID {00000000-0000-0000-0000-000000001101}
      IID 1
      NAME g.wav
      VOLPAN 1 0 1 -1
      SOFFS 7.5
      PLAYRATE 1 1 0 -1 0 0.0025
      CHANMODE 0
      GUID {00000000-0000-0000-0000-000000001102}
      <SOURCE WAVE
        FILE "Media\\g.wav"
      >
    >
  >
  <TRACK {00000000-0000-0000-0000-000000002000}
    NAME drums
    VOLPAN 1.41253754 0 -1 -1 1
    MUTESOLO 0 0 0
    SEL 1
    FX 1
    TRACKID {00000000-0000-0000-0000-000000002000}
    <FXCHAIN
      WNDRECT 0 0 1172 695
      SHOW 0
      LASTSEL 0
      DOCKED 0
      BYPASS 0 0 0
      <VST "VSTi: MT-PowerDrumKit (MANDA AUDIO) (16 out)" MT-PowerDrumKit.dll 0 "" 1297371204<5653544D5450446D74706F7765726472> ""
        RFBUTe5e7f4AAAAAEAAAAAEAAAAAAAAAAgAAAAAAAAAEAAAAAAAAAAgAAAAAAAAAEAAAAAAAAAAgAAAAAAAAAEAAAAAAAAAAgAAAAAAAAAAAAQAAAAAAAAACAAAAAAAA
        AAAQAAAA
      >
      PRESETNAME MT-PowerDrumKit
      FLOATPOS 621 518 961 648
      FXID {00000000-0000-0000-0000-000000002001}
      WAK 0 0
      BYPASS 1 0 0
      <VST "VST: ReaVerb (Cockos)" reaverb.dll 0 "" 1919252066<56535472657662726561766572620000> ""
        YnZlcu5e7f4CAAAAAQAAAAAAAAACAAAAAAAAAAIAAAABAAAAAAAAAAIAAAAAAAAATAAAAAEAAAAAABAA
        AAAQAAAA
      >
      FLOATPOS 0 0 0 0
      FXID {00000000-0000-0000-0000-000000002002}
      WAK 0 0
    >
    <ITEM
      POSITION 0
      SNAPOFFS 0
      LENGTH 6
      LOOP 1
      FADEIN 1 0 0 1 0 0 0 1 0 0 1 0 0
      FADEOUT 1 0 0 1 0 0 0 1 0 0 1 0 0
      MUTE 0 0
      SEL 0
      IGUID {00000000-0000-0000-0000-000000002101}
      IID 2
      NAME 02-drums-MIDI
      VOLPAN 1 0 1 -1
      SOFFS 0
      PLAYRATE 1 1 0 -1 0 0.0025
      CHANMODE 0
      GUID {00000000-0000-0000-0000-000000002102}
      <SOURCE MIDI
        HASDATA 1 960 QN
        CCINTERP 32
        E 5913 90 24 7f
        E 256 80 24 00
        E 0 b0 7b 00
      >
    >
  >
  <TRACK {00000000-0000-0000-0000-000000003000}
    NAME mic
    VOLPAN 1 0 -1 -1 1
    MUTESOLO 0 0 0
    SEL 0
    FX 1
    TRACKID {00000000-0000-0000-0000-000000003000}
    <FXCHAIN
      WNDRECT 200 200 833 318
      SHOW 0
      LASTSEL 0
      DOCKED 0
      BYPASS 0 0 0
      <JS sstillwell/hpflpf ""
        100 22000 -6 - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      >
      FLOATPOS 0 0 0 0
      FXID {00000000-0000-0000-0000-000000003001}
      WAK 0 0
      BYPASS 0 0 0
      <JS sstillwell/1175 ""
        -16 5 4 20 250 100 - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      >
      FLOATPOS 0 0 0 0
      FXID {00000000-0000-0000-0000-000000003002}
      WAK 0 0
      BYPASS 0 0 0
      <JS Liteon/deesser ""
        -30 6000 1 - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      >
      FLOATPOS 0 0 0 0
      FXID {00000000-0000-0000-0000-000000003003}
      WAK 0 0
      BYPASS 0 0 0
      <VST "VST: ReaVerb (Cockos)" reaverb.dll 0 "" 1919252066<56535472657662726561766572620000> ""
        YnZlcu5e7f4CAAAAAQAAAAAAAAACAAAAAAAAAAIAAAABAAAAAAAAAAIAAAAAAAAATAAAAAEAAAAAABAA
        AFNtYWxsIHZvY2FsIHJldmVyABAAAAA=
      >
      FLOATPOS 0 0 0 0
      FXID {00000000-0000-0000-0000-000000003004}
      WAK 0 0
    >
    <ITEM
      POSITION 0
      SNAPOFFS 0
      LENGTH 6
      LOOP 1
      FADEIN 1 0.01 0 1 0 0 0 1 0 0 1 0 0
      FADEOUT 1 0.01 0 1 0 0 0 1 0 0 1 0 0
      MUTE 0 0
      SEL 0
      IGUID {00000000-0000-0000-0000-000000003101}
      IID 3
      NAME m.wav
      VOLPAN 1 0 1 -1
      SOFFS 0
      PLAYRATE 1 1 0 -1 0 0.0025
      CHANMODE 0
      GUID {00000000-0000-0000-0000-000000003102}
      <SOURCE WAVE
        FILE "Media\\m.wav"
      >
    >
  >
>
'''.replace('\n', '\r\n')


@pytest.fixture
def rpp_text():
    return RPP


# ---------- проект на диске для analyze.py / variants.py ----------
import datetime, glob, json, shutil, subprocess, tempfile
import numpy as np, soundfile as sf
import freezelib

SR = 48000


def pink(rms_db, seconds=6, ch=2, seed=1):
    """Розовый шум с заданным RMS (dBFS) каждого канала."""
    rng = np.random.default_rng(seed + ch * 100 + int(seconds * 10))
    n = int(seconds * SR)
    X = np.fft.rfft(rng.standard_normal((n, ch)), axis=0)
    f = np.fft.rfftfreq(n, 1 / SR); f[0] = f[1]
    x = np.fft.irfft(X / np.sqrt(f)[:, None], n=n, axis=0)
    return x / np.sqrt(np.mean(x ** 2, axis=0)) * 10 ** (rms_db / 20)


def rpp_path(folder):
    return freezelib.find_rpp(folder)


def rpp(folder):
    with open(rpp_path(folder), encoding='utf-8', newline='') as f: return f.read()


def edit_rpp(folder, old, new):
    t = rpp(folder); assert old in t, old
    with open(rpp_path(folder), 'w', encoding='utf-8', newline='') as f: f.write(t.replace(old, new))


def edit_rpp_master_threshold(folder, thr):
    t = rpp(folder)
    i = t.index('<JS loser/MGA_JSLimiterST'); s = t.index('\n', i) + 1; e = t.index('\r\n', s)
    line = t[s:e]; ind = line[:len(line) - len(line.lstrip())]; tok = line.split(); tok[0] = f'{thr:g}'
    with open(rpp_path(folder), 'w', encoding='utf-8', newline='') as f: f.write(t[:s] + ind + ' '.join(tok) + t[e:])


def write_freeze(folder, index, signal):
    e = next(e for e in freezelib.plan(rpp(folder)) if e['index'] == index)
    os.makedirs(os.path.join(folder, 'freeze'), exist_ok=True)
    sf.write(os.path.join(folder, e['file']), signal.astype(np.float32), SR, subtype='FLOAT')
    fz = os.path.join(folder, 'freeze'); data = freezelib.load_json(fz, 'freeze.json'); data.setdefault('tracks', {})
    data['tracks'][str(index)] = dict(e, time='2026-11-21T10:00')
    freezelib.save_json(fz, 'freeze.json', data)


def copy_project(folder):
    dst = tempfile.mkdtemp(prefix='copy-', dir=os.path.dirname(folder))
    shutil.copytree(folder, dst, dirs_exist_ok=True, ignore=shutil.ignore_patterns('freeze', 'calib.json'))
    return dst


def save_calib(folder, tracks, master, key=None):
    freezelib.save_json(folder, 'calib.json', dict(key=key or freezelib.calib_key(rpp(folder)), time='2026-11-21T10:00',
                                                   tracks=tracks, master=master))


def run(folder, *args):
    fd, js = tempfile.mkstemp(suffix='.json'); os.close(fd)
    try:
        r = subprocess.run([sys.executable, os.path.join(SKILL, 'analyze.py'), folder, '--json', js, *args],
                           capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr
        with open(js, encoding='utf-8') as f: return r.stdout, json.load(f)
    finally:
        os.remove(js)


@pytest.fixture
def project(tmp_path, rpp_text):
    d = tmp_path / 'song'; (d / 'Media').mkdir(parents=True)
    (d / 'song.rpp').write_bytes(rpp_text.encode('utf-8'))
    sf.write(d / 'Media' / 'g.wav', pink(-20, seconds=13.5, ch=1).astype(np.float32), SR, subtype='FLOAT')
    sf.write(d / 'Media' / 'm.wav', pink(-18, seconds=6, ch=2, seed=7).astype(np.float32), SR, subtype='FLOAT')
    return str(d)
