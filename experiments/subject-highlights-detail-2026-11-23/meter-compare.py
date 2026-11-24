"""What the exposure advice sees on the whole frame against the subject mask (brief Q10).

For a few planes of a capture: per colour, the 99.9th and 99.99th percentiles and the clipped
share, over every sample (the product's metering) and over the samples inside the mask. Then the
exposure change each rule would ask for.

  python meter-compare.py <capture folder> <planes dir> <mask .npz> <ordinal> [<ordinal> ...]
"""
import json
import pathlib
import subprocess
import sys

import numpy as np
import rawpy

TOOL = pathlib.Path(r'C:\dev\blog\death-of-software\projects\strehl\target\release\strehl-raw-archive.exe')
run, pdir, mfile = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), sys.argv[3]
wanted = [int(v) for v in sys.argv[4:]]
planes = {p['ordinal']: p for p in json.loads((pdir / 'planes.json').read_text())}
mask = np.load(mfile)['mask']
scratch = pdir / 'tmp-meter'
scratch.mkdir(exist_ok=True)
TARGET = 0.9


def levels(v, white_span):
    v = np.sort(v.astype(np.float32)) / white_span
    n = len(v)
    return v[int(0.999 * n)], v[int(0.9999 * n)], float((v >= 0.995).mean()), n


print('plane | region  | colour |  p99.9  p99.99  clipped share (samples) | stops to put p99.9 at 0.9 | stops to put p99.99 at 0.9')
for o in wanted:
    name = planes[o]['files'][0]
    subprocess.run([str(TOOL), 'restore', str(run / (name + '.straw')), '--output-dir', str(scratch)], check=True, capture_output=True)
    with rawpy.imread(str(scratch / name)) as raw:
        img = raw.raw_image_visible.copy()
        black = np.array(raw.black_level_per_channel, dtype=np.float32)
        white = float(raw.white_level)
        pattern = raw.raw_pattern.copy()
        colours = raw.color_desc.decode()
    (scratch / name).unlink()
    big = np.kron(mask, np.ones((4, 4), bool))     # mask blocks are 4x4 on each half-resolution colour plane
    for region in ('frame', 'subject'):
        allv = []
        for c in 'RGB':
            parts = []
            for y in (0, 1):
                for x in (0, 1):
                    if colours[pattern[y, x]] != c:
                        continue
                    plane = img[y::2, x::2].astype(np.float32) - black[pattern[y, x]]
                    hh, ww = min(plane.shape[0], big.shape[0]), min(plane.shape[1], big.shape[1])
                    plane = plane[:hh, :ww]
                    parts.append(plane[big[:hh, :ww]] if region == 'subject' else plane.ravel())
            v = np.concatenate(parts)
            allv.append(v)
            a, b, clip, n = levels(v, white - float(black.mean()))
            print('%5d | %-7s | %s      | %6.3f  %6.3f  %.5f %% (%d) | %+5.2f | %+5.2f' % (
                o, region, c, a, b, 100 * clip, round(clip * n), np.log2(TARGET / max(a, 1e-6)), np.log2(TARGET / max(b, 1e-6))))
        a, b, clip, n = levels(np.concatenate(allv), white - float(black.mean()))
        print('%5d | %-7s | all    | %6.3f  %6.3f  %.5f %% (%d) | %+5.2f | %+5.2f   <- the product meters "frame, all"' % (
            o, region, a, b, 100 * clip, round(clip * n), np.log2(TARGET / max(a, 1e-6)), np.log2(TARGET / max(b, 1e-6))))
scratch.rmdir()
