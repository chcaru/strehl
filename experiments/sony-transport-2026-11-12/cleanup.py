"""Remove only verified owned replay RAWs from Pi RAM; retain all PC originals."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'experiments/sony-edup-2026-11-12'))
from remote import ssh
OUT=ROOT/'outputs/sony-transport-2026-11-12'
inputs=[]
for name in ['production-replays.json','production-a7c2.json']:
    inputs.extend(json.loads((OUT/name).read_text())['inputs'])
expected={Path(x['path']).name:x['sha256'] for x in inputs}
code='''from pathlib import Path
import hashlib,json,subprocess
root=Path('/run/strehl-transport-20261112');assert root.resolve()==root and not root.is_symlink()
removed=[]
for name,digest in EXPECTED.items():
 p=root/name;assert p.parent==root and p.resolve()==p and not p.is_symlink()
 assert hashlib.sha256(p.read_bytes()).hexdigest()==digest
 p.unlink();removed.append(name)
r={'removed_verified_temporary_raws':removed,'remaining_test_raws':len(list(root.glob('*.ARW'))),'production_raws_pending':len(list(Path('/run/strehl-raw').iterdir())),'swap':Path('/proc/swaps').read_text()}
for name,args in [('service',['systemctl','is-active','strehl-capture']),('route',['ip','route','get','10.0.0.109']),('throttling',['vcgencmd','get_throttled']),('memory',['free','-b'])]:
 p=subprocess.run(args,capture_output=True,text=True);r[name]=p.stdout.strip();assert p.returncode==0
r['headless_sha256']=hashlib.sha256(Path('/opt/strehl-capture/strehl-capture-headless').read_bytes()).hexdigest()
assert r['service']=='active' and r['production_raws_pending']==0 and r['remaining_test_raws']==0 and r['throttling']=='throttled=0x0'
print(json.dumps(r))
'''.replace('EXPECTED',repr(expected))
p=ssh(code,host='10.0.0.178',root=True);assert p.returncode==0,p.stderr
result=json.loads(p.stdout)
result['receiver_sha256']=hashlib.sha256((Path.home()/'AppData/Local/StrehlCaptureReceiver/strehl-capture-receiver.exe').read_bytes()).hexdigest()
assert result['headless_sha256']==json.loads((OUT/'pi-install.json').read_text())['after_sha256']
assert result['receiver_sha256'].upper()==json.loads((OUT/'receiver-install.json').read_text(encoding='utf-8-sig'))['after_sha256']
(OUT/'final-state.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
