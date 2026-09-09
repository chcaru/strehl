from pathlib import Path
import ast,hashlib,io,json,time,zipfile
start=time.monotonic();cpu=time.process_time();r=Path.cwd();h=r/'experiments/common-tiff-dimensions';w=h/'work'
read_bytes=0
def read(p,cap):
 global read_bytes
 n=p.stat().st_size
 assert 0<n<=cap and read_bytes+n<=16<<20
 b=p.read_bytes();read_bytes+=len(b);assert len(b)==n
 return b
def pin(b):return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
base=read(w/'source-freeze-1.json',64<<10);assert pin(base)['sha256']=='7b37fe67c8cee38e655d461ee9c5b498b60808b834d2b97d61ee3be9a76b6de4'
freeze=json.loads(base);archive=read(w/'source-1.zip',8<<20);assert pin(archive)['sha256']=='0dbe11b91a4351e041bff97201506600fee03ab3b37bf1b32e5b34cd63016770'
names=['run-stage.py','bounded-build-process.py','prepare-release.py','capture-stage.py','run-stage-contract.md','independent-controls.py','independent-spec.md']
changes={};current={}
with zipfile.ZipFile(io.BytesIO(archive)) as z:
 for name in names:
  key='experiments/common-tiff-dimensions/'+name
  old=z.read(key);read_bytes+=len(old);assert pin(old)==freeze['source_bindings'][key]
  new=read(h/name,128<<10);current[name]=pin(new)
  if name.endswith('.py'):
   def functions(b):
    return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(b).body if isinstance(n,ast.FunctionDef)}
   a,b=functions(old),functions(new)
   changes[name]=dict(unchanged=[k for k in a if k in b and a[k]==b[k]],changed=[k for k in a if k in b and a[k]!=b[k]],added=sorted(set(b)-set(a)),removed=sorted(set(a)-set(b)))
  else:
   changes[name]=dict(old_bytes=len(old),new_bytes=len(new),append_only=new.startswith(old))
  if name=='bounded-build-process.py':
   assert new.count(b'target/common-tiff-dimensions-2')==1 and new.replace(b'target/common-tiff-dimensions-2',b'target/common-tiff-dimensions-1')==old
  if name=='independent-controls.py':
   assert new.count(b'build-2/strehl-common-input.exe')==1 and new.replace(b'build-2/strehl-common-input.exe',b'build-1/strehl-common-input.exe')==old
  if name=='independent-spec.md':assert new.startswith(old)
assert changes['run-stage.py']['changed']==['authority'] and len(changes['run-stage.py']['unchanged'])==16
assert changes['prepare-release.py']['changed']==['source_map','archive_sources','main'] and changes['prepare-release.py']['added']==['base_sources']
assert changes['capture-stage.py']['changed']==['main']
extras=['scratch-scan.py','scratch-scan-controls.py','scratch-scan-spec.md','scratch-control-capture.py','scratch-scan-rationale.md','build2-source-addendum.md']
for n in extras:current[n]=pin(read(h/n,128<<10))
sample=dict(cpu_seconds=time.process_time()-cpu,wall_seconds=time.monotonic()-start,read_bytes=read_bytes)
assert sample['cpu_seconds']+1<=5 and sample['wall_seconds']+2<=10 and read_bytes<=16<<20
record=dict(schema='dimensions-build2-root-source-audit-v1',source_only=True,base_freeze=pin(base),base_archive=pin(archive),current=current,changes=changes,sample=sample,reservation=dict(cpu_seconds=5,wall_seconds=10,read_bytes=16<<20,written_bytes=1<<20),scope='Root independently compares producer code choices against preserved source1; no candidate import, control, compiler, fixture or product.')
data=(json.dumps(record,sort_keys=True,indent=2)+'\n').encode()
assert len(data)<1<<20
with (w/'build2-root-source-read.json').open('xb') as f:f.write(data)
print(json.dumps(dict(record=pin(data),sample=sample,changes=changes)))
