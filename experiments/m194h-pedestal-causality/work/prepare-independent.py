from pathlib import Path
import hashlib,json,time,os
r=Path.cwd();h=r/'experiments/m194h-pedestal-causality';w=h/'work';started=time.monotonic()
def read(p,cap=1<<20):
 p=Path(p);a=p.stat();assert a.st_size<=cap
 with p.open('rb') as f:
  b0=os.fstat(f.fileno());b=f.read(cap+1);b1=os.fstat(f.fileno())
 a1=p.stat();full=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_nlink)
 shared=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_nlink)
 assert full(a)==full(a1) and full(b0)==full(b1) and shared(a)==shared(b0) and len(b)==a.st_size and len(b)<=cap
 assert time.monotonic()-started<=18 and time.process_time()<=9
 return b
def ref(p,cap=1<<20):
 p=Path(p).resolve();b=read(p,cap);return dict(path=p.relative_to(r).as_posix(),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def obj(p):return json.loads(read(p))
sources=obj(w/'source-freeze-3.json')['source_bindings']
roles={'build':w/'build-release-3.json','components':w/'components-release-1.json','render':w/'render-release-1.json','subject':w/'subject-release-1.json'}
for name,p in roles.items():assert obj(p)['source_bindings']==sources,name
for p in ['work/prepare-independent.py','work/independent-release-decision.md','work/check-run.py','work/check-run-source-review.md','work/independent-windows-reader-correction-review.md','work/checker-windows-identity-source-fix.md','work/build2-source-review.md','work/checker-build2-admission-addendum.md','work/build3-source-review.md','work/checker-build3-path-addendum.md']:
 q=h/p;f=ref(q,4<<20);sources[f['path']]={k:f[k] for k in ('bytes','sha256')}
assert all(sources[k]==v for k,v in obj(w/'source-freeze-3.json')['source_bindings'].items())
for key,pin in sources.items():
 f=ref(r/key,4<<20);assert pin=={k:f[k] for k in ('bytes','sha256')},key
stem=w/'render-external-1';base=h/'subject-1'
bundle={'result':ref(base/'result.json'),'tail':ref(base/'parent-tail.json'),'outer':ref(Path(str(stem)+'-outer.json')),'stdout':ref(Path(str(stem)+'-stdout.bin')),'stderr':ref(Path(str(stem)+'-stderr.bin')),'exit':ref(Path(str(stem)+'-exit.txt'))}
assert obj(base/'result.json')['status']=='COMPLETE_STAGE_UNVERIFIED'
outer=obj(Path(str(stem)+'-outer.json'));assert outer['exit_code']==0 and not outer['timeout_terminated']
p=w/'independent-release-1.json';assert not p.exists()
py=r'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe'
value=dict(schema='m194h-independent-check-release-v1',source_bindings=sources,render=bundle,subject_grant=ref(w/'subject-release-1.json'),command=[py,'-I','-B',str(h/'independent-verify.py'),'--release',str(p),'--release-sha256','ACTUAL_RELEASE_SHA256','--source-sha256','ACTUAL_SOURCE_SHA256','--output',str(h/'independent-check-1')])
b=(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode();assert len(b)<=1<<20
with p.open('xb') as f:f.write(b);f.flush();os.fsync(f.fileno())
assert read(p)==b
proof=dict(schema='m194h-independent-release-source-equality-v1',release=ref(p),producer_roles={k:ref(v) for k,v in roles.items()},source_freeze=ref(w/'source-freeze-3.json'),all_producer_maps_equal=True,producer_map_is_checker_subset=True,producer_source_count=len(obj(w/'source-freeze-3.json')['source_bindings']),checker_source_count=len(sources),own_cpu_sample=time.process_time(),own_wall_sample=time.monotonic()-started,scope='Metadata-only construction, sampled cost with1CPU/2wall reserve; scientific checker not run.')
q=w/'independent-release-equality-1.json';assert not q.exists()
raw=(json.dumps(proof,sort_keys=True,separators=(',',':'))+'\n').encode()
with q.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
print(json.dumps(proof))
