"""Through-focus measures of every base plane, per 16 x 16 sensor-pixel block.

Reads the green site planes written by extract.py. For each plane, on the green plane above black
(half resolution: 1 px = 2 sensor px), block sums over 8 x 8 px:

  lap2     the 4-neighbour Laplacian squared: what `strehl focus-step` sums per tile
  mid2     difference of Gaussians, sigma 1.5 and 3 px, squared: a mid band
  low2     difference of Gaussians, sigma 3 and 6 px, squared: a low band
  mean     the mean level
  lap2m    lap2 over pixels farther than 12 px from any sample above BRIGHT of full scale
  nm       how many pixels of the block lap2m counted
  bright   pixels above BRIGHT of full scale
  pin      pixels at the raw pin

Writes one float32 array (planes, H/8, W/8) per measure and the planes' focus positions.

  python curves.py <planes folder> <out folder> [workers]
"""
import concurrent.futures as cf
import json
import pathlib
import sys

import numpy as np
from scipy import ndimage

BLOCK = 8
BRIGHT = 0.5
KEEP_AWAY = 12
NAMES = ['lap2', 'mid2', 'low2', 'mean', 'lap2m', 'nm', 'bright', 'pin']


def block(a):
    h, w = a.shape[0] // BLOCK * BLOCK, a.shape[1] // BLOCK * BLOCK
    return a[:h, :w].reshape(h // BLOCK, BLOCK, w // BLOCK, BLOCK).sum(axis=(1, 3), dtype=np.float64).astype(np.float32)


def one(path):
    z = np.load(path)
    meta = json.loads(str(z['meta']))
    g = z['g'].astype(np.float32) - meta['black']
    full = meta['white'] - meta['black']
    lap = np.zeros_like(g)
    lap[1:-1, 1:-1] = g[1:-1, :-2] + g[1:-1, 2:] + g[:-2, 1:-1] + g[2:, 1:-1] - 4 * g[1:-1, 1:-1]
    lap2 = lap * lap
    s1 = ndimage.gaussian_filter(g, 1.5)
    s2 = ndimage.gaussian_filter(g, 3.0)
    s3 = ndimage.gaussian_filter(g, 6.0)
    bright = g > BRIGHT * full
    pin = z['g'] >= meta['white'] - 2
    near = ndimage.binary_dilation(bright, iterations=KEEP_AWAY) if bright.any() else bright
    away = ~near
    out = [block(lap2), block((s1 - s2) ** 2), block((s2 - s3) ** 2), block(g) / BLOCK ** 2,
           block(lap2 * away), block(away.astype(np.float32)), block(bright.astype(np.float32)),
           block(pin.astype(np.float32))]
    return meta['plane'], meta['focus'], out


def main():
    src, dst = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else 12
    dst.mkdir(parents=True, exist_ok=True)
    paths = sorted(src.glob('base-*.npz'))
    cubes, focus = None, np.zeros(len(paths), np.int32)
    with cf.ThreadPoolExecutor(workers) as pool:
        for i, (plane, f, out) in enumerate(pool.map(one, paths)):
            if cubes is None:
                cubes = [np.zeros((len(paths),) + out[0].shape, np.float32) for _ in NAMES]
            for cube, a in zip(cubes, out):
                cube[i] = a
            focus[i] = f
            if (i + 1) % 25 == 0:
                print(i + 1, 'of', len(paths), flush=True)
    for name, cube in zip(NAMES, cubes):
        np.save(dst / (name + '.npy'), cube)
    np.save(dst / 'focus.npy', focus)
    print('written', cubes[0].shape, 'focus', focus[0], focus[-1])


if __name__ == '__main__':
    main()
