"""F2 gate (capture calibration spec 9, F2): the in-focus range from contrast on eight stacks.

Runs `strehl subject` on each stack with 13 planes (its default) and with every plane, in a
private cache, and compares `in_focus.in_focus_first/last` and `reaches_*` with the spec's
table. Tolerance: one frame spacing of the set (`--frames 2` allows two: the port reads the
injected noise model and `strehl subject`'s own outline where the reference fitted its noise
and used its own mask). Writes nothing into the capture folders.

  python gates.py <strehl exe> <out dir>
"""
import json
import os
import pathlib
import subprocess
import sys

CAP = pathlib.Path('D:/StrehlCaptures')
# run, (all planes first, last), (13 planes first, last), reaches (first, last); None: either.
TABLE = [
    ('stack-1795713444768-14989', (32366, 33174), (32366, 33166), (False, False)),
    ('stack-1795460665629-8651', (24699, 25644), (24713, 25637), (False, False)),
    ('stack-1795300522964-6430', (31125, 32287), (31132, 32231), (False, False)),
    ('stack-1795433406862-8651', (30704, 31754), (30784, 31684), (False, False)),
    ('stack-1795371396674-6430', (15833, 16418), (15853, 16388), (False, False)),
    ('stack-1795476520452-8651', (60830, 62800), (60830, 62800), (True, True)),
    ('stack-1794786793543-11226', (50300, 51860), (50300, 51860), (True, True)),
    ('stack-1794689780304-11226', (61050, 61898), (61050, 61898), (True, None)),
]


def run(exe, out, name, extra):
    dst = out / f'{name}-{"all" if extra else "13"}.json'
    env = dict(os.environ, STREHL_CACHE_DIR=str(out / 'cache'))
    cmd = [exe, 'subject', str(CAP / name), '--out', str(dst)] + extra
    p = subprocess.run(cmd, env=env, capture_output=True, text=True)
    (out / (dst.stem + '.log')).write_text(p.stdout + p.stderr, encoding='utf-8')
    if p.returncode != 0:
        return None, f'exit {p.returncode}'
    return json.loads(dst.read_text(encoding='utf-8')), None


def spacing(v):
    pos = [p[0] for p in (v.get('in_focus') or {}).get('per_position') or []]
    gaps = [b - a for a, b in zip(pos, pos[1:])]
    return max(gaps) if gaps else 0.0


def main():
    exe, out = sys.argv[1], pathlib.Path(sys.argv[2])
    frames = float(sys.argv[sys.argv.index('--frames') + 1]) if '--frames' in sys.argv else 1.0
    out.mkdir(parents=True, exist_ok=True)
    fails = 0
    rows = []
    for name, full, thirteen, reaches in TABLE:
        for label, extra, want in (('all', ['--every', '1'], full), ('13', [], thirteen)):
            v, err = run(exe, out, name, extra)
            if err:
                rows.append((name, label, err, 'FAIL'))
                fails += 1
                continue
            d = v.get('in_focus') or {}
            got = (d.get('in_focus_first'), d.get('in_focus_last'))
            got_r = (d.get('reaches_first'), d.get('reaches_last'))
            tol = frames * spacing(v)
            ok = all(g is not None and abs(g - w) <= tol + 1e-6 for g, w in zip(got, want))
            ok &= all(w is None or g == w for g, w in zip(got_r, reaches))
            fails += not ok
            b = v.get('bounds') or {}
            rows.append((name, label,
                         f'{got[0]} - {got[1]} (want {want[0]} - {want[1]}, tol {tol:.0f}); '
                         f'reaches {got_r}; bounds {b.get("start")} - {b.get("end")}; '
                         f'old {(v.get("depth") or {}).get("first_focus")} - {(v.get("depth") or {}).get("last_focus")}',
                         'ok' if ok else 'FAIL'))
            print(*rows[-1], flush=True)
    (out / 'gates.txt').write_text('\n'.join(' | '.join(map(str, r)) for r in rows) + '\n', encoding='utf-8')
    print('failures', fails)
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
