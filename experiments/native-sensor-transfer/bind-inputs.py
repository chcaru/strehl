"""One fixed original-content binding pass. No decoder, image array or numerical check."""
import time
START=time.monotonic()
from pathlib import Path
import argparse,hashlib,json,os,sys,types

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
BASE=ROOT/'experiments/m194h-pedestal-causality/build-and-run.py'
BASE_SHA='b505a2fff0024691d98088c599f7f554c1543268de09c836a6bc1fe6c17b7410'
PATHS=tuple('D:/personal/macro/requests/10-paper-iso-var/DSC%05d.ARW'%i for i in range(235,240))+tuple(
 'D:/personal/macro/requests/6-11-extended-dark-frames/DSC%05d.ARW'%i for i in range(872,894))
CAPS=dict(cpu_seconds=20,wall_seconds=60,read_bytes=1<<30,write_bytes=64<<10)
def need(v,s):
 if not v:raise ValueError(s)
def main():
 p=argparse.ArgumentParser();p.add_argument('--release',required=True);p.add_argument('--release-sha256',required=True);a=p.parse_args()
 need(Path.cwd().resolve()==ROOT and sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode,'fixed isolated context')
 release_path=HERE/'input-binding-release-1.json'
 need(Path(a.release)==release_path,'fixed release path')
 raw=release_path.read_bytes();need(len(raw)<16384 and hashlib.sha256(raw).hexdigest()==a.release_sha256,'held binding release')
 release=json.loads(raw)
 own=Path(__file__).read_bytes();base=BASE.read_bytes()
 need(hashlib.sha256(own).hexdigest()==release['source']['sha256'] and len(own)==release['source']['bytes'],'held own source')
 need(hashlib.sha256(base).hexdigest()==BASE_SHA,'held stable-read primitive')
 need(release['schema']=='native-sensor-transfer-input-binding-release-v1' and release['limits']==CAPS and release['originals']==list(PATHS),'fixed population and bounds')
 command=[a.release_sha256 if v=='ACTUAL_RELEASE_SHA256' else v for v in release['command']]
 need(command==sys.orig_argv,'exact released invocation')
 module=types.ModuleType('native_input_binding_stable_read');module.__file__=str(BASE)
 exec(compile(base,str(BASE),'exec'),module.__dict__)
 read_bytes=len(raw)+len(own)+len(base)
 out=HERE/'input-bindings-1.json';need(not out.exists(),'fresh binding receipt')
 result=dict(schema='native-sensor-transfer-input-bindings-v1',status='INITIAL_INCOMPLETE',
 release=dict(path=release_path.relative_to(ROOT).as_posix(),bytes=len(raw),sha256=a.release_sha256),
 command=command,source=release['source'],originals=[],error=None,limits=CAPS,
 scope='One stable streaming hash per fixed original; no atomic snapshot, RAW decode, pixel statistic, or physical calibration claim. Process-local CPU/wall samples, with reserved final publication; no Job memory or whole-host timing claim.')
 def check():
  need(time.process_time()+1<=CAPS['cpu_seconds'] and time.monotonic()-START+2<=CAPS['wall_seconds'],'binding process sample plus publication reserve')
 try:
  for name in PATHS:
   check();path=Path(name);before=path.stat()
   need(0<before.st_size<=38825984 and read_bytes+before.st_size<=CAPS['read_bytes'],'fixed bounded original extent')
   read_bytes+=before.st_size
   _,ref=module.read(path,38825984,keep=False,check=check)
   ref['path']=name
   result['originals'].append(ref)
  need(len(result['originals'])==27 and sum(r['bytes'] for r in result['originals'])==926855168,'fixed original count and encoded total')
  check();result['status']='INPUT_IDENTITIES_HELD_UNDECODED'
 except BaseException as error:
  result['status']='REFUSED';result['error']=str(error)[:2048]
 result['work']=dict(read_bytes_charged=read_bytes,retained_original_refs=len(result['originals']),
  process_cpu_sample=time.process_time(),elapsed_wall_sample=time.monotonic()-START,
  final_publication_reserve=dict(cpu_seconds=1,wall_seconds=2),raw_decodes=0)
 data=(json.dumps(result,indent=2,allow_nan=False)+'\n').encode()
 need(len(data)<=CAPS['write_bytes'],'binding receipt extent')
 with out.open('xb') as f:need(f.write(data)==len(data),'binding full write');f.flush();os.fsync(f.fileno())
 print(json.dumps(dict(status=result['status'],originals=len(result['originals']),receipt=dict(path=out.relative_to(ROOT).as_posix(),bytes=len(data),sha256=hashlib.sha256(data).hexdigest()),work=result['work'])),flush=True)
 return 0 if result['status']=='INPUT_IDENTITIES_HELD_UNDECODED' else 1
if __name__=='__main__':raise SystemExit(main())
