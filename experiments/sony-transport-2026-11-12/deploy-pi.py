"""Replace only the idle Pi service executable; preserve configuration and rollback."""
import hashlib,json,subprocess,sys,time,uuid
from pathlib import Path
import requests
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'experiments/sony-edup-2026-11-12'))
from remote import ssh,OPTIONS,BASE
OUT=ROOT/'outputs/sony-transport-2026-11-12'
URL='http://10.0.0.178:8787'
CFG=json.loads((BASE/'private/headless.json').read_text())
AUTH={'Authorization':'Bearer '+CFG['pairing_key']}


def state():
    r=requests.get(URL+'/api/state',headers=AUTH,timeout=8);r.raise_for_status();return r.json()


def command(op):
    s=state();r=requests.post(URL+'/api/command',headers=AUTH,json={'id':str(uuid.uuid4()),
        'camera_revision':s['camera_revision'],'plan_revision':s['plan_revision'],
        'sequence_id':s['sequence_id'],'command':{'op':op}},timeout=8);r.raise_for_status()


def wait(predicate):
    end=time.monotonic()+40
    while time.monotonic()<end:
        try:
            s=state()
            if predicate(s):return s
        except requests.RequestException:pass
        time.sleep(.25)
    raise TimeoutError('Camera service did not reach expected state')


def main():
    before=state()
    assert not before['busy'] and before['pending_control']==0 and before['storage']['pending_frames']==0
    assert not before['start_set'] and not before['end_set'],'Preserve newly selected user bounds'
    assert before['phase'] in ['ready','complete','stopped'] and not before['failure']
    (OUT/'camera-before-deploy.json').write_text(json.dumps(before,indent=2)+'\n')
    binary=OUT/'arm64/strehl-capture-headless'
    digest=hashlib.sha256(binary.read_bytes()).hexdigest()
    staging='/home/strehl/strehl-transport-20261112/strehl-capture-headless'
    subprocess.run(['scp',*OPTIONS,'-o','HostKeyAlias=10.0.0.187',str(binary),'strehl@10.0.0.178:'+staging],check=True)
    command('disconnect');wait(lambda s:not s['connected'] and not s['busy'])
    code='''import pathlib,hashlib,subprocess,shutil,os,json
p=pathlib.Path('/opt/strehl-capture/strehl-capture-headless')
c=pathlib.Path('/etc/strehl-capture/headless.json')
new=pathlib.Path('/home/strehl/strehl-transport-20261112/strehl-capture-headless')
backup=pathlib.Path('/root/strehl-transport-20261112/headless-before')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(new)==EXPECTED
assert not list(pathlib.Path('/run/strehl-raw').iterdir())
assert not backup.exists(),'Rollback already exists; inspect before repeating'
backup.parent.mkdir(mode=0o700,exist_ok=True);shutil.copy2(p,backup)
old=sha(p);config=sha(c);assert sha(backup)==old
subprocess.run(['systemctl','stop','strehl-capture'],check=True)
try:
 candidate=p.with_suffix('.transport-new');shutil.copyfile(new,candidate);candidate.chmod(0o755);os.replace(candidate,p)
 subprocess.run(['systemctl','start','strehl-capture'],check=True)
 assert sha(c)==config and sha(p)==EXPECTED
except BaseException:
 shutil.copy2(backup,p);subprocess.run(['systemctl','start','strehl-capture'],check=True);raise
print(json.dumps({'before_sha256':old,'after_sha256':sha(p),'configuration_preserved':True,'backup':str(backup),'service':subprocess.run(['systemctl','is-active','strehl-capture'],capture_output=True,text=True).stdout.strip()}))
'''.replace('EXPECTED',repr(digest))
    p=ssh(code,host='10.0.0.178',root=True,timeout=60)
    assert p.returncode==0,p.stderr
    install=json.loads(p.stdout);assert install['service']=='active'
    (OUT/'pi-install.json').write_text(json.dumps(install,indent=2)+'\n')
    wait(lambda s:not s['busy'])
    if not state()['connected']:command('connect')
    after=wait(lambda s:s['connected'] and s['editable'] and s['preview']['fresh'] and not s['failure'])
    assert after['position']==before['position'] and after['storage']['pending_frames']==0
    assert not after['start_set'] and not after['end_set']
    (OUT/'camera-after-deploy.json').write_text(json.dumps(after,indent=2)+'\n')
    print(json.dumps({'install':install,'phase':after['phase'],'position':after['position'],'preview_fresh':after['preview']['fresh'],'pending':0}))


if __name__=='__main__':main()
