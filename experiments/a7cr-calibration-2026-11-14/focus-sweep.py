"""Find a subject's focus range from the live preview (bounds for plan capture 3).

Moves focus monotonically from LOW to HIGH in STEP units (approached from below,
as the controller's plan does), grabs a fresh preview at each position and
records a per-tile sharpness (mean squared Laplacian of the preview's luma over
a grid of tiles). Restores the starting focus. Preview JPEGs are compressed and
only 1024 px wide, so this locates depth coarsely; it does not measure depth of
field at the sensor's resolution.

  python -X utf8 focus-sweep.py --low 61265 --high 62865 --step 40 --out sweep.json
"""
import argparse
import io
import json
import time

import numpy as np
import requests
from PIL import Image

import darks

api = darks.api


def preview_after(generation):
    for _ in range(60):
        s = api.state()
        p = s['preview']
        if p['generation'] > generation + 1 and p['fresh']:
            r = requests.get(api.URL + '/api/preview', headers=api.AUTH, timeout=10)
            r.raise_for_status()
            return p['generation'], np.asarray(Image.open(io.BytesIO(r.content)).convert('L'), float)
        time.sleep(0.25)
    raise RuntimeError('no fresh preview')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--low', type=int, required=True)
    ap.add_argument('--high', type=int, required=True)
    ap.add_argument('--step', type=int, required=True)
    ap.add_argument('--grid', default='8x6')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    gx, gy = map(int, a.grid.split('x'))
    before = darks.settled()
    rows = []
    try:
        api.command('focus', target=a.low - 200)
        darks.settled()
        for pos in range(a.low, a.high + 1, a.step):
            api.command('focus', target=pos)
            s = darks.settled()
            gen, im = preview_after(s['preview']['generation'])
            lap = (4 * im[1:-1, 1:-1] - im[:-2, 1:-1] - im[2:, 1:-1] - im[1:-1, :-2] - im[1:-1, 2:]) ** 2
            h, w = lap.shape
            tiles = [[float(lap[y * h // gy:(y + 1) * h // gy, x * w // gx:(x + 1) * w // gx].mean())
                      for x in range(gx)] for y in range(gy)]
            rows.append({'target': pos, 'position': s['position'], 'tiles': tiles, 'mean': float(im.mean())})
            print(pos, s['position'], round(float(lap.mean()), 1), flush=True)
    finally:
        api.command('focus', target=before['position'] - 200)
        darks.settled()
        api.command('focus', target=before['position'])
        print('restored', darks.settled()['position'])
    json.dump({'grid': [gx, gy], 'rows': rows}, open(a.out, 'w'), indent=1)


if __name__ == '__main__':
    main()
