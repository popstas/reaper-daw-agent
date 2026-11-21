import os, subprocess, sys
import numpy as np, soundfile as sf
import freezelib, measure
from conftest import SKILL, SR, pink, rpp, write_freeze


def write_pink(tmp_path, rms):
    p = tmp_path / 'pink.wav'; sf.write(p, pink(rms).astype(np.float32), SR, subtype='FLOAT'); return p


def analyze(project, *args):
    r = subprocess.run([sys.executable, os.path.join(SKILL, 'analyze.py'), project, *args], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    return r.stdout


def model_stems(project, tmp_path, gain):
    d = tmp_path / 'stems'; analyze(project, '--no-calib', '--stems-dir', str(d))
    out = {}
    for f in sorted(os.listdir(d)):
        name = f[:-4]; x, sr = sf.read(d / f, always_2d=True)
        sf.write(d / f, (x * 10 ** (gain.get(name, 0) / 20)).astype(np.float32), sr, subtype='FLOAT')
        out[name] = str(d / f)
    return out


def model_master(project, tmp_path):
    p = str(tmp_path / 'master.wav'); analyze(project, '--no-calib', '--wav', p); return p


def run_calib(project, master, stems, ok=True):
    args = [sys.executable, os.path.join(SKILL, 'calib.py'), project, '--master', master]
    for n, p in stems.items(): args += ['--stem', f'{n}={p}']
    r = subprocess.run(args, capture_output=True, text=True)
    assert (r.returncode == 0) == ok, r.stdout + r.stderr
    return r.stdout + r.stderr


def frozen(project):
    write_freeze(project, 0, pink(-14)); write_freeze(project, 1, pink(-16, seed=4))
    return project


def test_measure_pink(tmp_path):            # wav розового шума −20 dBFS RMS
    r = measure.measure(str(write_pink(tmp_path, -20)))
    assert -24 < r['I'] < -16 and r['tp'] is not None and r['lra'] is not None


def test_stems_dir_writes_tracks(project, tmp_path):
    stems = model_stems(project, tmp_path, {})
    assert sorted(stems) == ['guitar', 'mic']             # drums без заморозки не в модели
    stems = model_stems(frozen(project), tmp_path, {})
    assert sorted(stems) == ['drums', 'guitar', 'mic']


def test_calib_roundtrip(project, tmp_path):
    frozen(project)
    stems = model_stems(project, tmp_path, gain={'mic': 0.5})   # модельные выходы треков, mic громче на 0.5 dB
    master = model_master(project, tmp_path)                    # analyze.py --no-calib --wav
    out = run_calib(project, master, stems)
    calib = freezelib.load_json(project, 'calib.json')
    assert abs(calib['tracks']['mic'] - 0.5) < 0.1 and abs(calib['tracks']['guitar']) < 0.1
    assert calib['key'] == freezelib.calib_key(rpp(project), project)
    assert calib['master'] is not None
    assert 'поправки:' in out and 'mic +0.5' in out
    assert 'поправка по рендеру до' in analyze(project)


def test_calib_refuses_silent_stem(project, tmp_path):
    # тихий стем трека модели (MT-PowerDrumKit не активирован): мастер без барабанов - поправка мастера была бы неверной
    stems = model_stems(frozen(project), tmp_path, {})
    sf.write(tmp_path / 'silent.wav', np.zeros((SR * 6, 2), np.float32), SR, subtype='FLOAT')
    stems['drums'] = str(tmp_path / 'silent.wav')
    out = run_calib(project, model_master(project, tmp_path), stems, ok=False)
    assert 'тишина' in out and 'drums' in out and 'активировать' in out
    assert freezelib.load_json(project, 'calib.json') == {}


def test_calib_refuses_without_freeze(project, tmp_path):
    stems = model_stems(project, tmp_path, {})
    out = run_calib(project, model_master(project, tmp_path), stems, ok=False)
    assert 'freeze.sh' in out and 'guitar' in out and freezelib.load_json(project, 'calib.json') == {}


def test_calib_warns_big_offset(project, tmp_path):
    stems = model_stems(frozen(project), tmp_path, gain={'mic': 1.6})
    out = run_calib(project, model_master(project, tmp_path), stems)
    assert 'больше 1 LU' in out and 'mic' in out
