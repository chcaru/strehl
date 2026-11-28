"""Settle ladder: how far the picture is from rest when the exposure starts, by settle time.

Bursts of ten planes 8 units apart at 1/100 s (the exposure freezes the picture), shot with
the plan's settle at 2000, 100, 250, 500 and 1000 ms, interleaved. Every frame is registered
against the frame at the same position in the first 2000 ms burst. The first plane of a burst
always waits 2 s after the approach, so its shift is the slow drift since the reference; it
is subtracted, and the 2000 ms bursts shot later show what is left of drift and wander.

  python e5-an.py <series.jsonl> <out.json> [workers]
"""
import concurrent.futures as cf
import json
import pathlib
import subprocess
import sys

import numpy as np
import rawpy
from scipy import ndimage

TOOL = r'C:\dev\blog\death-of-software\projects\strehl\target\release\strehl-raw-archive.exe'
SCRATCH = pathlib.Path(r'C:\strehl-scratch\calib-page\tmp-raw')
rows = [json.loads(l) for l in open(sys.argv[1]) if '"settle-' in l]
out = pathlib.Path(sys.argv[2])
workers = int(sys.argv[3]) if len(sys.argv) > 3 else 4
SIDE = 768


def read(run, name):
    SCRATCH.mkdir(parents=True, exist_ok=True)
    work = SCRATCH / ('%s-%s' % (run.name, name))
    work.mkdir(exist_ok=True)
    raw_name = name[:-len('.straw')]
    subprocess.run([TOOL, 'restore', str(run / name), '--output-dir', str(work)], check=True, capture_output=True)
    with rawpy.imread(str(work / raw_name)) as raw:
        img = raw.raw_image_visible.copy()
        black = float(np.mean(raw.black_level_per_channel))
    (work / raw_name).unlink()
    work.rmdir()
    h, w = img.shape
    x0, y0 = (w // 2 - SIDE) & ~1, (h // 2 - SIDE) & ~1
    a = img[y0:y0 + 2 * SIDE, x0:x0 + 2 * SIDE].astype(np.float32) - black
    return a[0::2, 0::2] + a[0::2, 1::2] + a[1::2, 0::2] + a[1::2, 1::2]


def register(ref, mov):
    r = ndimage.gaussian_filter(ref, 1.5)
    m0 = ndimage.gaussian_filter(mov, 1.5)
    d = np.zeros(2)
    core = (slice(16, -16), slice(16, -16))
    for _ in range(8):
        m = ndimage.shift(m0, (-d[1], -d[0]), order=3, mode='nearest') if d.any() else m0
        gy, gx = np.gradient(m)
        A = np.stack([gx[core].ravel(), gy[core].ravel(), m[core].ravel(), np.ones(m[core].size, np.float32)], 1)
        sol, *_ = np.linalg.lstsq(A, r[core].ravel(), rcond=None)
        step = np.array([sol[0], sol[1]]) / max(sol[2], 1e-6)
        d += step
        if np.abs(step).max() < 0.002:
            break
    return 2 * d      # sensor pixels


def names(run):
    return sorted(p.name for p in run.glob('*.ARW.straw'))


runs = [(int(r['label'].split('-')[1]), pathlib.Path(r['folder'].replace(chr(92), '/'))) for r in rows]
ref_run = runs[0][1]
with cf.ThreadPoolExecutor(workers) as ex:
    refs = list(ex.map(lambda n: read(ref_run, n), names(ref_run)))


def burst(item):
    settle, run = item
    ns = names(run)
    shifts = []
    for k, n in enumerate(ns):
        shifts.append(register(refs[k], read(run, n)))
    shifts = np.array(shifts)
    rel = shifts - shifts[0]
    return {'settle': settle, 'run': run.name, 'shift': shifts.tolist(), 'rel': rel.tolist()}


with cf.ThreadPoolExecutor(2) as ex:
    res = list(ex.map(burst, runs[1:]))
by = {}
for r in res:
    rel = np.array(r['rel'])[1:]
    mag = np.hypot(rel[:, 0], rel[:, 1])
    by.setdefault(r['settle'], []).append(mag)
    print('settle %4d ms %s: first-plane shift (%+.2f, %+.2f) px; planes 2-10 against it: median %.2f px, max %.2f px, x rms %.2f y rms %.2f' % (
        r['settle'], r['run'][-20:], r['shift'][0][0], r['shift'][0][1], float(np.median(mag)), float(mag.max()),
        float(np.sqrt((rel[:, 0] ** 2).mean())), float(np.sqrt((rel[:, 1] ** 2).mean()))))
print('by settle (all repeats): median, 90th percentile, max of the distance from rest, px')
summary = {}
for settle in sorted(by):
    m = np.concatenate(by[settle])
    summary[settle] = {'median': float(np.median(m)), 'p90': float(np.percentile(m, 90)), 'max': float(m.max()), 'n': int(m.size)}
    print('  %4d ms: %.2f  %.2f  %.2f  (n %d)' % (settle, summary[settle]['median'], summary[settle]['p90'], summary[settle]['max'], m.size))
out.write_text(json.dumps({'bursts': res, 'summary': summary}, indent=1))
