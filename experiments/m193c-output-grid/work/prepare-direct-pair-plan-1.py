"""Root metadata-only plan: preserve the executed closure; never open image payloads."""
from pathlib import Path
import argparse,hashlib,json,time
root=Path(__file__).resolve().parents[3]
h=root/'experiments/m193c-output-grid'
start=time.monotonic()
seen={}
def ref(p,sha=None):
 p=Path(p).resolve()
 assert p.is_relative_to(root) or p==Path(r'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe')
 assert p.suffix.lower() not in ('.tiff','.tif','.arw','.raw','.npy','.npz')
 a=p.stat();assert 0<a.st_size<=32*1024*1024
 raw=p.read_bytes();z=p.stat()
 assert (a.st_dev,a.st_ino,a.st_size,a.st_mtime_ns)==(z.st_dev,z.st_ino,z.st_size,z.st_mtime_ns)
 value=dict(path=p.relative_to(root).as_posix() if p.is_relative_to(root) else str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
 assert sha is None or value['sha256']==sha
 assert seen.setdefault(str(p),value)==value
 return value
def read(p,sha):
 r=ref(p,sha);raw=Path(p).read_bytes()
 assert len(raw)==r['bytes'] and hashlib.sha256(raw).hexdigest()==r['sha256']
 return r,json.loads(raw)
p=argparse.ArgumentParser()
p.add_argument('--runner-sha256',required=True);p.add_argument('--spec-sha256',required=True)
p.add_argument('--review',nargs=2,action='append',required=True)
a=p.parse_args()
rp=h/'direct-pair-plan-1.json';out=h/'direct-pair-1'
assert not rp.exists() and not out.exists()
release,old=read(h/'sensor-white-coverage-release-2.json','a6ab7a11ab053c61c12e3496414fca22b15afd31f43c642b9e6dc1d01b8b9801')
audit,checked=read(h/'work/independent-sensor-white-coverage-1-audit.json','f5372a6fc28f9a0d34cc37356374beeca266ac5539d5fb93d3d1f2ff1b7c979a')
assert checked['status']=='PASS_SAVED_COVERAGE_OUTCOME_AUDIT' and checked['subject_complete'] is False
coverage={key:ref(root/value['path'],value['sha256']) for key,value in checked['external'].items()}
assert coverage['release']==release
coverage['audit']=audit
prior,work=read(h/'work/direct-pair-prior-work-1.json','e0c9eb506b6755013e8fe98b61ae4535aaa7e05e2cb1875cdd8e507fc07412ff')
assert work==dict(cpu_seconds=368.203125,wall_seconds=402.6725757,file_bytes=3947560798,metadata_bytes=22360152)
sources=dict(old['source_bindings'])
for name,pin in ((h/'direct-pair-run.py',a.runner_sha256),(h/'direct-pair-preregister.md',a.spec_sha256),
                 (h/'work/independent-sensor-white-coverage-1-audit.py','ec4f22316255ad98e95c56ec2e07a6d7ef4301e0cc62451a79c9d9f2b66b3f44'),
                 (Path(__file__),None),*((root/name,sha) for name,sha in a.review)):
 r=ref(name,pin);v={k:r[k] for k in ('sha256','bytes')}
 assert sources.setdefault(r['path'],v)==v
for name,value in sources.items():
 r=ref(root/name,value['sha256']);assert r['bytes']==value['bytes']
python=ref(old['python_executable']['path'],old['python_executable']['sha256'])
base=[python['path'],'-B','-X','faulthandler','-X']
script=str(h/'direct-pair-run.py')
parent=base+['pycache_prefix='+str(out/'parent-cache'),script,'--plan',str(rp),'--sha256','ACTUAL_PLAN_SHA256','--output',str(out)]
worker=base+['pycache_prefix='+str(out/'worker-cache'),script,'--plan',str(rp),'--sha256','ACTUAL_PLAN_SHA256','--output',str(out/'worker'),'--worker','--request',str(out/'request.json'),'--request-sha256','ACTUAL_REQUEST_SHA256']
plan=dict(schema='m193c-direct-pair-plan-v1',source_bindings=sources,coverage=coverage,prior_work=prior,python_executable=python,commands=dict(parent=parent,worker=worker))
raw=(json.dumps(plan,sort_keys=True,indent=2)+'\n').encode()
assert len(raw)<=256*1024 and time.monotonic()-start<30 and time.process_time()<20
with rp.open('xb') as s:assert s.write(raw)==len(raw)
print(json.dumps(dict(status='PREPARED_METADATA_ONLY',plan=ref(rp),source_count=len(sources),metadata_files_checked=len(seen),image_payloads_opened=0)))
