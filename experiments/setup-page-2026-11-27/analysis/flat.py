"""How square a flat target lies to the sensor, from a short stack of it (results R11).

  python flat.py <run folder> <out.json>

One frame per plane (the first member of each base-exposure group, by the capture journal).
Per 64-pixel tile of the half-resolution green plane: the energy of the 4-neighbour Laplacian
over the tile's mean squared plus a floor. A tile's best focus is the vertex of a parabola
through its contrast at the plane of its maximum and the two beside it; tiles whose maximum
is at either end of the stack, or whose contrast is under a fifth of the frame's 90th
percentile, are left out. A plane, then a plane plus a bowl, is fitted to best focus against
position on the sensor (Huber weights).
"""
import json
import pathlib
import subprocess
import sys

import numpy as np
import rawpy

TOOL = r'C:\dev\blog\death-of-software\projects\strehl\target\release\strehl-raw-archive.exe'
SCRATCH = pathlib.Path(r'C:\strehl-scratch\setup-polish\tmp-raw')
run = pathlib.Path(sys.argv[1])
out = pathlib.Path(sys.argv[2])
T = 32


def planes():
    """{target position: file name of the first member of its last base-tier group}."""
    found = {}
    intent = {}
    for line in open(run / 'events.jsonl', encoding='utf-8'):
        e = json.loads(line)
        d = e['data']
        if e['event'] == 'capture_intent':
            intent = {'tier': d.get('tier', 'base'), 'target': d.get('target')}
        if e['event'] in ('capture_buffered', 'capture_complete') and intent.get('tier') == 'base':
            files = sorted(d['response']['files'], key=lambda f: f.get('member_index', 0))
            found[intent['target']] = files[0]['name']
    return dict(sorted(found.items()))


def green(name):
    SCRATCH.mkdir(parents=True, exist_ok=True)
    work = SCRATCH / name
    work.mkdir(exist_ok=True)
    subprocess.run([TOOL, 'restore', str(run / (name + '.straw')), '--output-dir', str(work)], check=True, capture_output=True)
    with rawpy.imread(str(work / name)) as raw:
        img = raw.raw_image_visible.copy()
        black = float(np.mean(raw.black_level_per_channel))
    (work / name).unlink()
    work.rmdir()
    return img[0::2, 1::2].astype(np.float32) - black


def tiles(g):
    lap = 4 * g[1:-1, 1:-1] - g[:-2, 1:-1] - g[2:, 1:-1] - g[1:-1, :-2] - g[1:-1, 2:]
    core = g[1:-1, 1:-1]
    ny, nx = lap.shape[0] // T, lap.shape[1] // T
    e = (lap[:ny * T, :nx * T] ** 2).reshape(ny, T, nx, T).mean((1, 3))
    m = core[:ny * T, :nx * T].reshape(ny, T, nx, T).mean((1, 3))
    return e / (m * m + 64.0 ** 2), m


pl = planes()
pos = np.array(list(pl.keys()), float)
stack = []
level = None
for p, name in pl.items():
    c, m = tiles(green(name))
    stack.append(c)
    level = m if level is None else level
C = np.array(stack)                     # planes x ny x nx
ny, nx = C.shape[1:]
k = C.argmax(0)
best = C.max(0)
inside = (k > 0) & (k < len(pos) - 1) & (best > 0.2 * np.percentile(best, 90)) & (level < 0.8 * 15871)
yy, xx = np.mgrid[:ny, :nx]
focus = np.full((ny, nx), np.nan)
for j, i in zip(yy[inside], xx[inside]):
    a, b, c = C[k[j, i] - 1, j, i], C[k[j, i], j, i], C[k[j, i] + 1, j, i]
    den = a - 2 * b + c
    if den < 0:
        # planes are not evenly spaced at the stack's end: use the three positions as they are
        p0, p1, p2 = pos[k[j, i] - 1], pos[k[j, i]], pos[k[j, i] + 1]
        A = np.array([[p0 * p0, p0, 1], [p1 * p1, p1, 1], [p2 * p2, p2, 1]])
        q = np.linalg.solve(A, np.array([a, b, c]))
        v = -q[1] / (2 * q[0])
        if p0 <= v <= p2:
            focus[j, i] = v
ok = np.isfinite(focus)
x = (xx[ok] + 0.5) / nx - 0.5            # -0.5 .. 0.5 across the frame width
y = (yy[ok] + 0.5) / ny - 0.5
z = focus[ok]


def fit(cols):
    A = np.stack(cols, 1)
    w = np.ones(len(z))
    for _ in range(12):
        sol, *_ = np.linalg.lstsq(A * w[:, None], z * w, rcond=None)
        r = z - A @ sol
        s = 1.4826 * np.median(np.abs(r - np.median(r))) + 1e-9
        w = np.sqrt(np.minimum(1.0, 1.345 * s / np.maximum(np.abs(r), 1e-9)))
    return sol, float(np.sqrt(np.mean(r ** 2))), float(s)


one = np.ones(len(z))
plane, rms1, mad1 = fit([one, x, y])
bowl, rms2, mad2 = fit([one, x, y, x * x + (y * ny / nx) ** 2])
half = len(z) // 2
order = np.random.default_rng(1).permutation(len(z))
halves = []
for part in (order[:half], order[half:]):
    A = np.stack([one[part], x[part], y[part]], 1)
    sol, *_ = np.linalg.lstsq(A, z[part], rcond=None)
    halves.append(sol.tolist())
res = {'run': run.name, 'positions': pos.tolist(), 'tiles': int(ny * nx), 'used': int(ok.sum()),
       'peak_at_first_plane': int((k == 0).sum()), 'peak_at_last_plane': int((k == len(pos) - 1).sum()),
       'plane': {'centre': float(plane[0]), 'across_width': float(plane[1]), 'across_height': float(plane[2]), 'rms': rms1, 'robust_sd': mad1},
       'with_bowl': {'across_width': float(bowl[1]), 'across_height': float(bowl[2]), 'bowl_at_half_width': float(bowl[3] * 0.25), 'rms': rms2},
       'random_halves': halves}
out.write_text(json.dumps(res, indent=1))
print(json.dumps(res, indent=1))
# where the usable tiles are, coarsely
grid = np.zeros((6, 9), int)
for j, i in zip(yy[ok], xx[ok]):
    grid[min(5, j * 6 // ny), min(8, i * 9 // nx)] += 1
print('usable tiles by region (6 x 9):')
print(grid)
med = np.full((6, 9), np.nan)
for a in range(6):
    for b in range(9):
        sel = ok & (yy * 6 // ny == a) & (xx * 9 // nx == b)
        if sel.sum() >= 20:
            med[a, b] = np.median(focus[sel])
print('median best focus by region:')
print(np.round(med, 1))
