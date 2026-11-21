from freezelib import (split_tracks, track_fx, kind_of, freeze_point, track_key, plan, freeze_status,
                       save_json, calib_key, master_fx, MODELED, MINOR)


def test_fx_blocks_keep_vst_state(rpp_text):
    g = track_fx(split_tracks(rpp_text)[0]['text'])
    assert [f['kind'] for f in g] == ['JS', 'JS', 'JS', 'VST3', 'JS', 'VST']
    assert g[3]['p'] == [] and g[3]['text'].count('\n') >= 3   # base64 состояние внутри
    assert g[1]['name'] == 'sstillwell/hpflpf' and g[1]['p'][0] == '80'


def test_master_fx(rpp_text):
    m = master_fx(rpp_text)
    assert [(f['name'], f['bypass']) for f in m] == [('sstillwell/1175', True), ('loser/MGA_JSLimiterST', False)]
    assert m[1]['p'][:4] == ['-8', '200', '75', '-1.4']


def test_kind_and_point(rpp_text):
    t = split_tracks(rpp_text)
    assert [kind_of(f) for f in track_fx(t[0]['text'])] == ['model', 'model', 'model', 'trigger', 'model', 'minor']
    assert freeze_point(track_fx(t[0]['text'])) == 3          # после Blue Cat
    assert freeze_point(track_fx(t[1]['text'])) == 0          # MT-PowerDrumKit, дальше ничего моделируемого
    assert freeze_point(track_fx(t[2]['text'])) is None       # mic


def test_bypassed_trigger_ignored(rpp_text):
    txt = split_tracks(rpp_text)[0]['text'].replace('BYPASS 0 0 0\n      <VST "VST3', 'BYPASS 1 0 0\n      <VST "VST3')
    assert freeze_point(track_fx(txt)) is None


def test_unknown_js_triggers(rpp_text):
    txt = split_tracks(rpp_text)[2]['text'].replace('<JS Liteon/deesser', '<JS someone/fancy_comp')
    assert freeze_point(track_fx(txt)) == 2


def test_key_ignores_after_point_and_volatile(rpp_text):
    t = split_tracks(rpp_text)[0]; fx = track_fx(t['text']); k = track_key(t['text'], fx, 3)
    after = t['text'].replace('-14 5 0 20 250 100', '-10 5 0 20 250 100')     # 1175 после точки
    vol = t['text'].replace('VOLPAN 0.70794578', 'VOLPAN 0.5')                # фейдер трека
    sel = t['text'].replace('SEL 0', 'SEL 1')
    for txt in (after, vol, sel):
        assert track_key(txt, track_fx(txt), 3) == k


def test_key_changes_before_point(rpp_text):
    t = split_tracks(rpp_text)[0]; fx = track_fx(t['text']); k = track_key(t['text'], fx, 3)
    for old, new in [('80 10000 -2', '80 10000 -5'), ('SOFFS 7.5', 'SOFFS 8'), ('AAAA', 'AAAB'), ('\n    FX 1\n', '\n    FX 0\n')]:
        txt = t['text'].replace(old, new)
        assert track_key(txt, track_fx(txt), 3) != k


def test_plan_and_file_names(rpp_text):
    p = plan(rpp_text)
    assert [(e['index'], e['name'], e['point'], e['file']) for e in p] == [(0, 'guitar', 3, 'freeze/01.wav'), (1, 'drums', 0, 'freeze/02.wav')]
    assert 'Blue Cat' in p[0]['after']


def test_plan_skips_muted_and_fx_off(rpp_text):
    t = rpp_text.replace('NAME drums\r\n    VOLPAN 1.41253754 0 -1 -1 1\r\n    MUTESOLO 0', 'NAME drums\r\n    VOLPAN 1.41253754 0 -1 -1 1\r\n    MUTESOLO 1')
    assert [e['name'] for e in plan(t)] == ['guitar']
    t = rpp_text.replace('NAME guitar\r\n    VOLPAN 0.70794578 0 -1 -1 1\r\n    MUTESOLO 0 0 0\r\n    SEL 0\r\n    FX 1', 'NAME guitar\r\n    VOLPAN 0.70794578 0 -1 -1 1\r\n    MUTESOLO 0 0 0\r\n    SEL 0\r\n    FX 0')
    assert [e['name'] for e in plan(t)] == ['drums']


def test_status_renamed_track(tmp_path, rpp_text):
    e = plan(rpp_text)[0]; (tmp_path / 'freeze').mkdir(); (tmp_path / e['file']).write_bytes(b'x')
    save_json(str(tmp_path / 'freeze'), 'freeze.json', {'tracks': {'0': dict(e, name='gtr')}})
    assert freeze_status(str(tmp_path), e) == 'stale'
    assert freeze_status(str(tmp_path), dict(e, index=5)) == 'missing'
    save_json(str(tmp_path / 'freeze'), 'freeze.json', {'tracks': {'0': e}})
    assert freeze_status(str(tmp_path), e) == 'ok'
    (tmp_path / e['file']).unlink()
    assert freeze_status(str(tmp_path), e) == 'missing'


def test_calib_key_minor_fx_only(rpp_text):
    k = calib_key(rpp_text)
    assert calib_key(rpp_text.replace('-14 5 0 20 250 100', '-10 5 0 20 250 100')) == k     # JSFX
    assert calib_key(rpp_text.replace('VOLPAN 1 0 -1 -1 1', 'VOLPAN 0.5 0 -1 -1 1')) == k  # фейдер
    assert calib_key(rpp_text.replace('BYPASS 1 0 0\r\n      <VST "VST: ReaVerb', 'BYPASS 0 0 0\r\n      <VST "VST: ReaVerb')) != k
    assert calib_key(rpp_text.replace('AAAA', 'AAAB')) != k                                  # заморозка


def test_sets():
    assert MODELED == frozenset({'sstillwell/hpflpf', 'sstillwell/rbj4eq', 'sstillwell/1175', 'Liteon/presenceeq',
                                 'popstas/guitar_noise_gate.jsfx', 'loser/MGA_JSLimiterST'})
    assert MINOR == ('ReaVerb', 'Liteon/deesser')


def test_find_rpp_skips_variant_copies(tmp_path):
    import os, time
    from freezelib import find_rpp
    (tmp_path / 'song.rpp').write_text('x'); time.sleep(0.01)
    (tmp_path / 'zz-variant-1.rpp').write_text('x')
    assert os.path.basename(find_rpp(str(tmp_path))) == 'song.rpp'


def test_wav_seconds_float(tmp_path):
    import numpy as np, soundfile as sf
    from freezelib import wav_seconds
    sf.write(tmp_path / 'a.wav', np.zeros((48000 * 3, 2), np.float32), 48000, subtype='FLOAT')
    assert abs(wav_seconds(str(tmp_path / 'a.wav')) - 3.0) < 1e-6


def test_cli_todo_and_save(project):
    import subprocess, sys, os
    from conftest import SKILL, pink, write_freeze
    cli = [sys.executable, os.path.join(SKILL, 'freezelib.py')]
    r = subprocess.run(cli + ['todo', project], capture_output=True, text=True)
    assert [l.split('\t')[:3] for l in r.stdout.splitlines()] == [['0', '3', '0'], ['1', '0', '0']]
    from freezelib import plan
    from conftest import rpp
    assert [l.split('\t')[5] for l in r.stdout.splitlines()] == [e['key'] for e in plan(rpp(project))]
    write_freeze(project, 0, pink(-14))
    r = subprocess.run(cli + ['todo', project], capture_output=True, text=True)
    assert [l.split('\t')[:3] for l in r.stdout.splitlines()] == [['0', '3', '1'], ['1', '0', '0']]
    import soundfile as sf, numpy as np
    sf.write(os.path.join(project, 'freeze', '02.wav'), np.full((48000 * 61, 2), 0.1, np.float32), 48000, subtype='FLOAT')
    r = subprocess.run(cli + ['save', project, '1'], capture_output=True, text=True)
    assert r.returncode == 0 and 'заморожено: drums после MT-PowerDrumKit' in r.stdout and '1:01' in r.stdout
    r = subprocess.run(cli + ['todo', project], capture_output=True, text=True)
    assert [l.split('\t')[2] for l in r.stdout.splitlines()] == ['1', '1']


def test_save_refuses_silent_stem(project):
    import subprocess, sys, os, json
    import numpy as np, soundfile as sf
    from conftest import SKILL
    os.makedirs(os.path.join(project, 'freeze'), exist_ok=True)
    sf.write(os.path.join(project, 'freeze', '02.wav'), np.zeros((48000, 2), np.float32), 48000, subtype='FLOAT')
    x = np.zeros((48000, 2), np.float32); x[100, 0] = 0.5
    sf.write(os.path.join(project, 'freeze', '01.wav'), x, 48000, subtype='FLOAT')
    r = subprocess.run([sys.executable, os.path.join(SKILL, 'freezelib.py'), 'save', project, '0', '1'], capture_output=True, text=True)
    assert r.returncode != 0 and 'тишина' in r.stdout + r.stderr and 'drums' in r.stdout + r.stderr
    tracks = json.load(open(os.path.join(project, 'freeze', 'freeze.json')))['tracks']
    assert list(tracks) == ['0']                              # guitar сохранена, тихий drums - нет
    assert not os.path.exists(os.path.join(project, 'freeze', '02.wav'))
