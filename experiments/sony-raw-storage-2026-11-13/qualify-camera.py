"""One new four-shot group, using the already qualified production API harness."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'experiments/sony-edup-2026-11-12'))
from remote import ssh
sys.path.insert(0, str(ROOT / 'experiments/sony-a7cr-2026-11-13'))
import qualify


def main():
    out = ROOT / 'outputs/sony-raw-storage-2026-11-13'
    assert not (out / 'storage-group.json').exists(), 'Never overwrite or silently repeat the physical qualification'
    p = ssh("import json,os,subprocess,pathlib;print(json.dumps({'load':os.getloadavg(),'meminfo':pathlib.Path('/proc/meminfo').read_text(),'throttled':subprocess.getoutput('vcgencmd get_throttled'),'temp':subprocess.getoutput('vcgencmd measure_temp'),'usb_tree':subprocess.getoutput('lsusb -t')}))", host='10.0.0.178', root=True, timeout=15)
    assert p.returncode == 0, p.stderr
    (out / 'host-before-group.json').write_text(p.stdout)
    qualify.OUT = out
    sys.argv = ['qualify.py', '--planes', '1', '--label', 'storage-group']
    qualify.main()


if __name__ == '__main__':
    main()
