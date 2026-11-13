"""Copy public samples/code to isolated tmpfs and run one bounded benchmark."""
from pathlib import Path
import argparse,json,subprocess,urllib.request
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'outputs/pi-capture-2026-11-11'
OUT=ROOT/'outputs/sony-raw-compression-2026-11-12'
OPTS=['-i',str(BASE/'private/pi-admin-ed25519'),'-o',
      'UserKnownHostsFile='+str(BASE/'private/pi-known-hosts'),'-o','BatchMode=yes']
DEST='/run/strehl-compression-20261112'
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--prepare-only',action='store_true');args=parser.parse_args()
    cfg=json.loads((BASE/'private/headless.json').read_text())
    request=urllib.request.Request('http://10.0.0.187:8787/api/state',
        headers={'Authorization':'Bearer '+cfg['pairing_key']})
    with urllib.request.urlopen(request,timeout=5) as response:state=json.load(response)
    assert state.get('busy') is False and state.get('phase')=='ready', 'Run only while the camera app is ready and idle'
    setup="""from pathlib import Path
import os,pwd,subprocess
p=Path('/run/strehl-compression-20261112')
assert not p.is_symlink() and p.resolve()==p and p.parent==Path('/run')
assert subprocess.run(['findmnt','-n','-o','FSTYPE','-T','/run'],capture_output=True,text=True,check=True).stdout.strip()=='tmpfs'
assert len(Path('/proc/swaps').read_text().splitlines())==1, 'This fixture requires swap disabled'
p.mkdir(exist_ok=True)
account=pwd.getpwnam('strehl');os.chown(p,account.pw_uid,account.pw_gid)
assert os.statvfs(p).f_bavail*os.statvfs(p).f_frsize >= 260_000_000, 'Insufficient free experiment RAM'
"""
    subprocess.run(['ssh',*OPTS,'strehl@10.0.0.187','sudo python3 -'],input=setup,text=True,check=True)
    subprocess.run(['ssh',*OPTS,'strehl@10.0.0.187','mkdir -p /home/strehl/strehl-compression-probe'],check=True)
    subprocess.run(['scp',*OPTS,str(OUT/'libpredict.so'),'strehl@10.0.0.187:/home/strehl/strehl-compression-probe/'],check=True)
    files=[OUT/'inputs/pixel-shift-4/DSC01472.ARW',
           OUT/'inputs/pixel-shift-4/DSC01473.ARW',Path(__file__).with_name('pi-bench.py')]
    subprocess.run(['scp',*OPTS,*map(str,files),'strehl@10.0.0.187:'+DEST+'/'],check=True)
    if args.prepare_only:
        print('Public RAM fixtures and native library prepared; no camera operation')
        raise SystemExit(0)
    with (OUT/'pi-bench-v3.jsonl').open('w',encoding='utf-8') as log:
        p=subprocess.run(['ssh',*OPTS,'strehl@10.0.0.187','python3 '+DEST+'/pi-bench.py'],
                         stdout=log,stderr=subprocess.PIPE,text=True,timeout=600)
    print('pi_bench_exit',p.returncode);print(p.stderr);assert p.returncode==0
