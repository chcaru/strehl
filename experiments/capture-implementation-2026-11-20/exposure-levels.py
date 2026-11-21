"""Does the light hold still at short exposures? The brightness of every RAW of the paired
runs of exposure-quality.py (mean of the central half of the frame, green, black removed).
Within a four-shot group the four shots should agree: a pixel-shift group mixes their
samples. LED drivers that dim by pulsing flicker, and a short exposure samples less of the
cycle. Reports, per setting and run: the spread inside each group ((max - min) / mean;
median and largest over the planes) and the drift over the run.
  python exposure-levels.py <runs.json> <scratch> <out.txt>"""
import json
import pathlib
import subprocess
import sys

import numpy as np
import rawpy

ROOT = pathlib.Path(__file__).resolve().parents[2]
TOOL = ROOT / 'target/release/strehl-raw-archive.exe'
rows = json.loads(pathlib.Path(sys.argv[1]).read_text())
scratch, out = pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3])
scratch.mkdir(parents=True, exist_ok=True)


def level(folder, name):
    p = scratch / name
    if p.exists():
        p.unlink()
    subprocess.run([str(TOOL), 'restore', str(pathlib.Path(folder) / (name + '.straw')), '--output-dir', str(scratch)], check=True, capture_output=True)
    with rawpy.imread(str(p)) as raw:
        img = raw.raw_image_visible.copy()
        black = float(np.mean(raw.black_level_per_channel))
        pattern = raw.raw_pattern.copy()
        colours = raw.color_desc.decode()
    p.unlink()
    y, x = next((y, x) for y in (0, 1) for x in (0, 1) if colours[pattern[y, x]] == 'G')
    g = img[y::2, x::2]
    h, w = g.shape
    return float(g[h // 4:3 * h // 4, w // 4:3 * w // 4].mean()) - black


lines = ['setting              run   within-group spread median / max   run drift (last plane / first)   shot means relative to the group mean (shots 1-4, median over planes)']
for r in rows:
    if r['shots'] != 4:
        continue
    t = r['seconds']
    name = ('%.1f s' % t if t >= 0.3 else '1/%d s' % round(1 / t)) + ' ISO %d' % r['iso']
    for side, folder in zip('AB', r['runs']):
        groups = []
        for line in open(pathlib.Path(folder) / 'events.jsonl', encoding='utf-8'):
            e = json.loads(line)
            if e.get('event') == 'capture_buffered':
                groups.append(sorted(f['name'] for f in e['data']['response']['files']))
        lv = np.array([[level(folder, n) for n in g] for g in groups])
        spread = (lv.max(axis=1) - lv.min(axis=1)) / lv.mean(axis=1)
        rel = np.median(lv / lv.mean(axis=1, keepdims=True), axis=0)
        lines.append('%-20s %s     %.4f / %.4f                       %.4f                       %s' % (
            name, side, np.median(spread), spread.max(), lv[-1].mean() / lv[0].mean(), ' '.join('%.4f' % v for v in rel)))
        print(lines[-1], flush=True)
out.write_text('\n'.join(lines) + '\n')
