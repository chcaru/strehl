"""Read-only: the Pi's USB devices now, this boot's USB kernel lines, the controller state."""
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
print('kernel:', read('/proc/version')[:120])
print('-- devices now (sysfs): path, speed Mbit/s, vendor:product, product')
for d in sorted(glob.glob('/sys/bus/usb/devices/*')):
    if os.path.exists(d + '/speed'):
        print(' ', os.path.basename(d), read(d + '/speed'), read(d + '/idVendor') + ':' + read(d + '/idProduct'), read(d + '/product'))
print('-- root hub ports: link state / disable / connect_type')
for p in sorted(glob.glob('/sys/bus/usb/devices/usb*/*-0:1.0/usb*-port*')):
    print(' ', p.split('/')[-1], 'state=' + read(p + '/state'), 'disable=' + read(p + '/disable'),
          'connect_type=' + read(p + '/connect_type'), 'over_current=' + read(p + '/over_current_count'),
          'early_stop=' + read(p + '/early_stop'), 'quirks=' + read(p + '/quirks'), 'usb3_lpm=' + read(p + '/usb3_lpm_permit'))
out = subprocess.run(['dmesg', '-T'], capture_output=True, text=True, timeout=20).stdout
lines = [l for l in out.splitlines() if 'usb' in l.lower() or 'xhci' in l.lower()]
print('-- dmesg usb/xhci lines this boot:', len(lines))
for l in lines[-80:]:
    print(' ', l[:200])
'''

r = ssh(REMOTE, host='10.0.0.178', root=False, timeout=70)
print(r.stdout)
if r.returncode:
    print('exit', r.returncode, r.stderr[-600:])
