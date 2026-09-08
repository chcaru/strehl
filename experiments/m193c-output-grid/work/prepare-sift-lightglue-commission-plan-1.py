"""Metadata/opaque-hash preparation for the first SIFT-LightGlue private commission."""
from pathlib import Path
from decimal import Decimal, ROUND_CEILING
import argparse,hashlib,json,time
root=Path(__file__).resolve().parents[3];h=root/'experiments/m193c-output-grid'
start=time.monotonic();seen={}
ALLOWANCE=dict(cpu_seconds=20,wall_seconds=30,file_bytes=1048576,metadata_bytes=1048576)
def ref(path,sha=None):
 p=Path(path).resolve();py=Path(r'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe')
 assert p.is_relative_to(root) or p==py
 assert p.suffix.lower() in ('.json','.lock','.md','.py','.rs','.toml','.tsv','.txt','.log') or p==py or p==h/'lightglue-acquisition-1/sift-lightglue.pth'
 a=p.stat();assert 0<=a.st_size<=64*1024*1024
 digest=hashlib.sha256();size=0
 with p.open('rb') as stream:
  while b:=stream.read(1024*1024):digest.update(b);size+=len(b)
 z=p.stat();assert (a.st_dev,a.st_ino,a.st_size,a.st_mtime_ns)==(z.st_dev,z.st_ino,z.st_size,z.st_mtime_ns) and size==a.st_size
 r=dict(path=p.relative_to(root).as_posix() if p.is_relative_to(root) else str(p),bytes=size,sha256=digest.hexdigest())
 assert sha is None or r['sha256']==sha
 assert seen.setdefault(str(p),r)==r
 return r
def read(path,sha=None):
 r=ref(path,sha);assert r['bytes']<=8*1024*1024
 b=Path(path).read_bytes();assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256']
 return r,json.loads(b)
p=argparse.ArgumentParser();p.add_argument('--source',nargs=2,action='append',required=True);p.add_argument('--audit-sha256',required=True);a=p.parse_args()
rp=h/'sift-lightglue-commission-plan-1.json';out=h/'sift-lightglue-commission-1';priorpath=h/'work/sift-lightglue-commission-prior-work-1.json'
assert not rp.exists() and not out.exists() and not priorpath.exists()
oldref,old=read(h/'lightglue-acquisition-plan-1.json','0302f5d4f963e734ee2f2d7d13841e06640e86e736ab47ed2fa1d469817af52d')
auditref,audit=read(h/'work/independent-lightglue-acquisition-audit.json',a.audit_sha256)
assert audit['schema']=='m193c-saved-lightglue-acquisition-audit-v1' and audit['status']=='PASS_SAVED_LIGHTGLUE_ACQUISITION_OUTCOME_AUDIT'
assert audit['subject_complete'] is True and audit['admission_allowed'] is True and audit['cpu_accounting_complete'] is True and all(audit['caps'].values())
baseline={key:ref(root/value['path'],value['sha256']) for key,value in audit['external'].items()}
assert all(baseline[key]['bytes']==value['bytes'] for key,value in audit['external'].items())
assert set(baseline)=={'plan','result','outer','console','exit'} and baseline['plan']==oldref;baseline['audit']=auditref
_,actual=read(root/baseline['result']['path'],baseline['result']['sha256'])
assert actual['status']=='COMPLETE_SOURCE_AND_CHECKPOINT_ACQUISITION_ONLY' and actual['errors']==[]
assert actual['charged_work']==audit['actual_final_work']
# Independently published audit PASS alone does not establish its launcher exited or fit its final tail.
auditouterref,auditouter=read(h/'work/independent-lightglue-acquisition-audit-outer.json')
stderrref=ref(h/'work/independent-lightglue-acquisition-audit-stderr.txt')
assert auditouter['exit_code']==0 and auditouter['stderr_bytes']==stderrref['bytes']==0 and auditouter['stdout_bytes']==auditref['bytes']
assert auditouter['command']==[old['python_executable']['path'],'-B',str(h/'work/independent-lightglue-acquisition-audit.py'),
 *sum(([f'--{key}-sha256',baseline[key]['sha256']] for key in ('plan','result','outer','console','exit')),[])]
assert auditouter['elapsed_wall_seconds']<=audit['audit_timing']['wall_seconds']+audit['audit_publication_allowance']['wall_seconds']
area4={k:ref(root/v['path'],v['sha256']) for k,v in old['area4_baseline'].items()}
assert all(area4[k]['bytes']==v['bytes'] for k,v in old['area4_baseline'].items()) and set(area4)==set(baseline)
base=dict(audit['actual_final_work']);base['wall_seconds']=Decimal(audit['next_wall_seconds']).quantize(Decimal('0.000001'),rounding=ROUND_CEILING)
prior={k:float(Decimal(str(base[k]))+ALLOWANCE[k]) if k.endswith('seconds') else base[k]+ALLOWANCE[k] for k in ALLOWANCE}
assert prior==dict(cpu_seconds=679.9375,wall_seconds=907.919086,file_bytes=4037605052,metadata_bytes=46344118)
priorraw=(json.dumps(prior,sort_keys=True,separators=(',',':'))+'\n').encode()
priorref=dict(path=priorpath.relative_to(root).as_posix(),bytes=len(priorraw),sha256=hashlib.sha256(priorraw).hexdigest())
sources=dict(old['source_bindings'])
for name,pin in [*a.source,(str(Path(__file__)),None),
 (str(h/'work/independent-lightglue-acquisition-audit-outer.json'),auditouterref['sha256'])]:
 r=ref(root/name,pin);v={k:r[k] for k in ('sha256','bytes')};assert sources.setdefault(r['path'],v)==v
for asset in actual['assets']:
 r=ref(root/asset['path'],asset['sha256']);assert r['bytes']==asset['bytes']
 if asset['id']!='checkpoint':
  v={k:r[k] for k in ('sha256','bytes')};assert sources.setdefault(r['path'],v)==v
required=('sift-lightglue-commission-run.py','sift-lightglue-adapter.py','sift-lightglue-commission-preregister.md',
 'work/independent-sift-lightglue-commission-source-review.md','work/independent-sift-lightglue-commission-audit.py',
 'work/independent-sift-lightglue-plan-preparation-read.md')
assert all((h/name).relative_to(root).as_posix() in sources for name in required)
for name,value in sources.items():
 r=ref(root/name,value['sha256']);assert r['bytes']==value['bytes']
python=ref(old['python_executable']['path'],old['python_executable']['sha256']);base=[python['path'],'-B','-X','faulthandler','-X'];script=str(h/'sift-lightglue-commission-run.py')
parent=base+['pycache_prefix='+str(out/'parent-cache'),script,'--plan',str(rp),'--sha256','ACTUAL_PLAN_SHA256','--output',str(out)]
worker=base+['pycache_prefix='+str(out/'worker-cache'),script,'--plan',str(rp),'--sha256','ACTUAL_PLAN_SHA256','--output',str(out/'worker'),'--worker','--request',str(out/'request.json'),'--request-sha256','ACTUAL_REQUEST_SHA256']
plan=dict(schema='m193c-sift-lightglue-commission-plan-v1',source_bindings=sources,area4_baseline=area4,acquisition_receipt=baseline,
 prior_work=priorref,preparation_allowance=ALLOWANCE,python_executable=python,commands=dict(parent=parent,worker=worker))
raw=(json.dumps(plan,sort_keys=True,indent=2)+'\n').encode();assert len(raw)<=256*1024 and time.monotonic()-start<30 and time.process_time()<20
with priorpath.open('xb') as stream:assert stream.write(priorraw)==len(priorraw)
assert ref(priorpath)==priorref
with rp.open('xb') as stream:assert stream.write(raw)==len(raw)
print(json.dumps(dict(status='PREPARED_METADATA_AND_OPAQUE_HASHES_ONLY',plan=ref(rp),prior_work=priorref,source_count=len(sources),
 metadata_files_checked=len(seen),image_payloads_opened=0,checkpoint_parses=0)))
