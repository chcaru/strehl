"""Read-only: what USB speed did the camera negotiate with the Pi?

Runs a short Python script on the Pi over the workspace's SSH runner. It
reads sysfs and the kernel log; it changes nothing and powers nothing.
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'experiments/sony-edup-2026-11-12'))
from remote import ssh  # noqa: E402

REMOTE = r'''
import glob, os, subprocess
def read(p):
    try:
        return open(p).read().strip()
    except OSError:
        return ''
print('uptime:', read('/proc/uptime').split()[0], 's')
print('-- devices now (sysfs): path, speed Mbit/s, vendor:product, product')
for d in sorted(glob.glob('/sys/bus/usb/devices/*')):
    if os.path.exists(d + '/speed'):
        print(' ', os.path.basename(d), read(d + '/speed'), read(d + '/idVendor') + ':' + read(d + '/idProduct'), read(d + '/product'))
for cmd in (['lsusb', '-t'],):
    try:
        print('--', ' '.join(cmd)); print(subprocess.run(cmd, capture_output=True, text=True, timeout=10).stdout)
    except Exception as e:
        print('  failed:', e)
print('-- kernel log, USB enumerations (journalctl -k, all boots kept)')
try:
    out = subprocess.run(['journalctl', '-k', '--no-pager', '-o', 'short-iso', '--since', '2026-11-12'], capture_output=True, text=True, timeout=40).stdout
    keep = [l for l in out.splitlines() if 'usb ' in l and ('new ' in l or 'Product:' in l or 'disconnect' in l or 'Manufacturer' in l)]
    print(len(out.splitlines()), 'kernel lines;', len(keep), 'usb lines')
    # collapse: print every "new ... USB device" line whose next Product line is the camera, plus counts per day
    cam = []
    for i, l in enumerate(keep):
        if 'new ' in l:
            nxt = ' | '.join(x.split('kernel: ', 1)[-1] for x in keep[i + 1:i + 3] if 'Product:' in x or 'Manufacturer' in x)
            cam.append(l.split('+')[0][:19] + ' ' + l.split('kernel: ', 1)[-1] + '  ->  ' + nxt)
    seen = {}
    for c in cam:
        day = c[:10]; kind = c[20:].split(' USB device')[0].split('new ')[-1] + ' | ' + c.split('->')[-1].strip()
        seen.setdefault((day, kind), [0, c[11:19], c[11:19]])
        seen[(day, kind)][0] += 1; seen[(day, kind)][2] = c[11:19]
    for (day, kind), (n, first, last) in sorted(seen.items()):
        print(' ', day, first, '-', last, 'x%d' % n, kind)
except Exception as e:
    print('  failed:', e)
'''

r = ssh(REMOTE, host='10.0.0.178', root=False, timeout=70)
print(r.stdout)
if r.returncode:
    print('exit', r.returncode, r.stderr[-600:])
