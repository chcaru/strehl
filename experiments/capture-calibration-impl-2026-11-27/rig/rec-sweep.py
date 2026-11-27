"""Record a live sweep (33 positions, the pass's window) as preview JPEGs, two per position.

  python rec-sweep.py <out folder> [first] [last]
"""
import hashlib
import pathlib
import sys
import time

sys.path.insert(0, 'C:/dev/blog/death-of-software/projects/strehl/outputs/shelly-power-2026-11-18')
import bench  # noqa: E402

out = pathlib.Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
first = int(sys.argv[2]) if len(sys.argv) > 2 else 29662
last = int(sys.argv[3]) if len(sys.argv) > 3 else 35662
positions = [first + (last - first) * i // 32 for i in range(33)]


def focus(target):
    bench.ready()
    bench.cmd('focus', target=target)
    bench.wait(lambda a: not a['busy'] and a.get('position') == target, 40)


def preview():
    return bench.client.get(bench.URL + '/api/preview', timeout=7).content


focus(positions[0] - 128)
t0 = time.time()
for p in positions:
    before = hashlib.md5(preview()).hexdigest()
    focus(p)
    seen, kept, last_hash = 0, 0, before
    end = time.time() + 6
    while kept < 2 and time.time() < end:
        b = preview()
        h = hashlib.md5(b).hexdigest()
        if h not in (last_hash, before):
            last_hash = h
            seen += 1
            if seen >= 2:
                (out / ('%05d-%d.jpg' % (p, kept))).write_bytes(b)
                kept += 1
        time.sleep(0.03)
print('swept', len(positions), 'positions in %.1f s' % (time.time() - t0))
