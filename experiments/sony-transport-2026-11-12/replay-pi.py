"""Production Rust sender -> installed HTTP receiver; originals remain untouched."""
import hashlib
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
import requests
import psutil

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'experiments/sony-edup-2026-11-12'))
from remote import ssh,OPTIONS,BASE
OUT=ROOT/'outputs/sony-transport-2026-11-12'
BIN='/home/strehl/strehl-transport-20261112'
RAM='/run/strehl-transport-20261112'


def remote(code,root=False,timeout=60):
    p=ssh(code,host='10.0.0.178',root=root,timeout=timeout)
    assert p.returncode==0,p.stderr
    return json.loads(p.stdout)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--case',choices=['all','61mp','a7c2'],default='all');parser.add_argument('--label',default='production-replays');args=parser.parse_args()
    assert args.label.replace('-','').isalnum()
    receipt_file=OUT/(args.label+'.json');assert not receipt_file.exists(),'Use a fresh evidence label'
    cfg=json.loads((BASE/'private/headless.json').read_text())
    r=requests.get('http://10.0.0.178:8787/api/state',headers={'Authorization':'Bearer '+cfg['pairing_key']},timeout=8)
    r.raise_for_status();s=r.json()
    assert not s['busy'] and not s['pending_control'] and s['storage']['pending_frames']==0
    setup=remote('''from pathlib import Path
import json,subprocess,os,pwd
b=Path('/home/strehl/strehl-transport-20261112');r=Path('/run/strehl-transport-20261112')
assert b.resolve()==b and r.resolve()==r and not b.is_symlink() and not r.is_symlink()
assert subprocess.run(['findmnt','-n','-o','FSTYPE','-T','/run'],capture_output=True,text=True).stdout.strip()=='tmpfs'
assert len(Path('/proc/swaps').read_text().splitlines())==1
assert not list(Path('/run/strehl-raw').iterdir())
assert os.statvfs('/run').f_bavail*os.statvfs('/run').f_frsize>450_000_000
user=pwd.getpwnam('strehl')
for p in [b,r]:p.mkdir(mode=0o700,exist_ok=True);os.chown(p,user.pw_uid,user.pw_gid)
c=b/'transfer.json';c.write_text(json.dumps(json.loads(Path('/etc/strehl-capture/headless.json').read_text())['transfer']))
os.chmod(c,0o600);os.chown(c,user.pw_uid,user.pw_gid)
print(json.dumps({'tmpfs':True,'swap_disabled':True,'camera_queue_empty':True}))
''',root=True)
    sources=[('61mp',ROOT/'outputs/sony-raw-compression-2026-11-12/inputs/pixel-shift-4/DSC01472.ARW'),
             ('a7c2',Path(r'D:\StrehlCaptures\stack-1794546666339-2273\frame-000001.ARW'))]
    sources=[(label,p) for label,p in sources if args.case in ['all',label]]
    assert all(p.is_file() for _,p in sources),'A requested input is missing'
    options=OPTIONS+['-o','HostKeyAlias=10.0.0.187']
    binary=OUT/'arm64/transfer-probe'
    subprocess.run(['scp',*options,str(binary),'strehl@10.0.0.178:'+BIN+'/transfer-probe'],check=True)
    binary_sha=hashlib.sha256(binary.read_bytes()).hexdigest()
    check=remote("import os,hashlib,json;os.chmod('"+BIN+"/transfer-probe',0o700);print(json.dumps({'sha256':hashlib.sha256(open('"+BIN+"/transfer-probe','rb').read()).hexdigest()}))")
    assert check['sha256']==binary_sha
    rows=[];stamp=str(int(time.time()*1000));inputs=[]
    for label,source in sources:
        expected=hashlib.sha256(source.read_bytes()).hexdigest()
        inputs.append({'label':label,'path':str(source),'sha256':expected,'bytes':source.stat().st_size})
        subprocess.run(['scp',*options,str(source),'strehl@10.0.0.178:'+RAM+'/'+source.name],check=True)
        for repeat,identity in enumerate([True,False,False,True]):
            run='stack-transport-bench-'+stamp+'-'+label+'-'+str(repeat)
            args=[BIN+'/transfer-probe','--config',BIN+'/transfer.json','--file',RAM+'/'+source.name,'--run',run]
            if identity:args.append('--identity')
            pc_load=psutil.cpu_percent(interval=.1)
            code='''import json,subprocess,resource,time
from pathlib import Path
def snap():
 return {'load':Path('/proc/loadavg').read_text(),'temperature_mC':int(Path('/sys/class/thermal/thermal_zone0/temp').read_text()),'tx':{i:int(Path('/sys/class/net/'+i+'/statistics/tx_bytes').read_text()) for i in ['wlan0','wlan1']},'route':subprocess.run(['ip','route','get','10.0.0.109'],capture_output=True,text=True).stdout}
before=snap();p=subprocess.run(ARGS,capture_output=True,text=True,timeout=110);after=snap()
assert p.returncode==0,p.stderr
r=resource.getrusage(resource.RUSAGE_CHILDREN)
print(json.dumps({'command':ARGS,'result':json.loads(p.stdout),'before':before,'after':after,'max_rss_KiB':r.ru_maxrss,'user_cpu_s':r.ru_utime,'system_cpu_s':r.ru_stime}))
'''.replace('ARGS',repr(args))
            row=remote(code,timeout=125)
            receipt=row['result']['receipt'];path=Path(receipt['path'])
            assert receipt['sha256']==expected and receipt['durable'] and path.stat().st_size==source.stat().st_size
            assert hashlib.sha256(path.read_bytes()).hexdigest()==expected
            assert receipt['encoding']==('identity' if identity else 'strehl-raw-v1')
            tx={i:row['after']['tx'][i]-row['before']['tx'][i] for i in ['wlan0','wlan1']}
            assert tx['wlan1']>=receipt['wire_bytes']*.9 and tx['wlan0']<receipt['wire_bytes']*.1
            row.update({'label':label,'repeat':repeat,'identity':identity,'pc_cpu_percent_before':pc_load,'source_sha256':expected,'pc_reread_exact':True,'tx_deltas':tx})
            rows.append(row)
            receipt_file.write_text(json.dumps({'setup':setup,'probe_sha256':binary_sha,'inputs':inputs,'rows':rows},indent=2)+'\n')
            print(json.dumps({'label':label,'identity':identity,'total_seconds':row['result']['total_seconds'],'upload_seconds':receipt['upload_seconds'],'wire_bytes':receipt['wire_bytes'],'original_bytes':receipt['bytes'],'max_rss_MiB':row['max_rss_KiB']/1024,'exact':True}),flush=True)


if __name__=='__main__':main()
