import numpy as np, soundfile as sf
from conftest import SR
import analyze


def test_ms_decode_formula():
    x = np.array([[1.0, 0.5], [0.2, -0.1]])
    y = analyze.ms_decode(x, ['70', '0'])
    assert np.allclose(y, [[1.35, 0.65], [0.13, 0.27]])
    assert np.allclose(analyze.ms_decode(x, ['0', '-6']), np.repeat(x[:, :1], 2, 1) * 10 ** (-6 / 20))


def test_build_resamples_96k(tmp_path):
    t = np.arange(96000) / 96000
    sf.write(tmp_path / 'a.wav', np.stack([np.sin(2 * np.pi * 440 * t)] * 2, 1).astype(np.float32), 96000, subtype='FLOAT')
    tr = dict(items=[dict(pos=0, len=0.5, soffs=0.25, file='a.wav', fi=0, fo=0, vol=1, chan=0, mute=False)])
    y = analyze.build(tr, str(tmp_path))
    assert abs(len(y) - SR // 2) <= 1 and abs(np.sqrt(np.mean(y[1000:-1000, 0] ** 2)) - 0.7071) < 0.01
