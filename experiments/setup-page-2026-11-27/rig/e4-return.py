"""E4/E5: how exactly the focus axis returns to a position, and how the picture
settles after a move. Magnified live view (1:1 with the sensor), recorded as JPEGs.

  python e4-return.py <out folder> <P> [ratio]

1. sweep 1: P-64 .. P+64 in steps of 4, from below (the fingerprint).
2. approaches to P, two frames each: from below and above by 128, 16 and 8 units,
   and from 5000 units away on each side.
3. sweep 2 (the same as 1; their difference is the drift during the test).
4. transients: every live frame for 4 s after a move of +8, +128 and -128 units.
"""
import json
import pathlib
import sys
import time

import rig
from rig import bench

out = pathlib.Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
P = int(sys.argv[2])
RATIO = int(sys.argv[3]) if len(sys.argv) > 3 else 93
log = []


def preview():
    r = bench.client.get(bench.URL + '/api/preview', timeout=7)
    if r.status_code != 200:
        return None, None
    return r.headers.get('x-preview-generation'), r.content


def fresh(count, tag, skip=1, limit=8.0):
    """Saves `count` new live frames after discarding `skip` new ones."""
    last, _ = preview()
    seen = kept = 0
    end = time.time() + limit
    while kept < count and time.time() < end:
        g, b = preview()
        if b is not None and g != last:
            last = g
            seen += 1
            if seen > skip:
                (out / ('%s-%d.jpg' % (tag, kept))).write_bytes(b)
                kept += 1
        time.sleep(0.02)
    return kept


def focus(target):
    bench.wait(lambda a: a['editable'] and not a['busy'], 60)
    bench.cmd('focus', target=target)
    bench.wait(lambda a: not a['busy'] and a.get('position') == target, 60)


def sweep(name):
    focus(P - 64 - 128)
    for p in range(P - 64, P + 65, 4):
        focus(p)
        fresh(2, '%s-%05d' % (name, p))
    log.append({'what': name, 'unix': time.time()})


def approach(kind):
    if kind == 'below128':
        focus(P - 128)
    elif kind == 'above128':
        focus(P + 128)
    elif kind == 'below16':
        focus(P - 16)
    elif kind == 'above16':
        focus(P + 16)
    elif kind == 'below8':
        focus(P - 8)
    elif kind == 'above8':
        focus(P + 8)
    elif kind == 'farbelow':
        focus(P - 5000)
    elif kind == 'farabove':
        focus(P + 5000)
    elif kind == 'farbelow+128':
        focus(P - 5000)
        focus(P - 128)
    elif kind == 'farabove+128':
        focus(P + 5000)
        focus(P - 128)
    focus(P)


def transient(kind, rep):
    start = {'+8': P - 8, '+128': P - 128, '-128': P + 128}[kind]
    focus(start)
    time.sleep(2.5)
    last, _ = preview()
    bench.wait(lambda a: a['editable'] and not a['busy'], 60)
    t0 = time.time()
    bench.cmd('focus', target=P)
    t1 = time.time()
    rows = []
    n = 0
    while time.time() - t0 < 4.5:
        g, b = preview()
        t = time.time()
        if b is not None and g != last:
            last = g
            name = 'x%s-%d-%03d.jpg' % (kind, rep, n)
            (out / name).write_bytes(b)
            rows.append({'name': name, 't': t - t0, 'generation': g})
            n += 1
        time.sleep(0.015)
    s = bench.state()
    log.append({'what': 'transient', 'kind': kind, 'rep': rep, 'posted_after': t1 - t0, 'frames': rows,
                'position': s.get('position')})


s = rig.settled()
bench.cmd('magnify', ratio=RATIO, x=320, y=240)
rig.settled()
time.sleep(1.0)
t_begin = time.time()
sweep('s1')
kinds = ['below128', 'above128', 'below16', 'above16', 'below8', 'above8']
for rep in range(6):
    for kind in kinds:
        approach(kind)
        fresh(2, 't-%s-%d' % (kind, rep))
        log.append({'what': 'approach', 'kind': kind, 'rep': rep, 'unix': time.time()})
    if rep < 4:
        for kind in ['farbelow', 'farabove', 'farbelow+128', 'farabove+128']:
            approach(kind)
            fresh(2, 't-%s-%d' % (kind, rep))
            log.append({'what': 'approach', 'kind': kind, 'rep': rep, 'unix': time.time()})
sweep('s2')
for rep in range(4):
    for kind in ['+8', '+128', '-128']:
        transient(kind, rep)
focus(P - 128)
focus(P)
bench.cmd('magnify', ratio=0, x=320, y=240)
rig.settled()
(out / 'log.json').write_text(json.dumps({'P': P, 'ratio': RATIO, 'began': t_begin, 'ended': time.time(), 'log': log}, indent=1))
print('recorded', len(list(out.glob('*.jpg'))), 'frames in %.0f s' % (time.time() - t_begin))
