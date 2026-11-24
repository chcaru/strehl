"""Per-colour levels of test runs' first RAW (member 1): the share of each
colour's samples at the pin and its 99.9th and 99.99th percentiles, as a
share of black to white. Restores the archive into scratch and deletes it.

  python levels.py <ladder.json>
"""
import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
import rigdata  # noqa: E402

rows = json.loads(pathlib.Path(sys.argv[1]).read_text())
print('seconds   colour  pinned_share  p99.9  p99.99')
for r in rows:
    folder = r['folder']
    names = rigdata.groups(folder)
    first = names[min(names)][0]
    img, black, white, cfa = rigdata.read(folder, first)
    for colour in 'RGB':
        mask = np.zeros(img.shape, bool)
        for y in (0, 1):
            for x in (0, 1):
                if cfa[y, x] == colour:
                    mask[y::2, x::2] = True
        v = img[mask].astype(np.float32)
        pinned = float((v >= white - 2).mean())
        p3, p4 = np.percentile(v, [99.9, 99.99])
        print('%8.5f   %s     %.6f    %.3f  %.3f' % (r['seconds'], colour, pinned,
              (p3 - black) / (white - black), (p4 - black) / (white - black)))
