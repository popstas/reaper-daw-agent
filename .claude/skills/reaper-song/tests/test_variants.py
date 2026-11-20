import glob, os, subprocess, sys
from conftest import SKILL, pink, write_freeze, rpp
from variants import check_edit

VARIANTS = os.path.join(SKILL, 'variants.py')


def test_refuse_before_point(project):
    write_freeze(project, 0, pink(-14))
    assert 'до заморозки' in check_edit(rpp(project), project, 'guitar/hpflpf:3=-5')
    assert 'render.sh --set' in check_edit(rpp(project), project, 'guitar/hpflpf:3=-5')
    assert check_edit(rpp(project), project, 'guitar/itemvol=-3') is not None
    assert check_edit(rpp(project), project, 'guitar/1175:1=-10') is None      # после точки
    assert check_edit(rpp(project), project, 'guitar/vol=-3') is None
    assert check_edit(rpp(project), project, 'master/MGA_JSLimiterST:1=-6') is None
    assert check_edit(rpp(project), project, 'mic/itemvol=-3') is None


def test_no_refuse_without_freeze(project):
    assert check_edit(rpp(project), project, 'guitar/hpflpf:3=-5') is None


def test_parallel_order_and_cleanup(project):
    r = subprocess.run([sys.executable, VARIANTS, project, 'base', 'guitar/vol=-3', 'mic/vol=-2', '--target', '-14'], capture_output=True, text=True)
    heads = [l for l in r.stdout.splitlines() if l.startswith('=== ')]
    assert heads == ['=== base', '=== guitar/vol=-3', '=== mic/vol=-2'], r.stdout + r.stderr
    assert r.stdout.count('порог лимитера под') == 3
    assert not glob.glob(os.path.join(project, 'zz-variant*'))


def test_refused_variant_does_not_stop_others(project):
    write_freeze(project, 0, pink(-14))
    r = subprocess.run([sys.executable, VARIANTS, project, 'guitar/hpflpf:3=-5', 'base'], capture_output=True, text=True)
    assert 'до заморозки' in r.stdout and r.stdout.count('=== ') == 2 and 'мастер' in r.stdout, r.stdout + r.stderr


def test_bad_edit_does_not_stop_others(project):
    r = subprocess.run([sys.executable, VARIANTS, project, 'nosuch/vol=-3', 'base'], capture_output=True, text=True)
    assert 'нет трека nosuch' in r.stdout and 'мастер' in r.stdout, r.stdout + r.stderr
    assert not glob.glob(os.path.join(project, 'zz-variant*'))
