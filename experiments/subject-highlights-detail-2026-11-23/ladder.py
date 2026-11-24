"""The shutter ladder (brief Q3, Q5): how bright the glints are, how much clips at each shutter,
whether the exposure ratios hold, and what a group costs in time.

  python ladder.py <index.json> <mask .npz> <out folder>
"""
import json
import pathlib
import sys

import numpy as np
from scipy import ndimage

import rigdata

index = [r for r in json.loads(pathlib.Path(sys.argv[1]).read_text()) if r.get('series') == 'ladder']
mask8 = np.load(sys.argv[2])['mask']
out = pathlib.Path(sys.argv[3])
out.mkdir(parents=True, exist_ok=True)
FULL = 16383.0 - 512.0
positions = sorted({r['position'] for r in index})
lines = []


def say(*a):
    s = ' '.join(str(v) for v in a)
    print(s, flush=True)
    lines.append(s)


def fit_mask(h, w):
    big = np.kron(mask8, np.ones((8, 8), bool))[2:, 2:]
    m = np.zeros((h, w), bool)
    hh, ww = min(h, big.shape[0]), min(w, big.shape[1])
    m[:hh, :ww] = big[:hh, :ww]
    return m


def timing(folder):
    t = {}
    for line in open(pathlib.Path(folder) / 'events.jsonl', encoding='utf-8'):
        e = json.loads(line)
        t[e['event']] = e['unix_ms']
        if e['event'] == 'capture_buffered':
            cam = e['data']['response']['camera_seconds']
    return cam, (t['finished'] - t['capture_intent']) / 1000


for pos in positions:
    rungs = sorted([r for r in index if r['position'] == pos], key=lambda r: (-r['seconds'], r['started']))
    say('\n=== position %d (%d groups)' % (pos, len(rungs)))
    data = {}
    for r in rungs:
        ms = rigdata.members(r['folder'])
        rgb, pinned, _ = rigdata.assemble(ms)
        key = (r['seconds'], r.get('note') or '')
        h, w = rgb.shape[:2]
        m = fit_mask(h, w)
        # member-to-member level (flicker): mean green of the central quarter per member
        lv = []
        for img, b, wl, cfa in ms:
            g = img[1::2, 0::2] if cfa[1, 0] == 'G' else img[0::2, 0::2]
            hh, ww = g.shape
            lv.append(float(g[hh // 4:3 * hh // 4, ww // 4:3 * ww // 4].mean()) - b)
        cam, total = timing(r['folder'])
        clipped = [int((pinned[..., i] & m).sum()) for i in range(3)]
        anyc = int((pinned.any(-1) & m).sum())
        say('%8.5f s %-22s | camera %.2f s, intent to finished %.2f s | member spread %.4f | sites with a pinned sample in the subject: R %d G %d B %d, any %d (%.4f %% of the subject)' % (
            r['seconds'], key[1], cam, total, (max(lv) - min(lv)) / np.mean(lv), *clipped, anyc, 100 * anyc / m.sum()))
        data[key] = (rgb, pinned, r)
        del ms
    keys = list(data)
    owner = [k for k in keys if 'first' in k[1]][0]
    last = [k for k in keys if 'last' in k[1]]
    # exposure ratios on 8x8 block means of green where both rungs are well inside the range
    def blocks(a):
        hh, ww = a.shape[0] // 8 * 8, a.shape[1] // 8 * 8
        return a[:hh, :ww].reshape(hh // 8, 8, ww // 8, 8).mean((1, 3))
    ref = blocks(data[owner][0][..., 1])
    say('exposure ratios against the owner shutter (median of green block means, blocks at 2-60 % of full scale in both):')
    measured = {}
    for k in keys:
        if k == owner:
            continue
        b = blocks(data[k][0][..., 1])
        sel = (ref > 0.02 * FULL) & (ref < 0.6 * FULL) & (b > 0.02 * FULL) & (b < 0.6 * FULL)
        if sel.sum() < 200:
            sel = (ref > 0.002 * FULL) & (ref < 0.6 * FULL) & (b > 0.002 * FULL) & (b < 0.6 * FULL)
        ratio = float(np.median(b[sel] / ref[sel]))
        measured[k] = ratio
        say('   %8.5f s %-20s nominal %.4f measured %.4f (%+.1f %%) on %d blocks' % (k[0], k[1], k[0] / owner[0], ratio, 100 * (ratio / (k[0] / owner[0]) - 1), sel.sum()))
    measured[owner] = 1.0
    # shift between the first and last owner-shutter groups (drift over the ladder)
    if last:
        a, b = data[owner][0][..., 1], data[last[0]][0][..., 1]
        cy, cx = a.shape[0] // 2, a.shape[1] // 2
        best = None
        for tile in range(9):
            y0 = cy - 1500 + (tile // 3) * 1200
            x0 = cx - 2200 + (tile % 3) * 1800
            ta, tb = a[y0:y0 + 512, x0:x0 + 512], b[y0:y0 + 512, x0:x0 + 512]
            if ta.mean() < 0.01 * FULL:
                continue
            fa, fb = np.fft.rfft2(ta - ta.mean()), np.fft.rfft2(tb - tb.mean())
            cross = fa * np.conj(fb)
            corr = np.fft.irfft2(cross / (np.abs(cross) + 1e-6), s=ta.shape)
            py, px = np.unravel_index(corr.argmax(), corr.shape)
            py, px = (py + 256) % 512 - 256, (px + 256) % 512 - 256
            say('   drift first -> last owner group, tile %d: %+d, %+d px (whole-pixel peak)' % (tile, px, py))
    # glints: brightest value per 9x9 window (revisits drift by a few px) in each rung, from the longest rung where the window is unpinned
    rad = None   # radiance in units of the owner shutter's full scale, max over colours
    for k in sorted(keys, key=lambda k: -k[0]):
        if 'last' in k[1]:
            continue
        rgb, pinned, r = data[k]
        peak = ndimage.maximum_filter(rgb.max(-1), 9) / FULL / measured[k]
        pin = ndimage.maximum_filter(pinned.any(-1).astype(np.uint8), 9) > 0
        if rad is None:
            rad, known = peak, ~pin
        else:
            take = ~known & ~pin
            rad[take] = peak[take]
            known |= take
            still = ~known
            rad[still] = np.maximum(rad[still], peak[still])
    h, w = rad.shape
    m = fit_mask(h, w)
    say('radiance of the subject in units of the owner shutter\'s full scale (9x9 window peaks; unknown = pinned even at the shortest shutter: %d sites)' % int((~known & m).sum()))
    for level in (1 / 5.2, 0.5, 1, 2, 4, 8, 16, 32, 64, 128, 250):
        say('   above %7.3f x: %9d sites (%.5f %% of the subject)' % (level, int(((rad >= level) & m).sum()), 100 * ((rad >= level) & m).sum() / m.sum()))
    # distinct glints above the owner full scale and their peaks
    lab, n = ndimage.label((rad >= 1.0) & m)
    if n:
        peaks = ndimage.maximum(rad, lab, range(1, n + 1))
        sizes = ndimage.sum(np.ones_like(rad), lab, range(1, n + 1))
        say('   %d separate regions exceed the owner full scale; peak median %.1f x, p90 %.1f x, max %.1f x; region size (9x9-dilated) median %d, p90 %d, max %d sites' % (
            n, np.median(peaks), np.percentile(peaks, 90), peaks.max(), np.median(sizes), np.percentile(sizes, 90), sizes.max()))
    np.savez_compressed(out / ('radiance-%d.npz' % pos), rad=rad.astype(np.float32), known=known)
    del data
(out / 'ladder.txt').write_text('\n'.join(lines) + '\n')
