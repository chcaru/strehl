"""Noise against exposure time, from the paired runs of exposure-quality.py.

  python exposure-analyse.py <runs.json> <scratch> <crops out folder> <out.json>

1. Each RAW (temporal noise, like with like): run A's and run B's RAW of the same plane and
   shot are two exposures of the same scene; their difference is noise only (edges, where a
   lens revisit can move detail by a fraction of a pixel, are masked out). One green site
   per 2x2 quad; black level removed; B scaled to A's level (the scale is reported: it is the
   exposure's repeatability). Pixels are binned by the brightness of the same scene point in
   the 0.6 s pair, so every setting is judged on the same pixels. SNR = mean / sigma, sigma
   from the median absolute deviation. A fit var = g * mean + r^2 over the bins gives the
   gain g (DN per electron) and so the electrons at each brightness.
2. The final render (four-shot, `stack --demosaic`, pyramid merge, the CLI's defaults): A's
   render minus B's in flat tiles (the 0.6 s render's flattest 30 % of 64 px tiles), SNR per
   tile; medians by brightness.
3. Crops of the same scene area from every setting's A render, one display transform
   (each render scaled to the 0.6 s render's level), 200 % nearest neighbour.
Renders go to <scratch> and are deleted at the end; restored RAWs are deleted as read.
"""
import json
import os
import pathlib
import subprocess
import sys

import cv2
import numpy as np
import rawpy
import tifffile

ROOT = pathlib.Path(__file__).resolve().parents[2]
TOOL = ROOT / 'target/release/strehl-raw-archive.exe'
EXE = ROOT / 'target/release/strehl.exe'
rows = json.loads(pathlib.Path(sys.argv[1]).read_text())
scratch, crops_out, out_json = pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3]), pathlib.Path(sys.argv[4])
scratch.mkdir(parents=True, exist_ok=True)
crops_out.mkdir(parents=True, exist_ok=True)
BINS = [0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.4]


def label(r):
    t = r['seconds']
    return ('%.1f s' % t if t >= 0.3 else '1/%d s' % round(1 / t)) + ' ISO %d' % r['iso'] + ('' if r['shots'] == 4 else ' single')


def files(folder):
    """(plane ordinal, shot) -> archive name, in capture order."""
    out = {}
    planes = []
    for line in open(pathlib.Path(folder) / 'events.jsonl', encoding='utf-8'):
        e = json.loads(line)
        if e.get('event') != 'capture_buffered':
            continue
        names = sorted(f['name'] for f in e['data']['response']['files'])
        planes.append(names)
    for i, names in enumerate(planes):
        for j, n in enumerate(names):
            out[(i, j)] = n
    return out


def green(folder, name):
    out = scratch / name
    if out.exists():
        out.unlink()
    subprocess.run([str(TOOL), 'restore', str(pathlib.Path(folder) / (name + '.straw')), '--output-dir', str(scratch)],
                   check=True, capture_output=True)
    with rawpy.imread(str(out)) as raw:
        img = raw.raw_image_visible.copy()  # copy inside the context
        black = float(np.mean(raw.black_level_per_channel))
        white = float(raw.white_level)
        pattern = raw.raw_pattern.copy()
        colours = raw.color_desc.decode()
    out.unlink()
    y, x = next((y, x) for y in (0, 1) for x in (0, 1) if colours[pattern[y, x]] == 'G')
    return img[y::2, x::2].astype(np.float32) - black, white - black


def mad_sigma(d):
    return 1.4826 * float(np.median(np.abs(d - np.median(d))))


report = []
data = {'labels': [], 'raw': {}, 'final': {}, 'gain': {}, 'scale': {}}
ref_row = rows[0]
assert ref_row['seconds'] > 0.5 and ref_row['shots'] == 4
ref_files = [files(f) for f in ref_row['runs']]
refs = {}


def ref(plane):
    if plane not in refs:
        a, full = green(ref_row['runs'][0], ref_files[0][(plane, 0)])
        b, _ = green(ref_row['runs'][1], ref_files[1][(plane, 0)])
        m = (a + b) / 2
        s = cv2.GaussianBlur(m, (0, 0), 1.0)
        g = cv2.Sobel(s, cv2.CV_32F, 1, 0) ** 2 + cv2.Sobel(s, cv2.CV_32F, 0, 1) ** 2
        g = cv2.dilate(g, np.ones((5, 5), np.uint8))
        keep = g < np.percentile(g, 60)
        keep[:16, :] = keep[-16:, :] = False
        keep[:, :16] = keep[:, -16:] = False
        refs[plane] = (m / full, keep)
    return refs[plane]


report.append('1. each RAW: SNR (mean / temporal sigma) by brightness of the scene point (fraction of full scale at 0.6 s), median over planes')
report.append('   setting              ' + ''.join('%9s' % ('%.1f%%' % (100 * (lo * hi) ** 0.5)) for lo, hi in zip(BINS, BINS[1:])) +
              '   gain DN/e-  read e-   e- at 10 %   B/A level (sd over planes)')
for r in rows:
    fa, fb = files(r['runs'][0]), files(r['runs'][1])
    planes = list(range(6 if r['shots'] == 4 else 3))
    snr = np.full((len(planes), len(BINS) - 1), np.nan)
    stats = []
    scales = []
    for pi, p in enumerate(planes):
        a, full = green(r['runs'][0], fa[(p, 0)])
        b, _ = green(r['runs'][1], fb[(p, 0)])
        level, keep = ref(p)
        k = float(a[keep].sum() / b[keep].sum())
        scales.append(1 / k)
        d = a - k * b
        m = (a + k * b) / 2
        for bi, (lo, hi) in enumerate(zip(BINS, BINS[1:])):
            sel = keep & (level >= lo) & (level < hi)
            if sel.sum() < 20000:
                continue
            sig = mad_sigma(d[sel]) / np.sqrt(2)
            mean = float(m[sel].mean())
            snr[pi, bi] = mean / sig
            stats.append((mean, sig * sig))
    s = np.nanmedian(snr, axis=0)
    st = np.array(stats)
    g, r2 = np.polyfit(st[:, 0], st[:, 1], 1)
    # electrons from a scene point at 10 % of full scale in the 0.6 s ISO 100 exposure
    level10 = 0.1 * full * (r['seconds'] * r['iso']) / (ref_row['seconds'] * ref_row['iso'])
    e10 = level10 / g
    name = label(r)
    data['labels'].append(name)
    data['raw'][name] = [None if np.isnan(v) else float(v) for v in s]
    data['gain'][name] = dict(dn_per_e=float(g), read_e=float(np.sqrt(max(r2, 0)) / g), electrons_at_10pc=float(e10), seconds=r['seconds'], iso=r['iso'], shots=r['shots'])
    data['scale'][name] = [float(v) for v in scales]
    report.append('   %-20s ' % name + ''.join('%9s' % ('-' if np.isnan(v) else '%.1f' % v) for v in s) +
                  '   %9.3f  %7.2f  %10.0f   %.4f (%.4f)' % (g, np.sqrt(max(r2, 0)) / g, e10, np.median(scales), np.std(scales)))
    print(report[-1], flush=True)
data['bins'] = BINS
if '--raw-only' in sys.argv:
    pathlib.Path(str(out_json).replace('.json', '-raw.txt')).write_text('\n'.join(report) + '\n')
    out_json.write_text(json.dumps(data, indent=1) + '\n')
    sys.exit(0)

# 2. renders
env = dict(os.environ, STREHL_PIXEL_SHIFT='remosaic')
renders = {}
for r in rows:
    if r['shots'] != 4:
        continue
    name = label(r)
    for side, folder in zip('AB', r['runs']):
        tif = scratch / ('render-%s-%s.tif' % (name.replace(' ', '_').replace('/', '-'), side))
        env['STREHL_CACHE_DIR'] = str(scratch / 'cache')
        p = subprocess.run([str(EXE), 'stack', folder, '--demosaic', '--out', str(tif)], env=env, capture_output=True, text=True)
        assert p.returncode == 0, p.stderr[-2000:]
        subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', str(scratch / 'cache')], capture_output=True)
        renders[(name, side)] = tif
        print('rendered', name, side, flush=True)

T = 64


def load_green(path):
    return tifffile.imread(str(path))[..., 1].astype(np.float32)


def tiles(a):
    h, w = a.shape
    return a[:h // T * T, :w // T * T].reshape(h // T, T, w // T, T)


ref_name = label(ref_row)
ra = load_green(renders[(ref_name, 'A')])
s = cv2.GaussianBlur(ra, (0, 0), 1.0)
e = tiles(cv2.Sobel(s, cv2.CV_32F, 1, 0) ** 2 + cv2.Sobel(s, cv2.CV_32F, 0, 1) ** 2).mean(axis=(1, 3))
lev = tiles(ra).mean(axis=(1, 3))
inner = np.zeros_like(e, bool)
inner[2:-2, 2:-2] = True
flat = inner & (e <= np.percentile(e[inner], 30)) & (lev > 0.002 * 65535)
edges = np.percentile(lev[flat], [0, 33.3, 66.7, 100])
report.append('\n2. final render (four-shot, 10 planes): SNR in flat tiles (%d tiles of %d px), A render minus B render, median by brightness tertile' % (flat.sum(), T))
report.append('   tertile mean level (fraction of 16-bit full scale, 0.6 s render): ' + ', '.join('%.3f' % float(np.median(lev[flat & (lev >= lo) & (lev <= hi)]) / 65535) for lo, hi in zip(edges, edges[1:])))
for r in rows:
    if r['shots'] != 4:
        continue
    name = label(r)
    a = load_green(renders[(name, 'A')])
    b = load_green(renders[(name, 'B')])
    k = float(tiles(a).mean(axis=(1, 3))[flat].sum() / tiles(b).mean(axis=(1, 3))[flat].sum())
    d = tiles(a - k * b)
    sig = (d - d.mean(axis=(1, 3), keepdims=True)).std(axis=(1, 3)) / np.sqrt(2)
    m = tiles((a + k * b) / 2).mean(axis=(1, 3))
    snr = m / np.maximum(sig, 1e-9)
    vals = [float(np.median(snr[flat & (lev >= lo) & (lev <= hi)])) for lo, hi in zip(edges, edges[1:])]
    data['final'][name] = vals
    report.append('   %-20s dark %.1f  mid %.1f  bright %.1f   (B/A level %.4f)' % (name, vals[0], vals[1], vals[2], 1 / k))
    print(report[-1], flush=True)

# 3. crops: the strongest in-focus detail and a dark flat area, from every A render
picks = []
order = np.argsort(-np.where(inner, e, 0).ravel())
ty, tx = divmod(int(order[0]), e.shape[1])
picks.append(('detail', ty, tx))
dark_sel = flat & (lev <= edges[1])
target = float(np.median(lev[dark_sel]))
ty, tx = divmod(int(np.argmin(np.where(dark_sel, np.abs(lev - target), np.inf))), e.shape[1])
picks.append(('dark-flat', ty, tx))
C = 192
names = [label(r) for r in rows if r['shots'] == 4]
ref_level = float(np.median(lev[flat]))
report.append('\n3. crops, %d px square, 200 %% nearest neighbour, left to right: %s' % (C, ', '.join(names)))
for kind, ty, tx in picks:
    y0 = int(np.clip(ty * T + T // 2 - C // 2, 0, ra.shape[0] - C))
    x0 = int(np.clip(tx * T + T // 2 - C // 2, 0, ra.shape[1] - C))
    strip = []
    scale = None
    for name in names:
        img = tifffile.imread(str(renders[(name, 'A')]))[..., :3].astype(np.float32)
        lv = float(np.median(tiles(img[..., 1]).mean(axis=(1, 3))[flat]))
        c = img[y0:y0 + C, x0:x0 + C] * (ref_level / lv)
        if scale is None:
            scale = 0.9 / max(1e-9, float(np.percentile(c, 99.5)))
        v = (np.clip(c * scale, 0, 1) ** (1 / 2.2))[..., ::-1]
        v = cv2.resize((v * 255 + 0.5).astype(np.uint8), (2 * C, 2 * C), interpolation=cv2.INTER_NEAREST)
        v = cv2.copyMakeBorder(v, 28, 0, 0, 4, cv2.BORDER_CONSTANT, value=(255, 255, 255))
        cv2.putText(v, name, (6, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1, cv2.LINE_AA)
        strip.append(v)
    path = crops_out / ('exposure-%s-y%d-x%d.png' % (kind, y0, x0))
    cv2.imwrite(str(path), np.concatenate(strip, axis=1))
    report.append('   %s: origin y=%d x=%d' % (path.name, y0, x0))
print('\n'.join(report[-3:]))
out_json.write_text(json.dumps(data, indent=1) + '\n')
pathlib.Path(str(out_json).replace('.json', '.txt')).write_text('\n'.join(report) + '\n')
for p in renders.values():
    p.unlink()
