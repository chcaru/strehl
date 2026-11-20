"""Power the camera on through the controller, read the USB speed it negotiated,
re-enable "manage power" if a restart reset it, then power the camera off.
The light is never switched on. Prints no keys."""
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'outputs/shelly-power-2026-11-18'))
from bench import cmd, state, wait, remote  # noqa: E402

PROBE = r'''
import glob, os, subprocess
def read(p):
    try:
        return open(p).read().strip()
    except OSError:
        return ''
for d in sorted(glob.glob('/sys/bus/usb/devices/*')):
    if os.path.exists(d + '/speed') and read(d + '/idVendor') == '054c':
        print('  sysfs', os.path.basename(d), read(d + '/speed'), 'Mbit/s', read(d + '/idProduct'), read(d + '/product'),
              'version', read(d + '/version'), 'bMaxPower', read(d + '/bMaxPower'), 'power/control', read(d + '/power/control'))
out = subprocess.run(['dmesg', '-T'], capture_output=True, text=True, timeout=20).stdout
lines = [l for l in out.splitlines() if 'usb 1-1' in l or 'usb 2-1' in l or 'xhci' in l.lower()]
for l in lines[-14:]:
    print('  ', l[:180])
'''


def show(s, label):
    p = s['power']
    print(time.strftime('%H:%M:%S'), label, '| phase', s['phase'], 'connected', s['connected'], 'busy', s['busy'],
          'manage_stack', p['manage_stack'], 'camera', p['camera']['on'], p['camera']['watts'], 'W light',
          p['light']['on'], p['light']['watts'], 'W | usb', s.get('usb_speed_mbps'), '|', s.get('message') or '', flush=True)


s = state()
show(s, 'before')
try:
    if not s['connected']:
        if not s['power']['camera']['on']:
            cmd('power', device='camera', on=True)
            show(state(), 'camera power requested')
        s = wait(lambda a: not a['busy'] and a['connected'], timeout=150)
    show(s, 'connected')
    print(remote(PROBE))
    if not s['power']['manage_stack']:
        cmd('power_plan', enabled=True)
        s = wait(lambda a: not a['busy'] and a['power']['manage_stack'])
        show(s, 'manage power re-enabled')
finally:
    s = wait(lambda a: not a['busy'], timeout=60)
    if s['power']['camera']['on'] or s['connected']:
        cmd('power', device='camera', on=False)
        s = wait(lambda a: not a['busy'] and not a['power']['camera']['on'], timeout=150)
    if s['power']['light']['on']:
        cmd('power', device='light', on=False)
        s = wait(lambda a: not a['busy'] and not a['power']['light']['on'], timeout=60)
    show(s, 'after')
