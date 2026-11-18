"""R10: native crops of several renders side by side, one display transform.

  python -X utf8 survey-crops.py OUT.png SIZE ZOOM GAIN[,LIFT] A.tif,B.tif,... X,Y [X,Y ...]

Rows are origins (top-left corner, output pixels), columns are images. Every
crop is SIZE px, enlarged ZOOM times by pixel replication (no resampling),
shown as (value / 65535 * GAIN) ^ (1 / 2.2). With LIFT, a second copy of each
row follows it at GAIN * LIFT, to look into the shadows. Keep SIZE * ZOOM *
columns under about 1600 px so the viewer does not resample.

Optional environment: SURVEY_SAT=k multiplies colour differences from the
pixel's mean by k (to make fringes visible); the same k for every column.
"""
import os
import sys

import numpy as np
import tifffile
from PIL import Image


def main():
    out, size, zoom = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    gl = [float(v) for v in sys.argv[4].split(',')]
    gain, lift = gl[0], (gl[1] if len(gl) > 1 else None)
    files = sys.argv[5].split(',')
    origins = [tuple(int(v) for v in o.split(',')) for o in sys.argv[6:]]
    sat = float(os.environ.get('SURVEY_SAT', '1'))
    imgs = [tifffile.memmap(f) if f.endswith('.tif') else None for f in files]
    rows = []
    for x, y in origins:
        for g in ([gain] if lift is None else [gain, gain * lift]):
            cells = []
            for im in imgs:
                c = np.asarray(im[y:y + size, x:x + size]).astype(np.float32) / 65535.0
                if sat != 1.0:
                    m = c.mean(2, keepdims=True)
                    c = m + sat * (c - m)
                v = np.clip(c * g, 0, 1) ** (1 / 2.2)
                v = (v * 255 + 0.5).astype(np.uint8)
                v = v.repeat(zoom, 0).repeat(zoom, 1)
                cells.append(v)
                cells.append(np.full((v.shape[0], 4, 3), 255, np.uint8))
            rows.append(np.concatenate(cells[:-1], 1))
            rows.append(np.full((4, rows[-1].shape[1], 3), 255, np.uint8))
    Image.fromarray(np.concatenate(rows[:-1], 0)).save(out)
    print(out, 'origins', origins, 'size', size, 'zoom', zoom, 'gain', gain, 'lift', lift, 'columns', files)


if __name__ == '__main__':
    main()
