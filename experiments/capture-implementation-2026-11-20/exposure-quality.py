"""What does a shorter exposure cost in noise, with ISO raised to keep the brightness?

  python exposure-quality.py <start> <planes> <out.json>

For each exposure, two four-shot runs of the same <planes> planes 8 units apart (A and B,
interleaved), error correction off: the pairs give the temporal noise of each RAW (same
plane, same shot, independent exposures) and of the final render (A's render minus B's).
Control for "is it the ISO or the light?": single-shot pairs at 1/25 s, at ISO 1600 and at
ISO 100 (four stops under, pushed in the analysis). Restores the exposure, pixel-shift mode
and error-correction setting it found. Deletes nothing (the caller deletes the runs listed).
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'outputs/shelly-power-2026-11-18'))
from bench import cmd, wait  # noqa: E402

start, planes, out = int(sys.argv[1]), int(sys.argv[2]), pathlib.Path(sys.argv[3])
s = wait(lambda a: not a['busy'], timeout=60)
orig = dict(iso=s['exposure']['iso'], shutter=s['exposure']['shutter'], shots=s['shots_per_plane'], ec=s.get('error_correction'))
options = sorted(s['exposure']['shutter_options'], key=lambda v: (v >> 16) / (v & 0xffff))
isos = sorted(i for i in s['exposure']['iso_options'] if i > 0)


def seconds(v):
    return (v >> 16) / (v & 0xffff)


def nearest_shutter(t):
    return min(options, key=lambda v: abs(seconds(v) / t - 1))


def iso_for(t):
    want = 100 * 0.6 / t
    return min(isos, key=lambda i: abs(i / want - 1))


def configure(shots, sh, iso):
    s = wait(lambda a: not a['busy'], timeout=60)
    if s['shots_per_plane'] != shots:
        cmd('pixel_shift', shots=shots)
        s = wait(lambda a: not a['busy'] and a['shots_per_plane'] == shots, timeout=60)
    if (s['exposure']['shutter'], s['exposure']['iso']) != (sh, iso):
        cmd('exposure', iso=iso, shutter=sh)
        s = wait(lambda a: not a['busy'] and a['exposure']['shutter'] == sh and a['exposure']['iso'] == iso, timeout=60)
    return s


def run(n):
    s = wait(lambda a: not a['busy'], timeout=60)
    seq = s['sequence_id'] + 1
    cmd('capture_positions', positions=[start + 8 * i for i in range(n)])
    wait(lambda a: a['sequence_id'] == seq and a['phase'] == 'capturing', timeout=60)
    s = wait(lambda a: a['sequence_id'] == seq and a['phase'] in ('complete', 'stopped', 'fault', 'disconnected') and not a['busy'], timeout=1200)
    assert s['phase'] == 'complete', s['phase']
    return str(pathlib.Path(s['storage']['receipt']['path'].replace('\\\\?\\', '')).parent)


plan = [(t, None, 4, planes) for t in (0.6, 1 / 3, 1 / 6, 1 / 10, 1 / 25, 1 / 50)]
plan += [(1 / 25, None, 1, 3), (1 / 25, 100, 1, 3)]
results = []
try:
    if orig['ec']:
        cmd('error_correction', enabled=False)
        wait(lambda a: not a['busy'] and a.get('error_correction') is False)
    for t, iso, shots, n in plan:
        sh = nearest_shutter(t)
        iso = iso or iso_for(seconds(sh))
        configure(shots, sh, iso)
        pair = [run(n), run(n)]
        row = dict(shutter=sh, seconds=seconds(sh), iso=iso, shots=shots, planes=n, runs=pair)
        print(json.dumps(row), flush=True)
        results.append(row)
        out.write_text(json.dumps(results, indent=1) + '\n')
finally:
    configure(orig['shots'], orig['shutter'], orig['iso'])
    if orig['ec']:
        cmd('error_correction', enabled=True)
        wait(lambda a: not a['busy'] and a.get('error_correction') is True)
    out.write_text(json.dumps(results, indent=1) + '\n')
