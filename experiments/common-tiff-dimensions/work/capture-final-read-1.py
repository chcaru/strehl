"""Direct once-only raw capture for the final saved reader, not a product runner."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,time
R=Path.cwd();W=R/'experiments/common-tiff-dimensions/work'
assert len(sys.argv)==4
release=Path(sys.argv[1]);release_sha=sys.argv[2];reader_sha=sys.argv[3]
reader=R/'experiments/common-tiff-dimensions/dimensions-independent-saved-read.py'
assert release==W/'dimensions-final-read-release-1.json'
def bounded_source(p,cap):
 size=p.stat().st_size
 assert 0<size<=cap
 with p.open('rb') as f:raw=f.read(size+1)
 assert len(raw)==size
 return raw
assert hashlib.sha256(bounded_source(release,262144)).hexdigest()==release_sha
assert hashlib.sha256(bounded_source(reader,131072)).hexdigest()==reader_sha
paths={k:W/('dimensions-final-read-external-1-'+v) for k,v in [('stdout','stdout.bin'),('stderr','stderr.bin'),('exit','exit.txt'),('outer','outer.json')]}
assert all(not p.exists() for p in paths.values())
command=[sys.executable,'-I','-S','-B',str(reader),'--release',str(release),'--release-sha256',release_sha,'--source-sha256',reader_sha]
timedout=False
with paths['stdout'].open('xb') as out,paths['stderr'].open('xb') as err:
 started=time.monotonic()
 child=subprocess.Popen(command,cwd=R,stdin=subprocess.DEVNULL,stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW)
 try:code=child.wait(timeout=60)
 except subprocess.TimeoutExpired:
  timedout=True;child.kill();code=child.wait(timeout=5)
 elapsed=time.monotonic()-started
 out.flush();os.fsync(out.fileno());err.flush();os.fsync(err.fileno())
with paths['exit'].open('xb') as f:f.write((str(code)+'\n').encode());f.flush();os.fsync(f.fileno())
def ref(p,cap):
 size=p.stat().st_size
 assert 0<=size<=cap
 with p.open('rb') as f:b=f.read(size+1)
 assert len(b)==size
 return dict(path=p.relative_to(R).as_posix(),bytes=size,sha256=hashlib.sha256(b).hexdigest())
value=dict(schema='dimensions-final-read-external-v1',command=command,source=dict(path=reader.relative_to(R).as_posix(),bytes=reader.stat().st_size,sha256=reader_sha),
 release=dict(path=release.relative_to(R).as_posix(),bytes=release.stat().st_size,sha256=release_sha),
 capture_source=ref(Path(__file__).resolve(),16384),exit_code=code,timeout_terminated=timedout,
 elapsed_wall_seconds=elapsed,stdout=ref(paths['stdout'],4096),stderr=ref(paths['stderr'],32768),exit=ref(paths['exit'],128),
 scope='Actual direct final-reader interval and terminal exit; raw byte streams. Reader reserves30CPU/60wall internally. Outer publication overhead and exact terminated CPU are not inferred from this interval.')
raw=(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
assert len(raw)<=16384
with paths['outer'].open('xb') as f:assert f.write(raw)==len(raw);f.flush();os.fsync(f.fileno())
print(json.dumps(dict(outer=ref(paths['outer'],16384),exit_code=code,timeout_terminated=timedout,reader_wall_seconds=elapsed)))
raise SystemExit(0 if code==0 and not timedout and elapsed<=60 else 1)
