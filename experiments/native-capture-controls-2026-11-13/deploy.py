"""Install matched controller/bridge binaries, preserving configuration and marks."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'experiments/sony-edup-2026-11-12'))
spec=importlib.util.spec_from_file_location('a7cr_deploy',ROOT/'experiments/sony-a7cr-2026-11-13/deploy.py')
api=importlib.util.module_from_spec(spec);spec.loader.exec_module(api)
OUT=ROOT/'outputs/native-capture-controls-2026-11-13'


def restore(before):
    for key,start in [('start',True),('end',False)]:
        if before[key+'_set']:
            api.command('focus',target=before['plan'][key]);api.wait(lambda s:s['editable'])
            api.command('mark',start=start)
    p=before['plan']
    api.command('settings',**{k:p[k] for k in ['step','settle_ms','approach','capture_timeout_s']})
    api.command('roi',roi=before['roi'])
    api.command('focus',target=before['position']);api.wait(lambda s:s['editable'])
    if before['shots_per_plane']!=4:
        api.command('pixel_shift',shots=before['shots_per_plane']);api.wait(lambda s:s['editable'])


def main():
    before=api.state()
    assert before['editable'] and not before['busy'] and before['storage'].get('pending_frames',0)==0
    assert not (before.get('failure') or {}).get('exposure_uncertain')
    stamp=str(int(time.time()))
    (OUT/('deployment-before-'+stamp+'.json')).write_text(json.dumps(before,indent=2)+'\n')
    stage='/home/strehl/strehl-controls-'+stamp
    r=api.ssh("from pathlib import Path\nPath("+repr(stage)+").mkdir()",host='10.0.0.178');assert r.returncode==0,r.stderr
    hashes={}
    for name in ['strehl-capture-headless','strehl-sony-ptp']:
        src=OUT/'arm64'/name;hashes[name]=hashlib.sha256(src.read_bytes()).hexdigest()
        r=subprocess.run(['scp',*api.OPTIONS,'-o','HostKeyAlias=10.0.0.187',str(src),'strehl@10.0.0.178:'+stage+'/'+name],capture_output=True,text=True)
        assert r.returncode==0,r.stderr
    api.command('disconnect');api.wait(lambda s:not s['connected'] and not s['busy'])
    code=r'''
from pathlib import Path
import json,hashlib,os,shutil,subprocess
stage=Path(STAGE);expected=HASHES
root=Path('/opt/strehl-capture');backup=Path('/root/strehl-controls-'+STAMP)
assert not list(Path('/run/strehl-raw').iterdir()),'RAM is not empty'
config=Path('/etc/strehl-capture/headless.json');original=config.read_bytes()
for name,digest in expected.items():assert hashlib.sha256((stage/name).read_bytes()).hexdigest()==digest
backup.mkdir()
for name in expected:shutil.copy2(root/name,backup/name)
subprocess.run(['systemctl','stop','strehl-capture'],check=True)
try:
 for name in expected:
  tmp=root/(name+'.controls');shutil.copy2(stage/name,tmp);os.chmod(tmp,0o755);os.replace(tmp,root/name)
 assert config.read_bytes()==original
 subprocess.run(['systemctl','start','strehl-capture'],check=True)
except BaseException:
 for name in expected:shutil.copy2(backup/name,root/name)
 subprocess.run(['systemctl','start','strehl-capture'],check=True);raise
print(json.dumps({'hashes':expected,'backup':str(backup),'configuration_preserved':config.read_bytes()==original}))
'''.replace('STAGE',repr(stage)).replace('HASHES',repr(hashes)).replace('STAMP',repr(stamp))
    r=api.ssh(code,host='10.0.0.178',root=True,timeout=55);assert r.returncode==0,r.stderr
    receipt=json.loads(r.stdout)
    api.wait(lambda s:not s['busy'])
    if not api.state()['connected']:api.command('connect')
    api.wait(lambda s:s['editable'] and not s['failure'])
    restore(before)
    after=api.state()
    assert after['plan']==before['plan'] and after['position']==before['position']
    receipt['focus_and_plan_preserved']=True
    (OUT/'deployment.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt))


if __name__=='__main__':main()
