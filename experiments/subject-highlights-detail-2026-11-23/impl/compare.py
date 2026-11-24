"""Compare render arms made by render.py (shd-q-restore).

  python compare.py <out root> <arm a> <arm b> <capture name> [...]

Per capture: whether the linear master is byte-identical, whether the photograph's pixels are
identical (its TIFF Software tag carries the build id, so its bytes differ between builds), the
optical-restore log lines (cutoffs; system -> restored (target) at 0.2/0.3/0.4 cycles/px per
channel) and the desktop's event line, for both arms.
"""
import json
import pathlib
import re
import sys

import numpy as np
import tifffile

root, a, b = pathlib.Path(sys.argv[1]), sys.argv[2], sys.argv[3]
for name in sys.argv[4:]:
    ra, rb = root / a / name, root / b / name
    ja, jb = json.loads((ra / 'run.json').read_text()), json.loads((rb / 'run.json').read_text())
    same_master = ja.get('master.tiff') == jb.get('master.tiff')
    pa, pb = tifffile.imread(ra / 'result.tiff'), tifffile.imread(rb / 'result.tiff')
    same_pixels = pa.shape == pb.shape and np.array_equal(pa, pb)
    print('== %s: master bytes %s, photograph pixels %s (%s vs %s)' % (
        name, 'IDENTICAL' if same_master else 'differ', 'IDENTICAL' if same_pixels else 'differ', a, b))
    if not same_pixels and pa.shape == pb.shape:
        d = np.abs(pa.astype(np.int64) - pb.astype(np.int64))
        print('   photograph: %.2f %% of samples differ, max |diff| %d of %d' % (100 * (d > 0).mean(), d.max(), np.iinfo(pa.dtype).max))
    for arm, r in ((a, ra), (b, rb)):
        log = (r / 'render.log').read_text(encoding='utf-8', errors='replace')
        for line in log.splitlines():
            m = re.match(r'\s+([RGB]): cutoff ([\d.]+).*system -> restored \(target\) MTF at 0\.2/0\.3/0\.4 (.*?); kernel', line)
            if m:
                print('   %-4s %s cutoff %s  system->restored (target) at 0.2/0.3/0.4: %s' % (arm, m.group(1), m.group(2), m.group(3)))
            if 'cutoffs R/G/B' in line or 'NOT APPLIED' in line:
                print('   %-4s %s' % (arm, line.strip()[:230]))
            if 'event=optical-restore' in line:
                print('   %-4s %s' % (arm, line.strip()))
