"""Is the lens capped? Camera on, a live frame with the light off, then with the light on for
a few seconds. A capped lens stays dark with the light on.

  python capcheck.py          leaves the camera on when capped, off otherwise
"""
import io
import json
import sys
import time

import numpy as np
from PIL import Image

sys.path.insert(0, 'C:/dev/blog/death-of-software/projects/strehl/.claude/worktrees/calibration-page-spec/experiments/setup-page-2026-11-27/rig')
import rig  # noqa: E402
from rig import bench  # noqa: E402


def live():
    last = None
    for _ in range(40):
        r = bench.client.get(bench.URL + '/api/preview', timeout=7)
        if r.status_code == 200:
            g = r.headers.get('x-preview-generation')
            if last is not None and g != last:
                im = np.asarray(Image.open(io.BytesIO(r.content)).convert('L'), float)
                return float(im.mean()), float(np.percentile(im, 99.9))
            last = g
        time.sleep(0.15)
    return None, None


s = bench.state()
if not (s['power']['camera'] or {}).get('on'):
    bench.cmd('power', device='camera', on=True)
    time.sleep(3)
    bench.wait(lambda a: not a['busy'], 150)
s = bench.state()
if not s['connected']:
    bench.cmd('connect')
    bench.wait(lambda a: a['connected'] and not a['busy'], 120)
s = rig.settled()
was_light = bool(s['power']['light']['on'])
off = live() if not was_light else (None, None)
if not was_light:
    bench.cmd('power', device='light', on=True)
    bench.wait(lambda a: not a['busy'], 60)
    time.sleep(4)
on = live()
if not was_light:
    bench.cmd('power', device='light', on=False)
    bench.wait(lambda a: not a['busy'], 60)
capped = on[0] is not None and on[0] < 4 and on[1] < 16
print(json.dumps({'light_off': off, 'light_on': on, 'capped': capped, 'unix': time.time()}))
if not capped:
    s = rig.settled()
    bench.cmd('power', device='camera', on=False)
    time.sleep(2)
    bench.wait(lambda a: not a['busy'], 120)
    print('camera off again')
