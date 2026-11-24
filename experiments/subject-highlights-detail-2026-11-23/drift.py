"""Is the picture drifting or shaking? Every try of a plane is at one focus position, so the
shift of each try against the plane's first try, with its time, is the rig's motion.

Uses member 1 of each group (green sites, a central 1536 px window split in four 768 px tiles),
phase correlation with a parabolic peak. Also the time each group took.

  python drift.py <capture folder> [min tries per plane]
"""
import json
import pathlib
import subprocess
import sys

import numpy as np
import rawpy

TOOL = pathlib.Path(r'C:\dev\blog\death-of-software\projects\strehl\target\release\strehl-raw-archive.exe')
SCRATCH = pathlib.Path(r'C:\strehl-scratch\i-round\tmp-raw')
run = pathlib.Path(sys.argv[1])
min_tries = int(sys.argv[2]) if len(sys.argv) > 2 else 4
T = 768


def green(name):
    SCRATCH.mkdir(parents=True, exist_ok=True)
    work = SCRATCH / ('drift-' + name)
    work.mkdir(exist_ok=True)
    subprocess.run([str(TOOL), 'restore', str(run / (name + '.straw')), '--output-dir', str(work)], check=True, capture_output=True)
    with rawpy.imread(str(work / name)) as raw:
        img = raw.raw_image_visible.copy()
        pattern = raw.raw_pattern.copy()
        colours = raw.color_desc.decode()
    (work / name).unlink()
    work.rmdir()
    y, x = next((y, x) for y in (0, 1) for x in (0, 1) if colours[pattern[y, x]] == 'G')
    g = img[y::2, x::2].astype(np.float32)
    h, w = g.shape
    return g[h // 2 - T:h // 2 + T, w // 2 - T:w // 2 + T]


fy = np.fft.fftfreq(T)[:, None]
fx = np.fft.rfftfreq(T)[None, :]
FR = np.hypot(fy, fx)
WIN = np.hanning(T)[:, None] * np.hanning(T)[None, :]


def shift(a, b):
    fa, fb = np.fft.rfft2((a - a.mean()) * WIN), np.fft.rfft2((b - b.mean()) * WIN)
    cross = fa * np.conj(fb)
    corr = np.fft.irfft2(cross / (np.abs(cross) + 1e-3 * np.abs(cross).max()) * np.exp(-(FR / 0.15) ** 2), s=(T, T))
    py, px = np.unravel_index(corr.argmax(), corr.shape)

    def sub(m, c, p):
        d = m - 2 * c + p
        return 0.0 if d == 0 else 0.5 * (m - p) / d
    dy = (py + T // 2) % T - T // 2 + sub(corr[(py - 1) % T, px], corr[py, px], corr[(py + 1) % T, px])
    dx = (px + T // 2) % T - T // 2 + sub(corr[py, (px - 1) % T], corr[py, px], corr[py, (px + 1) % T])
    return 2 * dx, 2 * dy          # green sites are 2 px apart: report sensor pixels


tries = {}
t0 = None
for line in open(run / 'events.jsonl', encoding='utf-8'):
    e = json.loads(line)
    t0 = t0 or e['unix_ms']
    if e['event'] == 'capture_buffered':
        r = e['data']['response']
        first = sorted(r['files'], key=lambda f: f['member_index'])[0]['name']
        tries.setdefault(e['data']['ordinal'], []).append(((e['unix_ms'] - t0) / 1000, first, r['camera_seconds']))
rates = []
for ordinal, ts in sorted(tries.items()):
    if len(ts) < min_tries:
        continue
    ref = green(ts[0][1])
    print('plane %d, %d tries:' % (ordinal + 1, len(ts)))
    prev = (0.0, 0.0, ts[0][0])
    for t, name, cam in ts[1:]:
        g = green(name)
        s = [shift(ref[y:y + T, x:x + T], g[y:y + T, x:x + T]) for y in (0, T) for x in (0, T)]
        dx, dy = float(np.median([v[0] for v in s])), float(np.median([v[1] for v in s]))
        step = np.hypot(dx - prev[0], dy - prev[1])
        dt = t - prev[2]
        rates.append(step / dt)
        print('   +%6.1f s: %+6.2f, %+6.2f px from the first try; moved %.2f px in %.1f s since the last (%.3f px/s); group took %.1f s' % (
            t - ts[0][0], dx, dy, step, dt, step / dt, cam))
        prev = (dx, dy, t)
if rates:
    r = np.array(rates)
    print('rate between consecutive tries: median %.3f px/s, 25th-75th percentile %.3f-%.3f; over one 8.3 s group that is %.2f px (median)' % (
        np.median(r), np.percentile(r, 25), np.percentile(r, 75), 8.3 * np.median(r)))
