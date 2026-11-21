# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy", "scipy", "soundfile", "pyloudnorm", "numba"]
# ///
"""Поправка модели по рендеру «до» со стемами: calib.json в папке проекта.
   uv run calib.py <папка> --master FILE --stem ТРЕК=FILE [--stem ...]
Поправка трека = LUFS стема - LUFS модели трека (после цепочки и фейдера, без поправок).
Поправка мастера = LUFS мастера - выход модели, посчитанный уже с поправками треков: ничего не учитывается дважды.
Ключ calib.json - freezelib.calib_key: отпечатки заморозки и мелкие FX (ReaVerb, де-эссер); фейдеры и JSFX в него не входят."""
import argparse, datetime, json, os, subprocess, sys, tempfile

DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, DIR)
import freezelib, measure


def model(folder, *args):
    fd, js = tempfile.mkstemp(suffix='.json'); os.close(fd)
    try:
        r = subprocess.run([sys.executable, os.path.join(DIR, 'analyze.py'), folder, '--json', js, *args], capture_output=True, text=True)
        if r.returncode: sys.exit(r.stdout + r.stderr)
        with open(js, encoding='utf-8') as f: return json.load(f)
    finally:
        os.remove(js)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('dir'); ap.add_argument('--rpp'); ap.add_argument('--master', required=True)
    ap.add_argument('--stem', action='append', default=[], help='ТРЕК=FILE')
    a = ap.parse_args()
    extra = ['--rpp', a.rpp] if a.rpp else []
    text = freezelib.read_rpp(freezelib.find_rpp(a.dir, a.rpp))
    # поправка по модели без заморозки VST вобрала бы сам VST (+7 dB Blue Cat) - сначала freeze.sh
    nofreeze = [e['name'] for e in freezelib.plan(text) if freezelib.freeze_status(a.dir, e) != 'ok']
    if nofreeze: sys.exit(f"нет актуальной заморозки: {', '.join(nofreeze)} - сначала freeze.sh, потом рендер «до» со стемами")
    m0 = model(a.dir, '--no-calib', *extra)
    tracks, notes, silent = {}, [], []
    for s in a.stem:
        name, path = s.split('=', 1)
        I = measure.measure(path)['I']
        if I is None or I <= -60:
            if name in m0['tracks']: silent.append(name)
            else: notes.append(f'{name}: стем - тишина, трека нет в модели')
            continue
        if name not in m0['tracks']: notes.append(f'{name}: нет в модели, без поправки'); continue
        tracks[name] = round(I - m0['tracks'][name]['lufs'], 2)
    # тихий стем трека модели: в мастере рендера его нет, а в модели есть - поправка мастера вышла бы неверной
    if silent: sys.exit(f"стем - тишина: {', '.join(silent)}. VSTi не звучит: активировать плагин (MT-PowerDrumKit - открыть его окно "
                        f"после открытия проекта) и повторить рендер «до»; calib.json не записан")
    data = dict(key=freezelib.calib_key(text, a.dir), time=datetime.datetime.now().isoformat(timespec='minutes'), tracks=tracks, master=None)
    freezelib.save_json(a.dir, 'calib.json', data)
    m1 = model(a.dir, *extra)
    I = measure.measure(a.master)['I']
    if I is None or I <= -60: sys.exit('мастер - тишина: медиа офлайн? поправка мастера не посчитана')
    data['master'] = round(I - m1['master_out'], 2)
    freezelib.save_json(a.dir, 'calib.json', data)
    for n in notes: print(n)
    big = [f'{n} {v:+.1f}' for n, v in tracks.items() if abs(v) > 1]
    if big: print(f"поправка больше 1 LU: {', '.join(big)} - модель трека расходится с рендером (заморозка, порт JSFX, немоделируемый FX?), разобрать по стемам")
    print('поправки: ' + ', '.join(f'{n} {v:+.1f}' for n, v in tracks.items()) + f"; мастер {data['master']:+.1f}")


if __name__ == '__main__':
    main()
