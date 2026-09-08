"""SOURCE ONLY: metadata plan for one private localization-option diagnostic."""
from pathlib import Path
from decimal import Decimal
import argparse,hashlib,json,time
root=Path(__file__).resolve().parents[3];h=root/'experiments/m193c-output-grid'
start=time.monotonic();seen={}
ALLOWANCE=dict(cpu_seconds=20,wall_seconds=30,file_bytes=1048576,metadata_bytes=1048576)
def ref(path,sha=None):
 p=Path(path).resolve()
 assert p.is_relative_to(root) or p==Path(r'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe')
 assert p.suffix.lower() in ('.json','.lock','.md','.py','.rs','.toml','.tsv','.txt') or p==Path(r'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe')
 a=p.stat();assert 0<a.st_size<=32*1024*1024
 b=p.read_bytes();z=p.stat();assert (a.st_dev,a.st_ino,a.st_size,a.st_mtime_ns)==(z.st_dev,z.st_ino,z.st_size,z.st_mtime_ns)
 r=dict(path=p.relative_to(root).as_posix() if p.is_relative_to(root) else str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
 assert sha is None or r['sha256']==sha
 assert seen.setdefault(str(p),r)==r
 return r
def read(path,sha):
 r=ref(path,sha);b=Path(path).read_bytes();assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256'];return r,json.loads(b)
p=argparse.ArgumentParser();p.add_argument('--source',nargs=2,action='append',required=True);p.add_argument('--audit-sha256',required=True);a=p.parse_args()
rp=h/'precise-upscale-plan-1.json';out=h/'precise-upscale-1';priorpath=h/'work/precise-upscale-prior-work-1.json'
assert not rp.exists() and not out.exists() and not priorpath.exists()
oldref,old=read(h/'factor-eight-plan-1.json','3d8b2c4e2e7e21d3bdc59994b2cffef3cf2687e6cf914b4a6992f52357d2e994')
auditref,audit=read(h/'work/independent-factor-eight-1-audit.json',a.audit_sha256)
assert audit['schema']=='m193c-saved-factor-eight-audit-v1' and audit['status']=='PASS_SAVED_FACTOR_EIGHT_OUTCOME_AUDIT' and audit['subject_complete'] is False
assert audit['refused_control']=='native-rotation-positive' and audit['cpu_accounting_complete'] is True
baseline={key:ref(root/value['path'],value['sha256']) for key,value in audit['external'].items()}
assert all(baseline[key]['bytes']==value['bytes'] for key,value in audit['external'].items())
assert set(baseline)=={'plan','result','outer','console','exit'} and baseline['plan']==oldref;baseline['audit']=auditref
base=dict(audit['actual_final_work'],wall_seconds=float(audit['next_wall_seconds']))
prior={k:float(Decimal(str(base[k]))+ALLOWANCE[k]) if k.endswith('seconds') else base[k]+ALLOWANCE[k] for k in ALLOWANCE}
assert prior==dict(cpu_seconds=480.390625,wall_seconds=556.2322624,file_bytes=3952852624,metadata_bytes=27651978)
priorraw=(json.dumps(prior,sort_keys=True,separators=(',',':'))+'\n').encode();priorref=dict(path=priorpath.relative_to(root).as_posix(),bytes=len(priorraw),sha256=hashlib.sha256(priorraw).hexdigest())
sources=dict(old['source_bindings'])
for name,pin in [*a.source,(str(Path(__file__)),None)]:
 r=ref(root/name,pin);v={k:r[k] for k in ('sha256','bytes')};assert sources.setdefault(r['path'],v)==v
required=('precise-upscale-run.py','precise-upscale-preregister.md','independent-precise-upscale-source-review.md','work/independent-precise-upscale-plan-preparation-read.md')
assert all((h/name).relative_to(root).as_posix() in sources for name in required)
for name,value in sources.items():
 r=ref(root/name,value['sha256']);assert r['bytes']==value['bytes']
python=ref(old['python_executable']['path'],old['python_executable']['sha256']);base=[python['path'],'-B','-X','faulthandler','-X'];script=str(h/'precise-upscale-run.py')
parent=base+['pycache_prefix='+str(out/'parent-cache'),script,'--plan',str(rp),'--sha256','ACTUAL_PLAN_SHA256','--output',str(out)]
worker=base+['pycache_prefix='+str(out/'worker-cache'),script,'--plan',str(rp),'--sha256','ACTUAL_PLAN_SHA256','--output',str(out/'worker'),'--worker','--request',str(out/'request.json'),'--request-sha256','ACTUAL_REQUEST_SHA256']
plan=dict(schema='m193c-precise-upscale-plan-v1',source_bindings=sources,factor_eight_baseline=baseline,prior_work=priorref,preparation_allowance=ALLOWANCE,python_executable=python,commands=dict(parent=parent,worker=worker))
raw=(json.dumps(plan,sort_keys=True,indent=2)+'\n').encode();assert len(raw)<=256*1024 and time.monotonic()-start<30 and time.process_time()<20
with priorpath.open('xb') as stream:assert stream.write(priorraw)==len(priorraw)
assert ref(priorpath)==priorref
with rp.open('xb') as stream:assert stream.write(raw)==len(raw)
print(json.dumps(dict(status='PREPARED_METADATA_ONLY',plan=ref(rp),prior_work=priorref,source_count=len(sources),metadata_files_checked=len(seen),image_payloads_opened=0)))
