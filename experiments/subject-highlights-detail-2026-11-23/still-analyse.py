"""Analyse the stillness test: where the picture sits over time.

Live series (magnified live view): each frame registered against the first (phase correlation,
parabolic peak) on the whole frame and on its four quadrants. Scaled to sensor pixels by the
magnifier ratio, checked against the picture itself (the ratio's tenth is the magnification).
Reports the slow drift (a quadratic trend), the faster motion left after removing it, its
spectrum (Lomb-Scargle, uneven sampling) and whether the four quadrants move together.

RAW burst: single shots at one focus position; green-site plane, four 768 px tiles around the
centre; shifts against the first frame with the journal's times.

  python still-analyse.py <still folder>
"""
import json
import pathlib
import subprocess
import sys

import numpy as np
from PIL import Image
from scipy import signal

root = pathlib.Path(sys.argv[1])
rec = json.loads((root / 'record.json').read_text())
TOOL = pathlib.Path(r'C:\dev\blog\death-of-software\projects\strehl\target\release\strehl-raw-archive.exe')


def register(a, b, soft=0.15):
    n0, n1 = a.shape
    win = np.hanning(n0)[:, None] * np.hanning(n1)[None, :]
    fa, fb = np.fft.rfft2((a - a.mean()) * win), np.fft.rfft2((b - b.mean()) * win)
    fy = np.fft.fftfreq(n0)[:, None]
    fx = np.fft.rfftfreq(n1)[None, :]
    cross = fa * np.conj(fb)
    corr = np.fft.irfft2(cross / (np.abs(cross) + 1e-3 * np.abs(cross).max()) * np.exp(-((fy ** 2 + fx ** 2) / soft ** 2)), s=a.shape)
    py, px = np.unravel_index(corr.argmax(), corr.shape)

    def sub(m, c, p):
        d = m - 2 * c + p
        return 0.0 if d == 0 else 0.5 * (m - p) / d
    dy = (py + n0 // 2) % n0 - n0 // 2 + sub(corr[(py - 1) % n0, px], corr[py, px], corr[(py + 1) % n0, px])
    dx = (px + n1 // 2) % n1 - n1 // 2 + sub(corr[py, (px - 1) % n1], corr[py, px], corr[py, (px + 1) % n1])
    return dx, dy


def describe(t, x, y, unit, label):
    t = np.asarray(t)
    out = {}
    for name, v in (('x', np.asarray(x)), ('y', np.asarray(y))):
        trend = np.polyval(np.polyfit(t, v, 2), t)
        res = v - trend
        out[name] = (trend, res)
    rx, ry = out['x'][1], out['y'][1]
    r = np.hypot(rx, ry)
    drift = np.hypot(out['x'][0][-1] - out['x'][0][0], out['y'][0][-1] - out['y'][0][0])
    step = np.hypot(np.diff(x), np.diff(y))
    print('%s: %d frames over %.1f s (%.1f a second)' % (label, len(t), t[-1] - t[0], (len(t) - 1) / (t[-1] - t[0])))
    print('   slow drift over the series: %.2f %s (%.4f %s/s)' % (drift, unit, drift / (t[-1] - t[0]), unit))
    print('   motion about the drift: rms %.3f %s in x, %.3f in y; radial median %.3f, 95th percentile %.3f, largest %.3f' % (
        rx.std(), unit, ry.std(), np.median(r), np.percentile(r, 95), r.max()))
    print('   frame-to-frame step: median %.3f %s, 95th percentile %.3f' % (np.median(step), unit, np.percentile(step, 95)))
    if len(t) > 40:
        freqs = np.linspace(0.05, min(4.0, 0.45 * (len(t) - 1) / (t[-1] - t[0])), 400)
        for name, v in (('x', rx), ('y', ry)):
            p = signal.lombscargle(t - t[0], v - v.mean(), 2 * np.pi * freqs, normalize=True)
            k = int(p.argmax())
            lowshare = p[freqs < 0.5].sum() / p.sum()
            print('   %s spectrum: strongest at %.2f Hz (normalised power %.2f); %.0f %% of the power below 0.5 Hz' % (name, freqs[k], p[k], 100 * lowshare))
    return rx, ry


for series in rec.get('live', []):
    frames = series['frames']
    if len(frames) < 5:
        continue
    folder = root / series['label']
    ratio = (rec.get('magnifier_used') or 10) / 10.0
    first = None
    T, X, Y, Q = [], [], [], []
    for f in frames:
        im = np.asarray(Image.open(folder / f['name']).convert('L'), np.float32)
        h, w = im.shape
        c = im[h // 2 - 256:h // 2 + 256, w // 2 - 384:w // 2 + 384]
        if first is None:
            first = c
            hh, ww = c.shape
        dx, dy = register(first, c)
        quads = [register(first[y0:y0 + hh // 2, x0:x0 + ww // 2], c[y0:y0 + hh // 2, x0:x0 + ww // 2]) for y0 in (0, hh // 2) for x0 in (0, ww // 2)]
        T.append(f['t']); X.append(dx); Y.append(dy); Q.append(quads)
    # one live pixel in sensor pixels: the live frame shows (sensor width / ratio) across its width
    live_w = Image.open(folder / frames[0]['name']).size[0]
    scale = 9504.0 / ratio / live_w
    print('\n%s: magnifier %.1fx, live frame %d px wide, so one live pixel is about %.2f sensor px (from the ratio; not checked against a RAW)' % (
        series['label'], ratio, live_w, scale))
    X, Y = np.array(X) * scale, np.array(Y) * scale
    rx, ry = describe(T, X, Y, 'sensor px', series['label'])
    Q = np.array(Q) * scale               # [frame, quadrant, xy]
    dev = Q - Q.mean(1, keepdims=True)    # each quadrant against the frame's mean shift
    dev = dev - dev.mean(0, keepdims=True)
    print('   quadrants against each other: rms %.3f sensor px (rigid motion would leave only measurement noise here); whole-frame motion rms %.3f' % (
        dev.std(), np.hypot(rx.std(), ry.std())))
    np.savez(root / (series['label'] + '-series.npz'), t=np.array(T), x=X, y=Y, q=Q)

b = rec.get('burst')
if b:
    import rawpy
    run = pathlib.Path(b['folder'])
    names, times = [], []
    t0 = None
    for line in open(run / 'events.jsonl', encoding='utf-8'):
        e = json.loads(line)
        t0 = t0 or e['unix_ms']
        if e['event'] == 'capture_buffered':
            names.append(e['data']['response']['files'][0]['name'])
            times.append((e['unix_ms'] - t0) / 1000)
    scratch = root / 'tmp'
    scratch.mkdir(exist_ok=True)
    TT = 768

    def green(name):
        subprocess.run([str(TOOL), 'restore', str(run / (name + '.straw')), '--output-dir', str(scratch)], check=True, capture_output=True)
        with rawpy.imread(str(scratch / name)) as raw:
            img = raw.raw_image_visible.copy()
            pattern = raw.raw_pattern.copy()
            colours = raw.color_desc.decode()
        (scratch / name).unlink()
        y, x = next((y, x) for y in (0, 1) for x in (0, 1) if colours[pattern[y, x]] == 'G')
        g = img[y::2, x::2].astype(np.float32)
        h, w = g.shape
        return g[h // 2 - TT:h // 2 + TT, w // 2 - TT:w // 2 + TT]

    ref = green(names[0])
    X, Y, Q = [0.0], [0.0], [[(0.0, 0.0)] * 4]
    for n in names[1:]:
        g = green(n)
        quads = [register(ref[y0:y0 + TT, x0:x0 + TT], g[y0:y0 + TT, x0:x0 + TT]) for y0 in (0, TT) for x0 in (0, TT)]
        q = np.array(quads) * 2.0                      # green sites are 2 sensor px apart
        X.append(float(np.median(q[:, 0]))); Y.append(float(np.median(q[:, 1]))); Q.append([tuple(v) for v in q])
    scratch.rmdir()
    print('\nRAW burst: %d single shots at %.4f s, one focus position, %s' % (len(names), b['seconds'], run.name))
    rx, ry = describe(times, np.array(X), np.array(Y), 'sensor px', 'burst')
    Q = np.array(Q)
    dev = Q - Q.mean(1, keepdims=True)
    dev = dev - dev.mean(0, keepdims=True)
    print('   tiles against each other: rms %.3f sensor px; whole-frame motion rms %.3f' % (dev.std(), np.hypot(rx.std(), ry.std())))
    print('   positions against the first frame (sensor px): ' + ' '.join('(%+.2f,%+.2f)' % (x, y) for x, y in zip(X, Y)))
    np.savez(root / 'burst-series.npz', t=np.array(times), x=np.array(X), y=np.array(Y), q=Q)
