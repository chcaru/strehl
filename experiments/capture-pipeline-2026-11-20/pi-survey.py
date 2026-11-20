"""Read-only survey of the studio Pi: hardware, network links, storage, controller state.
Prints no keys."""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'outputs/shelly-power-2026-11-18'))
from bench import state, remote  # noqa: E402

PROBE = r'''
import glob, os, subprocess
def read(p):
    try:
        return open(p).read().strip()
    except OSError:
        return ''
def sh(*a, t=15):
    try:
        r = subprocess.run(list(a), capture_output=True, text=True, timeout=t)
        return (r.stdout + r.stderr).strip()
    except Exception as e:
        return 'ERR %r' % (e,)
print('model:', read('/proc/device-tree/model').strip('\x00'))
print('mem:', [l for l in read('/proc/meminfo').splitlines() if l.split(':')[0] in ('MemTotal', 'MemAvailable')])
print('cpus:', os.cpu_count(), 'governor', read('/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor'), 'cur kHz', read('/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq'))
print('-- usb devices')
for d in sorted(glob.glob('/sys/bus/usb/devices/*')):
    if os.path.exists(d + '/speed'):
        print(' ', os.path.basename(d), read(d + '/speed'), read(d + '/idVendor') + ':' + read(d + '/idProduct'), read(d + '/product'))
print('-- net')
for n in sorted(os.listdir('/sys/class/net')):
    print(' ', n, 'state', read('/sys/class/net/%s/operstate' % n), 'speed', read('/sys/class/net/%s/speed' % n), 'carrier', read('/sys/class/net/%s/carrier' % n))
print(sh('ip', '-br', 'addr'))
print(sh('ip', 'route'))
for n in sorted(os.listdir('/sys/class/net')):
    if n.startswith('wl'):
        print('-- iw', n)
        print(sh('iw', 'dev', n, 'link'))
        print(sh('iw', 'dev', n, 'station', 'dump'))
        print(sh('iw', 'dev', n, 'info'))
print('-- df')
print(sh('df', '-h', '/', '/run/strehl-raw', '/var', '/home'))
print('-- mounts strehl:', [l for l in read('/proc/mounts').splitlines() if 'strehl' in l])
print('-- /opt/strehl-capture')
print(sh('ls', '-la', '--time-style=long-iso', '/opt/strehl-capture'))
print('-- service')
print(sh('systemctl', 'show', 'strehl-capture', '-p', 'ActiveState', '-p', 'ExecStart', '-p', 'MainPID', '-p', 'User'))
print('-- lsusb -t')
print(sh('lsusb', '-t'))
print('-- python usb modules:', sh('python3', '-c', 'import usb; print(usb.__version__)'))
print('-- uptime', read('/proc/uptime').split()[0])
'''

s = state()
keep = {k: s.get(k) for k in ('phase', 'connected', 'busy', 'message', 'usb_speed_mbps', 'error_correction', 'editable', 'failure')}
keep['power'] = {k: (v if not isinstance(v, dict) else {a: v.get(a) for a in ('on', 'watts')}) for k, v in (s.get('power') or {}).items()}
keep['storage'] = s.get('storage')
print(json.dumps(keep, indent=1)[:2500])
print('state keys:', sorted(s.keys()))
print(remote(PROBE))
