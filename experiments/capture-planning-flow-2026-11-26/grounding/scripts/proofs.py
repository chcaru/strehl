"""The proof planes of rig-series.py: what the capture's own plane check says of each, how the
light and the exposure ratio settle after the light comes on, and how far the picture drifts.

Per proof plane (a four-shot base group and a four-shot highlight group, each its own test run):

  check     `strehl pixel-shift --json` on each run: verdict, the members' residuals, the green
            witness pairs' shift, the local disagreement's 99th percentile
  level     the base group's member 1: mean green over the frame, against the first proof
  ratio     base / highlight member 1, the median over 8 x 8 blocks well exposed in the base
  drift     member 1 of the base group registered against the first proof's (translation and
            scale; the same green photosites, so no colour or parity term): phase correlation on
            TILE-px tiles of the green plane that hold detail, median over tiles

  python proofs.py <series folder>
"""
import json
import os
import pathlib
import subprocess
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from extract import read_raw  # noqa: E402

CLI = pathlib.Path(os.environ['LOCALAPPDATA']) / 'Programs/Strehl/strehl-cli.exe'
root = pathlib.Path(sys.argv[1])
rec = json.loads((root / 'record.json').read_text())
work = root / 'check'
work.mkdir(exist_ok=True)
env = dict(os.environ, STREHL_CACHE_DIR=str(root / 'cache'))
TILE = 256


def check(folder, name):
    out = work / (name + '.json')
    if not out.exists():
        r = subprocess.run([str(CLI), 'pixel-shift', folder, '--json', str(out)], capture_output=True, text=True, env=env)
        (work / (name + '.txt')).write_text(r.stdout + r.stderr)
    g = json.loads(out.read_text())['groups'][0]
    res = np.array(g.get('residual_px') or [], float)
    gate = g.get('gate') if isinstance(g.get('gate'), dict) else {}
    return {'verdict': g['verdict'], 'gate': gate.get('reason'), 'retake': bool(gate.get('retake')),
            'residual_px': res.round(3).tolist(), 'residual_max': float(np.abs(res).max()) if res.size else None,
            'witness_shift': np.array(g.get('witness_pair_shift_px') or [], float).round(3).tolist(),
            'local_p99': (g.get('tile_local_px') or {}).get('p99'), 'gains': np.array(g.get('gains') or [], float).round(4).tolist()}


def green(folder, name='frame-000001.ARW'):
    cache = work / (pathlib.Path(folder).name + '-' + name + '.npy')
    if cache.exists():
        return np.load(cache)
    img, black, white, cfa = read_raw(pathlib.Path(folder), name, work / ('tmp-' + pathlib.Path(folder).name))
    (work / ('tmp-' + pathlib.Path(folder).name)).rmdir()
    gy, gx = [(y, x) for y in (0, 1) for x in (0, 1) if cfa[y][x] == 'G'][0]
    g = img[gy::2, gx::2].astype(np.float32) - black
    np.save(cache, g)
    return g


def shift_of(a, b):
    """Sub-pixel translation of b against a (one tile), by phase correlation with a parabola fit."""
    wy = np.hanning(a.shape[0])[:, None]; wx = np.hanning(a.shape[1])[None, :]
    fa = np.fft.rfft2((a - a.mean()) * wy * wx); fb = np.fft.rfft2((b - b.mean()) * wy * wx)
    cross = fa * np.conj(fb)
    corr = np.fft.irfft2(cross / np.maximum(np.abs(cross), 1e-9), s=a.shape)
    py, px = np.unravel_index(np.argmax(corr), corr.shape)

    def refine(c, p, n):
        l, m, r = c[(p - 1) % n], c[p], c[(p + 1) % n]
        d = l - 2 * m + r
        return (0.5 * (l - r) / d if abs(d) > 1e-12 else 0.0)
    dy = py + refine(corr[:, px], py, corr.shape[0]); dx = px + refine(corr[py, :], px, corr.shape[1])
    if dy > a.shape[0] / 2: dy -= a.shape[0]
    if dx > a.shape[1] / 2: dx -= a.shape[1]
    return dy, dx, float(corr[py, px])


def register(ref, img, tiles):
    rows = []
    for (y, x) in tiles:
        dy, dx, peak = shift_of(ref[y:y + TILE, x:x + TILE], img[y:y + TILE, x:x + TILE])
        if peak > 0.05 and abs(dy) < 20 and abs(dx) < 20:
            rows.append((y + TILE / 2, x + TILE / 2, dy, dx))
    r = np.array(rows)
    if len(r) < 12:
        return None
    cy, cx = ref.shape[0] / 2, ref.shape[1] / 2
    # shift = t + s * (position - centre), fitted robustly: one scale for both axes
    A = np.zeros((2 * len(r), 3)); bvec = np.zeros(2 * len(r))
    A[0::2, 0] = 1; A[0::2, 2] = r[:, 0] - cy; bvec[0::2] = r[:, 2]
    A[1::2, 1] = 1; A[1::2, 2] = r[:, 1] - cx; bvec[1::2] = r[:, 3]
    keep = np.ones(len(bvec), bool)
    for _ in range(4):
        sol, *_ = np.linalg.lstsq(A[keep], bvec[keep], rcond=None)
        resid = bvec - A @ sol
        s = 1.4826 * np.median(np.abs(resid[keep] - np.median(resid[keep]))) + 1e-6
        keep = np.abs(resid) < 3 * s
    # green-plane px -> sensor px
    return {'dy_px': float(2 * sol[0]), 'dx_px': float(2 * sol[1]), 'scale_ppm': float(1e6 * sol[2]), 'tiles': int(len(r)),
            'rms_px': float(2 * np.sqrt(np.mean(resid[keep] ** 2)))}


rows = []
ref = None
tiles = None
for p in rec['proofs']:
    row = {'label': p['label'], 'after_light_s': p['after_light_s'], 'base_wall_s': p['base']['wall_s'],
           'highlight_wall_s': p['highlight']['wall_s'], 'light_watts': p['light_watts']}
    row['base_check'] = check(p['base']['folder'], p['label'] + '-base')
    row['highlight_check'] = check(p['highlight']['folder'], p['label'] + '-highlight')
    g = green(p['base']['folder'])
    h = green(p['highlight']['folder'])
    if ref is None:
        ref = g
        # tiles that hold detail and no clipped sample: by the Laplacian's energy over the level
        cand = []
        for y in range(TILE, g.shape[0] - 2 * TILE, TILE):
            for x in range(TILE, g.shape[1] - 2 * TILE, TILE):
                t = g[y:y + TILE, x:x + TILE]
                if t.max() > 12000:
                    continue
                lap = t[1:-1, :-2] + t[1:-1, 2:] + t[:-2, 1:-1] + t[2:, 1:-1] - 4 * t[1:-1, 1:-1]
                cand.append((float((lap ** 2).mean() / max(t.mean(), 30.0) ** 2), y, x))
        cand.sort(reverse=True)
        tiles = [(y, x) for _, y, x in cand[:60]]
        level0 = float(g.mean())
    row['level'] = float(g.mean() / level0)
    bm = g[:g.shape[0] // 4 * 4, :g.shape[1] // 4 * 4].reshape(g.shape[0] // 4, 4, g.shape[1] // 4, 4).mean(axis=(1, 3))
    hm = h[:h.shape[0] // 4 * 4, :h.shape[1] // 4 * 4].reshape(h.shape[0] // 4, 4, h.shape[1] // 4, 4).mean(axis=(1, 3))
    ok = (bm > 0.05 * 15871) & (bm < 0.6 * 15871)
    row['ratio'] = float(np.median(bm[ok] / hm[ok])); row['ratio_blocks'] = int(ok.sum())
    row['drift'] = register(ref, g, tiles)
    # within the proof: the highlight group's member 1 against the base group's, taken 10 s later
    row['highlight_against_base'] = register(g, h * row['ratio'], tiles)
    rows.append(row)
    d = row['drift'] or {}
    print('%-5s %5.0f s | base %s (residual max %.2f px, witness %.2f, local p99 %.2f) | highlight %s | level %.4f | ratio %.2f | drift dx %+.2f dy %+.2f px scale %+.0f ppm (%d tiles, rms %.2f)'
          % (row['label'], row['after_light_s'], row['base_check']['verdict'], row['base_check']['residual_max'] or 0,
             max(abs(v) for v in np.ravel(row['base_check']['witness_shift'])) if row['base_check']['witness_shift'] else 0,
             row['base_check']['local_p99'] or 0, row['highlight_check']['verdict'], row['level'], row['ratio'],
             d.get('dx_px', np.nan), d.get('dy_px', np.nan), d.get('scale_ppm', np.nan), d.get('tiles', 0), d.get('rms_px', np.nan)), flush=True)
(root / 'proofs.json').write_text(json.dumps(rows, indent=1))
