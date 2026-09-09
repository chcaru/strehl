"""Once-only root metadata construction; no image/executable payload read."""
from pathlib import Path
import hashlib,json,os,stat,sys,time
START=time.monotonic();CPU=time.process_time();READ=0
R=Path.cwd();H=R/'experiments/common-tiff-dimensions';W=H/'work'
def check():
 assert time.process_time()-CPU+1<=10 and time.monotonic()-START+2<=20
 assert READ<=8*(1<<20)
def ref(path,cap=262144,empty=False):
 global READ
 p=Path(path);p=p if p.is_absolute() else R/p
 for q in (p,*p.parents):
  t=q.lstat();assert not stat.S_ISLNK(t.st_mode) and not getattr(t,'st_file_attributes',0)&0x400
 t=p.stat();assert stat.S_ISREG(t.st_mode) and (0 if empty else 1)<=t.st_size<=cap
 READ+=t.st_size+1;check()
 with p.open('rb') as f:
  opened=os.fstat(f.fileno());b=f.read(t.st_size+1);closed=os.fstat(f.fileno())
 u=p.stat()
 shared=lambda q:(q.st_dev,q.st_ino,q.st_size,q.st_mtime_ns,q.st_nlink,getattr(q,'st_file_attributes',0))
 full=lambda q:shared(q)+(q.st_ctime_ns,)
 assert full(t)==full(u) and full(opened)==full(closed) and shared(t)==shared(opened) and len(b)==t.st_size
 return dict(path=p.relative_to(R).as_posix(),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def bundle(stage,number=1):
 d=H/(stage+'-'+str(number))
 prefix=('build-external-'+str(number) if stage=='build' else 'prepare-external-1' if stage=='prepare' else stage+'-recovery-external-1')
 v={k:ref(d/name) for k,name in [('result','result.json'),('tail','parent-tail.json')]}
 v.update({k:ref(W/(prefix+'-'+name),empty=k=='stderr') for k,name in [('outer','outer.json'),('stdout','stdout.bin'),('stderr','stderr.bin'),('exit','exit.txt')]})
 return v
assert len(sys.argv)==4 and R==Path('C:/dev/blog/death-of-software/projects/strehl')
release=W/'dimensions-final-read-release-1.json'
receipt=W/'dimensions-final-read-preparation-1.json'
assert not release.exists() and not receipt.exists()
sources={k:ref(H/n,131072) for k,n in [('reader','dimensions-independent-saved-read.py'),('amendment','dimensions-independent-result-recovery-amendment.md'),('review','dimensions-independent-saved-read-source-review.md')]}
assert [sources[k]['sha256'] for k in ('reader','amendment','review')]==sys.argv[1:]
index=H/'prepare-1/fixtures/index.json';index_ref=ref(index)
assert index_ref['sha256']=='d07f356bdd7b2286b88404a337afd831319130e979b9adc27222d5ad71b1bf98'
READ+=index_ref['bytes']+1;check()
with index.open('rb') as f:index_raw=f.read(index_ref['bytes']+1)
assert len(index_raw)==index_ref['bytes'] and hashlib.sha256(index_raw).hexdigest()==index_ref['sha256']
legacy=json.loads(index_raw)['legacy'];assert set(legacy)=={'index','report','manifest','output'}
exe=dict(path='experiments/common-tiff-dimensions/build-2/strehl-common-input.exe',bytes=3201536,sha256='172a52135ebee5853169cd3cd8bd8e9c97b4dc6ad5a886c20bfd57ea0a4a0684')
assert (R/exe['path']).stat().st_size==exe['bytes']
history_names=[
 ('recovery-controls-result',W/'recovery-controls-1/result.json'),
 ('recovery-controls-outer',W/'controls-recovery-external-1-outer.json'),
 ('recovery-controls-stdout',W/'controls-recovery-external-1-stdout.bin'),
 ('recovery-controls-stderr',W/'controls-recovery-external-1-stderr.bin'),
 ('recovery-controls-exit',W/'controls-recovery-external-1-exit.txt'),
 ('recovery-controls-root-capture',W/'controls-recovery-capture-root-1.json'),
 ('saved-control-review',H/'recovery-controls-result-review.md'),
 ('saved-control-review-and-finalization-receipt',W/'recovery-controls-independent-read-1.json'),
 ('recovery-source-review',H/'recovery-source-review.md'),
 ('final-saved-reader-source-review',H/'dimensions-independent-saved-read-source-review.md'),
 ('root-final-release-constructor-source',Path(__file__).resolve())]
value=dict(schema='common-tiff-dimensions-final-saved-read-release-v1',reader=sources['reader'],
 plan=ref(H/'dimensions-independent-result-plan.md',32768),amendment=sources['amendment'],
 producer_freeze=ref(W/'source-freeze-2.json'),execution_freeze=ref(W/'recovery-source-freeze-1.json'),
 stages={s:bundle(s,2 if s=='build' else 1) for s in ['build','prepare','recovery','render','verify']},
 history={'build1':bundle('build',1)},fixtures=index_ref,checker=ref(H/'verify-1/check/result.json'),
 executable=exe,legacy=legacy,profile=ref(R/'experiments/M165-common-input/linear-prophoto-d50-v1.icc',16384),
 root_captures={s:ref(W/(s+'-recovery-capture-root-1.json')) for s in ['recovery','render','verify']},
 retained_history=[dict(role=role,file=ref(p,empty='stderr' in role)) for role,p in history_names],
 output=str(W/'dimensions-independent-read-1.json'))
assert not Path(value['output']).exists() and not (W/'dimensions-independent-read-1-progress.json').exists()
raw=(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
assert len(raw)<=262144
check()
with release.open('xb') as f:assert f.write(raw)==len(raw);f.flush();os.fsync(f.fileno())
rr=ref(release);assert rr['sha256']==hashlib.sha256(raw).hexdigest()
record=dict(schema='dimensions-final-read-preparation-v1',status='PREPARED_UNRUN_RELEASE',release=rr,
 invocation=sys.orig_argv,source=ref(Path(__file__).resolve(),32768),read_bytes_sample=READ,
 cpu_sample_seconds=time.process_time()-CPU,wall_sample_seconds=time.monotonic()-START,
 reserved=dict(cpu_seconds=10,wall_seconds=20,read_bytes=8*(1<<20),retained_bytes=1<<20),
 final_allowance=dict(cpu_seconds=1,wall_seconds=2),
 scope='Root metadata binding only; original executable/image references are carried for final reader authentication, not payload-read here.')
check()
record_raw=(json.dumps(record,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
assert len(raw)+len(record_raw)<=1<<20
with receipt.open('xb') as f:assert f.write(record_raw)==len(record_raw);f.flush();os.fsync(f.fileno())
print(json.dumps(dict(release=rr,receipt=ref(receipt),read_bytes_sample=READ,status=record['status'])))
check()
