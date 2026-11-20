"""Sample the Pi's CPU (per core and the controller's processes) while the installed
controller captures a short stack.   pi-cpu.py <planes> <step>"""
import pathlib
import subprocess
import sys
import threading

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'experiments/sony-edup-2026-11-12'))
from remote import ssh  # noqa: E402

SAMPLER = r'''
import os, time
def cores():
    out = {}
    for l in open('/proc/stat'):
        if l.startswith('cpu'):
            p = l.split(); v = list(map(int, p[1:9]))
            out[p[0]] = (sum(v), v[3] + v[4])
    return out
def procs():
    out = {}
    for pid in os.listdir('/proc'):
        if pid.isdigit():
            try:
                s = open('/proc/%s/stat' % pid).read()
                name = s[s.index('(') + 1:s.rindex(')')]
                f = s[s.rindex(')') + 2:].split()
                if name.startswith('strehl'):
                    out[name] = out.get(name, 0) + int(f[11]) + int(f[12])
            except OSError:
                pass
    return out
hz = os.sysconf('SC_CLK_TCK')
a, pa, t0 = cores(), procs(), time.time()
rows = []
for i in range(SECONDS):
    time.sleep(1.0)
    b, pb = cores(), procs()
    busy = {k: 100 * (1 - (b[k][1] - a[k][1]) / max(1, b[k][0] - a[k][0])) for k in b}
    pr = {k: 100 * (pb[k] - pa.get(k, 0)) / hz for k in pb}
    rows.append((time.time() - t0, busy, pr))
    a, pa = b, pb
for t, busy, pr in rows:
    print('%5.1f s  all %3.0f%%  cores %s  | %s' % (t, busy['cpu'], ' '.join('%3.0f' % busy[k] for k in sorted(busy) if k != 'cpu'),
          ' '.join('%s %.0f%%' % (k, v) for k, v in sorted(pr.items()) if v > 0.5)))
'''
planes, step = sys.argv[1], sys.argv[2]
seconds = 12 + 8 * int(planes)
box = {}
t = threading.Thread(target=lambda: box.setdefault('r', ssh(SAMPLER.replace('SECONDS', str(seconds)), host='10.0.0.178', timeout=seconds + 40)))
t.start()
r = subprocess.run([sys.executable, str(pathlib.Path(__file__).with_name('rig.py')), 'stack', planes, step], capture_output=True, text=True)
print(r.stdout[-700:], r.stderr[-300:])
t.join()
print(box['r'].stdout, box['r'].stderr[-300:])
