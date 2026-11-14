"""Install an idle A7CR controller with rollback, preserving LAN keys and RAWs."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import uuid
import requests

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'experiments/sony-edup-2026-11-12'))
from remote import ssh, OPTIONS, BASE

OUT = ROOT / 'outputs/sony-a7cr-2026-11-13'
URL = 'http://10.0.0.178:8787'
CONFIG = json.loads((BASE / 'private/headless.json').read_text())
AUTH = {'Authorization': 'Bearer ' + CONFIG['pairing_key']}


def state():
    r = requests.get(URL + '/api/state', headers=AUTH, timeout=8)
    r.raise_for_status()
    return r.json()


def command(op, **values):
    s = state()
    r = requests.post(URL + '/api/command', headers=AUTH, json={
        'id': str(uuid.uuid4()), 'camera_revision': s['camera_revision'],
        'plan_revision': s['plan_revision'], 'sequence_id': s['sequence_id'],
        'command': {'op': op, **values}}, timeout=8)
    r.raise_for_status()
    return r.json()


def wait(predicate, timeout=45):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        try:
            s = state()
            if predicate(s): return s
        except requests.RequestException: pass
        time.sleep(.25)
    raise RuntimeError('Controller state timeout')


def main():
    before = state()
    assert not before['busy'] and before['storage'].get('pending_frames', 0) == 0
    assert not (before.get('failure') or {}).get('exposure_uncertain')
    if before['connected']:
        command('disconnect')
        wait(lambda s: not s['connected'] and not s['busy'])
    p = ssh("from pathlib import Path\nPath('/home/strehl/strehl-a7cr-20261113').mkdir(exist_ok=True)", host='10.0.0.178')
    assert p.returncode == 0, p.stderr
    hashes = {}
    for name in ['strehl-capture-headless', 'strehl-sony-ptp']:
        f = OUT / 'arm64' / name
        hashes[name] = hashlib.sha256(f.read_bytes()).hexdigest()
        r = subprocess.run(['scp', *OPTIONS, '-o', 'HostKeyAlias=10.0.0.187', str(f),
            'strehl@10.0.0.178:/home/strehl/strehl-a7cr-20261113/' + name], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
    code = r'''
from pathlib import Path
import json,hashlib,subprocess,shutil,os
hashes=EXPECTED
stage=Path('/home/strehl/strehl-a7cr-20261113')
root=Path('/opt/strehl-capture')
config=Path('/etc/strehl-capture/headless.json')
mount=Path(r'/etc/systemd/system/run-strehl\x2draw.mount')
backup=Path('/root/strehl-a7cr-20261113')
assert not list(Path('/run/strehl-raw').iterdir()),'RAM contains files; no deployment'
for name,digest in hashes.items():assert hashlib.sha256((stage/name).read_bytes()).hexdigest()==digest
backup.mkdir(exist_ok=True)
for src,name in [(root/'strehl-capture-headless','headless-before'),(config,'headless.json'),(mount,'ram.mount')]:
 if not (backup/name).exists():shutil.copy2(src,backup/name)
original=config.read_bytes()
subprocess.run(['systemctl','stop','strehl-capture'],check=True)
try:
 for name in hashes:
  tmp=root/(name+'.candidate');shutil.copy2(stage/name,tmp);os.chmod(tmp,0o755);os.replace(tmp,root/name)
 c=json.loads(original);c['bridge']=str(root/'strehl-sony-ptp');config.write_text(json.dumps(c,indent=2)+'\n')
 text=mount.read_text();assert 'size=512M' in text or 'size=1G' in text
 mount.write_text(text.replace('size=512M','size=1G'))
 subprocess.run(['mount','-o','remount,size=1G','/run/strehl-raw'],check=True)
 subprocess.run(['systemctl','daemon-reload'],check=True)
 subprocess.run(['systemctl','start','strehl-capture'],check=True)
except BaseException:
 shutil.copy2(backup/'headless-before',root/'strehl-capture-headless');config.write_bytes(original)
 subprocess.run(['systemctl','start','strehl-capture'],check=True);raise
print(json.dumps({'binaries':hashes,'bridge':c['bridge'],'ram_mount':'1 GiB tmpfs,noswap','backup':str(backup),'keys_preserved':json.loads(original)['pairing_key']==c['pairing_key'],'receiver_preserved':json.loads(original)['transfer']==c['transfer']}))
'''.replace('EXPECTED', repr(hashes))
    p = ssh(code, host='10.0.0.178', root=True, timeout=55)
    assert p.returncode == 0, p.stderr
    install = json.loads(p.stdout)
    (OUT / 'install.json').write_text(json.dumps(install, indent=2) + '\n')
    wait(lambda s: not s['busy'])
    if not state()['connected']: command('connect')
    after = wait(lambda s: s['editable'] and s['preview']['fresh'] and not s['failure'])
    (OUT / 'connected.json').write_text(json.dumps(after, indent=2) + '\n')
    print(json.dumps({'install': install, 'phase': after['phase'], 'focus': after['position'],
                     'preview': after['preview'], 'shots_per_plane': after['shots_per_plane']}))


if __name__ == '__main__': main()
