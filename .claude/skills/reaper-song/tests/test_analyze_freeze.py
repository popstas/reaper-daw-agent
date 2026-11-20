import analyze, freezelib
from conftest import pink, write_freeze, run, copy_project, edit_rpp


def test_modeled_set_matches():
    assert set(analyze.FX) == freezelib.MODELED


def test_frozen_guitar_uses_wav(project):
    write_freeze(project, 0, pink(-14))            # «выход Blue Cat» на 6 dB громче сырого
    out, js = run(project)
    assert 'заморожено после' in out and 'Blue Cat' in out
    assert 'не моделируется: VST3' not in out.split('## mic')[0]
    out0, js0 = run(copy_project(project))
    assert js['tracks']['guitar']['lufs'] > js0['tracks']['guitar']['lufs'] + 3
    assert 'нет заморозки - freeze.sh' in out0
    assert js['master_out'] > js['master_in'] - 20


def test_stale_freeze_reported(project):
    write_freeze(project, 0, pink(-14)); edit_rpp(project, '80 10000 -2', '80 10000 -5')
    out, js = run(project)
    assert 'заморозка устарела' in out and 'freeze.sh' in out
    assert 'не моделируется: VST3' in out


def test_midi_drums_enter_model(project):
    out0, js0 = run(project)
    assert 'drums' not in js0['tracks'] and 'нет заморозки - freeze.sh' in out0.split('## mic')[0].split('## drums')[1]
    write_freeze(project, 1, pink(-16))
    out, js = run(project)
    assert 'drums' in js['tracks'] and 'MT-PowerDrumKit' in out


def test_freeze_length_mismatch(project):
    write_freeze(project, 0, pink(-14, seconds=4))   # проект 6 с
    write_freeze(project, 1, pink(-16, seconds=9))
    out, js = run(project)
    assert js['master_out'] > -70


def test_short_term_fast_matches_pyloudnorm():
    import numpy as np, pyloudnorm as pyln
    x = np.concatenate([pink(-20, seconds=6), pink(-30, seconds=6, seed=3)])
    st = analyze.short_term(x)
    m = pyln.Meter(analyze.SR)
    for i in (0, 2, 7):
        assert abs(st[i] - m.integrated_loudness(x[i * analyze.SR:(i + 3) * analyze.SR])) < 0.3


def test_fast_lufs_matches_pyloudnorm():
    import numpy as np, pyloudnorm as pyln
    m = pyln.Meter(analyze.SR)
    quiet = np.concatenate([pink(-20, seconds=5), pink(-45, seconds=5, seed=3), pink(-80, seconds=3, seed=5)])
    for x in (pink(-20), pink(-14, seconds=9), quiet):
        assert abs(analyze.lufs_fast(x) - m.integrated_loudness(x)) < 0.005
    assert analyze.lufs_fast(np.zeros((analyze.SR, 2))) == -99.0
