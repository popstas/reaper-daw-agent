import re
from conftest import run, save_calib, edit_rpp_master_threshold, edit_rpp


def test_track_offsets_applied(project):
    _, js0 = run(project, '--no-calib')
    save_calib(project, tracks={'mic': 1.0}, master=0.4)        # key = freezelib.calib_key(текущий .rpp)
    out, js = run(project)
    assert abs(js['tracks']['mic']['lufs'] - js0['tracks']['mic']['lufs'] - 1.0) < 0.05
    assert abs(js['pred'] - js['master_out'] - 0.4) < 1e-6
    assert 'поправка' in out and 'рендер ≈' in out


def test_calib_survives_fader_edit(project):
    save_calib(project, tracks={'mic': 1.0}, master=0.4)
    edit_rpp(project, 'VOLPAN 1 0 -1 -1 1', 'VOLPAN 0.5 0 -1 -1 1')
    out, js = run(project)
    assert 'устарела' not in out and abs(js['pred'] - js['master_out'] - 0.4) < 1e-6


def test_calib_stale(project):
    save_calib(project, tracks={'mic': 1.0}, master=0.4, key='old')
    out, js = run(project)
    assert 'поправка устарела' in out and abs(js['pred'] - js['master_out'] - 0.5) < 1e-6


def test_master_null_defaults(project):
    save_calib(project, tracks={'mic': 1.0}, master=None)
    _, js = run(project)
    assert abs(js['pred'] - js['master_out'] - 0.5) < 1e-6


def test_no_calib_flag(project):
    save_calib(project, tracks={'mic': 1.0}, master=0.4)
    _, js = run(project, '--no-calib'); _, js0 = run(project, '--no-calib')
    assert js['tracks']['mic'] == js0['tracks']['mic']
    assert abs(js['pred'] - js['master_out'] - 0.5) < 1e-6


def test_target_hits(project):
    out, js = run(project, '--target', '-14')
    m = re.search(r'порог лимитера под -14.0 LUFS: (-?[\d.]+)', out); assert m, out
    edit_rpp_master_threshold(project, float(m[1]))
    _, js2 = run(project)
    assert abs(js2['pred'] - (-14)) <= 0.1


def test_target_unreachable(project):
    out, _ = run(project, '--target', '0')
    assert 'цель недостижима: при пороге -30 прогноз' in out
    out, _ = run(project, '--target', '-60')
    assert 'цель недостижима: при пороге 0 прогноз' in out


def test_target_no_limiter(project):
    edit_rpp(project, '<JS loser/MGA_JSLimiterST', '<JS loser/other_limiter')
    out, _ = run(project, '--target', '-14')
    assert 'нет MGA_JSLimiterST на мастере' in out
