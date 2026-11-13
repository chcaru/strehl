"""Exact 61 MP RAW replay over the selected adapter, with/without compression."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from remote import ssh, OPTIONS, OUT, ROOT
sys.path.insert(0,str(ROOT/'experiments/sony-raw-compression-2026-11-12'))
from wire import receive,controls

DEST='/run/strehl-edup-20261112'


def snapshot():
    p=ssh("import pathlib,json,subprocess;print(json.dumps({'route':subprocess.run(['ip','route','get','10.0.0.109'],capture_output=True,text=True).stdout,'tx':{i:int(pathlib.Path('/sys/class/net/'+i+'/statistics/tx_bytes').read_text()) for i in ['wlan0','wlan1']},'load':pathlib.Path('/proc/loadavg').read_text()}))",root=True)
    assert p.returncode==0,p.stderr
    return json.loads(p.stdout)


def main():
    controls()
    code='''from pathlib import Path
import subprocess,pwd,os
p=Path('/run/strehl-edup-20261112')
assert p.resolve()==p and not p.is_symlink()
assert subprocess.run(['findmnt','-n','-o','FSTYPE','-T','/run'],capture_output=True,text=True).stdout.strip()=='tmpfs'
assert len(Path('/proc/swaps').read_text().splitlines())==1
p.mkdir(exist_ok=True);u=pwd.getpwnam('strehl');os.chown(p,u.pw_uid,u.pw_gid)
assert os.statvfs(p).f_bavail*os.statvfs(p).f_frsize>150_000_000
'''
    p=ssh(code,root=True);assert p.returncode==0,p.stderr
    source=ROOT/'outputs/sony-raw-compression-2026-11-12/inputs/pixel-shift-4/DSC01472.ARW'
    expected=hashlib.sha256(source.read_bytes()).hexdigest()
    assert expected=='453154311a136a0bb08efc4e3f0124e6d7fdc0116a5c413893a5c6b101f25c72'
    options=OPTIONS+['-o','HostKeyAlias=10.0.0.187']
    subprocess.run(['scp',*options,str(source),str(ROOT/'experiments/sony-raw-compression-2026-11-12/wire.py'),
                    'strehl@10.0.0.178:'+DEST+'/'],check=True)
    target=OUT/'raw-replays';target.mkdir(exist_ok=False)
    rows=[]
    for repeat,mode in enumerate(['identity','cfa','cfa','identity']):
        before=snapshot();assert 'dev wlan1' in before['route']
        part=target/(f'{repeat}-{mode}.partial');final=part.with_suffix('.ARW')
        start=time.perf_counter()
        proc=subprocess.Popen(['ssh',*options,'strehl@10.0.0.178',
          'python3 '+DEST+'/wire.py send --file '+DEST+'/DSC01472.ARW --mode '+mode+' --workers 4 --stats'],
          stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
        with part.open('wb') as f:
            receipt=receive(proc.stdout,f);f.flush();os.fsync(f.fileno())
        stderr=proc.stderr.read().decode();assert proc.wait(timeout=10)==0,stderr
        assert receipt['sha256']==expected
        part.replace(final);duration=time.perf_counter()-start
        assert hashlib.sha256(final.read_bytes()).hexdigest()==expected
        after=snapshot();deltas={i:after['tx'][i]-before['tx'][i] for i in before['tx']}
        assert deltas['wlan1']>=.9*receipt['wire_bytes'] and deltas['wlan0']<.1*receipt['wire_bytes']
        row={'repeat':repeat,'mode':mode,'seconds_to_durable':duration,'tx_deltas':deltas,
             'sender_stats':json.loads(stderr),'before':before,'after':after,**receipt}
        rows.append(row);(OUT/'raw-replays.json').write_text(json.dumps(rows,indent=2)+'\n')
        print(json.dumps({k:v for k,v in row.items() if k not in ['before','after','sender_stats']}),flush=True)


if __name__=='__main__':main()
