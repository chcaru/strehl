from pathlib import Path
import hashlib
import json
import subprocess
import time
import uuid
import rawpy
import requests

repo = Path(__file__).resolve().parents[2]
out = repo / 'outputs/sony-capture-throughput-2026-11-11'
out.mkdir(exist_ok=True)
base = repo / 'outputs/pi-capture-2026-11-11'
cfg = json.loads((base/'private/headless.json').read_text())
url = 'http://10.0.0.187:8787'
headers = {'Authorization': 'Bearer '+cfg['pairing_key']}

def state():
    r = requests.get(url+'/api/state', headers=headers, timeout=8)
    r.raise_for_status(); return r.json()

def command(op, **args):
    s = state()
    r = requests.post(url+'/api/command', headers=headers, json={
        'id':str(uuid.uuid4()),'camera_revision':s['camera_revision'],
        'plan_revision':s['plan_revision'],'sequence_id':s['sequence_id'],
        'command':{'op':op, **args}},timeout=8)
    r.raise_for_status()

def wait(predicate, seconds=30):
    end = time.monotonic()+seconds
    while True:
        s=state()
        assert not s['failure'] or s['busy'],s['failure']
        if predicate(s):return s
        assert time.monotonic()<end,s['message']
        time.sleep(.1)

if __name__ == '__main__':
    s=state()
    if not s['connected'] and not s['busy'] and not s['failure']:
        command('connect');s=wait(lambda s:s['phase']=='ready' and s['preview']['fresh'])
    assert s['phase']=='ready' and s['editable'] and not s['start_set'] and not s['end_set']
    assert s['storage']['pending_frames']==0
    (out/'before-probe.json').write_text(json.dumps(s,indent=2)+'\n')
    command('disconnect');wait(lambda s:not s['connected'] and not s['busy'])
    ssh=['ssh','-i',str(base/'private/pi-admin-ed25519'),'-o',
         'UserKnownHostsFile='+str(base/'private/pi-known-hosts'),'-o','BatchMode=yes',
         'strehl@10.0.0.187','sudo python3 -']
    script=(Path(__file__).with_name('probe-pi.py')).read_text()
    p=subprocess.Popen(ssh,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    p.stdin.write(script);p.stdin.close()
    result=None
    for line in p.stdout:
        value=json.loads(line)
        if 'result' in value:
            result=value['result'];(out/'direct-probe.json').write_text(json.dumps(result,indent=2)+'\n')
        else:print(line.strip(),flush=True)
    error=p.stderr.read();p.wait(timeout=15)
    assert p.returncode==0,(p.returncode,error)
    assert result and len(result['frames'])==4 and not result['remaining_ram_files']
    verified=[]
    for frame in result['frames']:
        file=Path(frame['receipt']['path'])
        assert hashlib.sha256(file.read_bytes()).hexdigest()==frame['sha256']
        with rawpy.imread(str(file)) as raw:
            plane=raw.raw_image_visible.copy()
            assert plane.shape==(4688,7028)
        verified.append({'file':str(file),'bytes':file.stat().st_size,'sha256':frame['sha256'],'shape':list(plane.shape)})
    (out/'direct-raw-verification.json').write_text(json.dumps(verified,indent=2)+'\n')
    command('connect');s=wait(lambda s:s['phase']=='ready' and s['preview']['fresh'])
    (out/'after-probe.json').write_text(json.dumps(s,indent=2)+'\n')
    print(json.dumps({'verified_raws':len(verified),'camera':s['phase'],'compression':result['compression']}))
