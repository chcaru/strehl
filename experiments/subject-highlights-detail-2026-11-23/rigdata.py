"""Read four-shot test groups for the analyses of this folder.

A group is restored from its `.ARW.straw` archives with the product's own tool into scratch
(deleted after reading) and assembled without interpolation: every photosite gets red, green
(the mean of its two samples) and blue from the member whose shifted filter has that colour.
Member offsets are the ones `strehl pixel-shift` reports for these runs, (0,-1), (1,-1), (1,0)
for members 2-4 against member 1; `check_offsets` confirms the sign convention on the data.
"""
import json
import pathlib
import subprocess

import numpy as np
import rawpy

TOOL = pathlib.Path(r'C:\dev\blog\death-of-software\projects\strehl\target\release\strehl-raw-archive.exe')
SCRATCH = pathlib.Path(r'C:\strehl-scratch\i-round\tmp-raw')
OFFSETS = [(0, 0), (0, -1), (1, -1), (1, 0)]    # (dx, dy) of members 1-4


def groups(folder):
    """Last complete group per plane: {plane: [file names by member]}."""
    out = {}
    for line in open(pathlib.Path(folder) / 'events.jsonl', encoding='utf-8'):
        e = json.loads(line)
        if e.get('event') in ('capture_buffered', 'capture_complete'):
            r = e['data']['response']
            files = sorted(r['files'], key=lambda f: f['member_index'])
            out[files[0]['plane']] = [f['name'] for f in files]
    return out


def read(folder, name):
    SCRATCH.mkdir(parents=True, exist_ok=True)
    src = pathlib.Path(folder) / (name + '.straw')
    work = SCRATCH / ('%s-%s' % (pathlib.Path(folder).name, name))
    work.mkdir(exist_ok=True)
    subprocess.run([str(TOOL), 'restore', str(src), '--output-dir', str(work)], check=True, capture_output=True)
    with rawpy.imread(str(work / name)) as raw:
        img = raw.raw_image_visible.copy()
        black = np.array(raw.black_level_per_channel, dtype=np.float32)
        white = float(raw.white_level)
        pattern = raw.raw_pattern.copy()
        colours = raw.color_desc.decode()
    (work / name).unlink()
    work.rmdir()
    cfa = np.array([[colours[pattern[y, x]] for x in (0, 1)] for y in (0, 1)])
    return img, float(black.mean()), white, cfa


def members(folder, plane=1):
    names = groups(folder)[plane]
    return [read(folder, n) for n in names]


def assemble(ms, sign=1, crop=None):
    """RGB (H, W, 3) float32, DN above black, and a per-site clip flag (any contributing sample pinned)."""
    img0, black, white, cfa = ms[0]
    h, w = img0.shape
    y0, y1, x0, x1 = crop or (2, h - 2, 2, w - 2)
    out = np.zeros((y1 - y0, x1 - x0, 3), np.float32)
    cnt = np.zeros((y1 - y0, x1 - x0, 3), np.float32)
    pinned = np.zeros((y1 - y0, x1 - x0, 3), bool)
    yy, xx = np.mgrid[y0:y1, x0:x1]
    for (img, b, wl, _), (dx, dy) in zip(ms, OFFSETS):
        sy, sx = yy + sign * dy, xx + sign * dx
        v = img[sy, sx]
        colour = cfa[sy % 2, sx % 2]
        for i, c in enumerate('RGB'):
            m = colour == c
            out[..., i][m] += v[m].astype(np.float32) - b
            cnt[..., i][m] += 1
            pinned[..., i][m] |= v[m] >= wl - 2
    return out / np.maximum(cnt, 1), pinned, (black, white)


def check_offsets(ms):
    """Mean |G - G'| between the two green samples of each site, for both sign conventions."""
    res = {}
    img0 = ms[0][0]
    h, w = img0.shape
    crop = (h // 2 - 400, h // 2 + 400, w // 2 - 400, w // 2 + 400)
    for sign in (1, -1):
        yy, xx = np.mgrid[crop[0]:crop[1], crop[2]:crop[3]]
        greens = []
        counts = np.zeros(yy.shape, np.int32)
        for (img, b, wl, cfa), (dx, dy) in zip(ms, OFFSETS):
            sy, sx = yy + sign * dy, xx + sign * dx
            g = np.where(cfa[sy % 2, sx % 2] == 'G', img[sy, sx].astype(np.float32) - b, np.nan)
            greens.append(g)
            counts += ~np.isnan(g)
        stack = np.stack(greens)
        spread = np.nanmax(stack, 0) - np.nanmin(stack, 0)
        res[sign] = (float(np.nanmean(spread[counts == 2])), float((counts == 2).mean()))
    return res
