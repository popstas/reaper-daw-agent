import os, re, sys
import numpy as np, soundfile as sf

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import abproj


def test_shift_and_rotation(tmp_path):
    rng = np.random.default_rng(1)
    sr = 48000
    x = rng.standard_normal(sr * 70) * 0.1
    sh = int(0.25 * sr)   # вторая версия: 0.25 с тишины в начале и тише на 6 dB
    y = np.concatenate([np.zeros(sh), x * 0.5])
    sf.write(tmp_path / "a.wav", x, sr); sf.write(tmp_path / "b.wav", y, sr)
    out = tmp_path / "ab.rpp"
    shifts, nseg, seg, total = abproj.build(str(out), [("A", str(tmp_path / "a.wav")), ("B", str(tmp_path / "b.wav"))], bars=2)
    assert abs(shifts[1][1] - 0.25) < 0.001 and shifts[1][2] > 0.99 and shifts[1][3] < 0.001
    assert seg == 4.0 and nseg == int(np.ceil(total / 4))
    text = out.read_bytes().decode()
    assert "\r\n" in text
    soffs = [float(v) for v in re.findall(r"SOFFS (\S+)", text)]
    pos = [float(v) for v in re.findall(r"POSITION (\S+)", text)]
    names = re.findall(r'FILE "(\S+)"', text)
    # трек A - отрезки 0, 2, 4...; трек B - 1, 3... со сдвигом 0.25
    for p, s, f in zip(pos, soffs, names):
        assert abs(s - p - (0.25 if f == "b.wav" else 0)) < 0.001
    assert names[0] == "a.wav" and pos[0] == 0
    assert text.count("MARKER") == nseg
