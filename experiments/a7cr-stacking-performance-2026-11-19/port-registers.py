"""Camera on through the controller; as root read the xHCI port registers (debugfs),
the kernel command line, package history and controller backups; camera off.
The light is never switched on. Prints no keys."""
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'outputs/shelly-power-2026-11-18'))
from bench import cmd, state, wait  # noqa: E402
sys.path.insert(0, str(ROOT / 'experiments/sony-edup-2026-11-12'))
from remote import ssh  # noqa: E402

PROBE = r'''
import glob, os, subprocess
def read(p):
    try:
        return open(p).read().strip()
    except OSError as e:
        return '(%s)' % e.strerror
if not os.path.isdir('/sys/kernel/debug/usb'):
    subprocess.run(['mount', '-t', 'debugfs', 'none', '/sys/kernel/debug'])
for p in sorted(glob.glob('/sys/kernel/debug/usb/xhci/*/ports/port*/portsc')):
    print('  ', p.split('/xhci/')[1], read(p))
for d in sorted(glob.glob('/sys/bus/usb/devices/*')):
    if os.path.exists(d + '/speed') and read(d + '/idVendor') == '054c':
        print('  sysfs', os.path.basename(d), read(d + '/speed'), read(d + '/idProduct'), read(d + '/product'))
print('cmdline:', read('/proc/cmdline'))
print('-- modprobe.d / udev rules mentioning usb')
for f in glob.glob('/etc/modprobe.d/*') + glob.glob('/etc/udev/rules.d/*'):
    t = read(f)
    if 'usb' in t.lower() or 'xhci' in t.lower():
        print('  ', f, '|', t.replace('\n', ' ; ')[:300])
print('-- config.txt usb/otg/current lines')
for l in read('/boot/firmware/config.txt').splitlines():
    if any(k in l.lower() for k in ('usb', 'otg', 'current', 'dwc', 'pcie')):
        print('  ', l)
print('-- apt/dpkg 13-16 Nov')
for f in ('/var/log/apt/history.log', '/var/log/dpkg.log'):
    for l in read(f).splitlines():
        if l.startswith(('Start-Date: 2026-11-1', 'Commandline', 'Upgrade', 'Install')) or l[:10] in ('2026-11-13', '2026-11-14', '2026-11-15', '2026-11-16'):
            if 'status' not in l:
                print('  ', l[:220])
print('-- /root and /opt/strehl-capture entries (mtime)')
for d in ('/root', '/opt/strehl-capture'):
    for e in sorted(os.scandir(d), key=lambda e: e.stat().st_mtime):
        print('  ', subprocess.run(['date', '-d', '@%d' % e.stat().st_mtime, '+%F %T %Z'], capture_output=True, text=True).stdout.strip(), d + '/' + e.name)
'''


def show(s, label):
    p = s['power']
    print(time.strftime('%H:%M:%S'), label, '| phase', s['phase'], 'connected', s['connected'],
          'manage_stack', p['manage_stack'], 'camera', p['camera']['on'], 'light', p['light']['on'], flush=True)


s = state()
show(s, 'before')
try:
    if not s['connected']:
        cmd('power', device='camera', on=True)
        s = wait(lambda a: not a['busy'] and a['connected'], timeout=150)
    show(s, 'connected')
    time.sleep(2)
    r = ssh(PROBE, host='10.0.0.178', root=True, timeout=90)
    print(r.stdout)
    if r.returncode:
        print('exit', r.returncode, r.stderr[-800:])
finally:
    s = wait(lambda a: not a['busy'], timeout=60)
    if s['power']['camera']['on'] or s['connected']:
        cmd('power', device='camera', on=False)
        s = wait(lambda a: not a['busy'] and not a['power']['camera']['on'], timeout=150)
    if s['power']['light']['on']:
        cmd('power', device='light', on=False)
        s = wait(lambda a: not a['busy'] and not a['power']['light']['on'], timeout=60)
    show(s, 'after')
