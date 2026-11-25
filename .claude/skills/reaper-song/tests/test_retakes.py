import numpy as np, soundfile as sf
import analyze

SR = analyze.SR


def take(tmp_path, name, segs, noise_db, seed):
    """Дубль: шум пола noise_db везде, игра -20 dB на участках segs (с), щелчок старта на 0.1 с."""
    rng = np.random.default_rng(seed)
    n = int(40 * SR)
    x = rng.standard_normal(n) * 10 ** (noise_db / 20)
    for a, b in segs:
        x[int(a * SR):int(b * SR)] += rng.standard_normal(int(b * SR) - int(a * SR)) * 0.1
    x[int(0.1 * SR):int(0.1 * SR) + 200] += 0.3   # щелчок старта
    p = tmp_path / f"{name}.wav"; sf.write(p, x, SR, subtype='FLOAT')
    return x, str(p)


def run(tmp_path, segs):
    g, gf = take(tmp_path, 'g', segs, -61, 1)
    m, mf = take(tmp_path, 'm', segs, -75, 2)
    return analyze.retakes(g, m, [gf], [mf])


def test_pause_in_middle_found(tmp_path):
    r = run(tmp_path, [(3, 18), (20.5, 38)])
    assert '0:18' in r and 'splicefind' in r


def test_edges_and_short_pause_ignored(tmp_path):
    # тишина 3 с до игры со щелчком старта, 2 с после, пауза 0.6 с в середине - не врезка
    assert 'нет' in run(tmp_path, [(3, 18), (18.6, 38)])
