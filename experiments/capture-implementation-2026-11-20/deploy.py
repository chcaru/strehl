"""Install the round-4 controller and bridge on the studio Pi, with a backup and automatic
rollback; or roll back to a backup.

usage: deploy.py install <arm64 folder> | rollback <backup dir>
Install also raises the RAW tmpfs to 2 GiB (unit file and a live remount) unless it is
already that size; rollback leaves the tmpfs as it is. Refuses unless the controller is
idle with nothing pending. Prints no keys. Writes install-<stamp>.json here.
"""
import hashlib
import json
import pathlib
import subprocess
import sys
import time

OUT = pathlib.Path(__file__).resolve().parent
ROOT = OUT.parent.parent
sys.path.insert(0, str(ROOT / 'outputs/shelly-power-2026-11-18'))
from bench import HOST, OPTIONS, cmd, state, wait, remote  # noqa: E402

NAMES = ['strehl-capture-headless', 'strehl-sony-ptp']


def record(name, data):
    (OUT / name).write_text(json.dumps(data, indent=2) + '\n', encoding='utf8')


def idle_state():
    s = state()
    assert not s['busy'] and not s['failure'], s['message']
    assert s['phase'] not in ('capturing', 'paused', 'scanning'), s['phase']
    assert not (s.get('storage') or {}).get('pending_frames'), 'RAWs pending'
    assert ((s.get('schedule') or {}).get('job') or {}).get('stage') not in ('armed', 'running'), 'stack scheduled'
    return s


INSTALL = r'''
import hashlib,json,os,pathlib,shutil,subprocess,time,urllib.request
P=pathlib.Path
directory=P('/opt/strehl-capture')
cfg=json.loads(P('/etc/strehl-capture/headless.json').read_bytes())
ram=P(cfg['transfer']['ram_directory']);queue=P(cfg['transfer']['state_directory'])
def idle():
 assert not list(ram.iterdir()) and not list((queue/'pending-transfers').glob('*')) and not (queue/'pending-transfer.json').exists()
def svc(op):subprocess.run(['systemctl',op,'strehl-capture'],check=True)
def healthy():
 for _ in range(80):
  try:
   req=urllib.request.Request('http://127.0.0.1:8787/api/state',headers={'Authorization':'Bearer '+cfg['pairing_key']})
   with urllib.request.urlopen(req,timeout=2) as response:s=json.load(response)
   if isinstance(s.get('power'),dict):return s
  except OSError:pass
  time.sleep(.25)
 raise RuntimeError('controller failed readiness')
idle()
if MODE=='install':
 for n,d in DIGESTS.items():assert hashlib.sha256((P(STAGE)/n).read_bytes()).hexdigest()==d
 backup=P('/root')/('strehl-before-round4-'+STAMP);backup.mkdir(mode=0o700)
 for n in DIGESTS:shutil.copy2(directory/n,backup/n)
 source=P(STAGE)
else:
 backup=P(BACKUP);source=backup
mount=P('/etc/systemd/system/run-strehl\\x2draw.mount')
svc('stop')
try:
 idle()
 for n in NAMES:
  tmp=directory/(n+'.round4-new')
  if tmp.exists():tmp.unlink()
  shutil.copy2(source/n,tmp);os.chmod(tmp,0o755);os.replace(tmp,directory/n)
 if MODE=='install':
  text=mount.read_text()
  if 'size=2G' not in text:
   assert 'size=1G' in text
   mount.write_text(text.replace('size=1G','size=2G'))
   subprocess.run(['systemctl','daemon-reload'],check=True)
   subprocess.run(['mount','-o','remount,size=2G','/run/strehl-raw'],check=True)
 svc('start');healthy()
except BaseException:
 if MODE=='install':
  svc('stop')
  for n in NAMES:
   tmp=directory/(n+'.round4-new');shutil.copy2(backup/n,tmp);os.replace(tmp,directory/n)
  svc('start')
 raise
if MODE=='install':shutil.rmtree(STAGE)
size=[l.split()[1] for l in open('/proc/mounts') if ' /run/strehl-raw ' in l]
print(json.dumps(dict(sha256={n:hashlib.sha256((directory/n).read_bytes()).hexdigest() for n in NAMES},backup=str(backup),mount=size)))
'''


def run(mode, arg):
    base = idle_state()
    stamp = str(int(time.time()))
    prelude = f'MODE={mode!r}\nSTAMP={stamp!r}\nNAMES={NAMES!r}\n'
    digests = {}
    if mode == 'install':
        src = pathlib.Path(arg)
        digests = {n: hashlib.sha256((src / n).read_bytes()).hexdigest() for n in NAMES}
        stage = '/home/strehl/round4-' + stamp
        remote(f'import pathlib\npathlib.Path({stage!r}).mkdir()')
        for n in NAMES:
            subprocess.run(['scp', *OPTIONS, '-o', 'HostKeyAlias=10.0.0.187', str(src / n),
                            'strehl@' + HOST + ':' + stage + '/' + n], check=True)
        prelude += f'STAGE={stage!r}\nDIGESTS={digests!r}\n'
    else:
        prelude += f'BACKUP={arg!r}\n'
    record(f'{mode}-input-{stamp}.json', {k: base.get(k) for k in
           ('phase', 'connected', 'position', 'plan', 'start_set', 'end_set', 'shots_per_plane', 'power')})
    was_connected = base['connected']
    if was_connected:
        cmd('disconnect', from_state=base)
        wait(lambda s: not s['busy'] and not s['connected'])
    result = json.loads(remote(prelude + INSTALL, root=True))
    if mode == 'install':
        assert result['sha256'] == digests, result
    record(f'{mode}-{stamp}.json', result)
    s = wait(lambda s: not s['busy'], timeout=90)
    if was_connected:
        cmd('connect')
        s = wait(lambda s: not s['busy'] and s['connected'], timeout=120)
    print(mode, json.dumps(result), '| phase', s['phase'], 'connected', s['connected'],
          'usb', s.get('usb_speed_mbps'), 'manage', s['power'].get('manage_stack'), flush=True)


if __name__ == '__main__':
    run(sys.argv[1], sys.argv[2])
